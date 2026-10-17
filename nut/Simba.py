#!/usr/bin/env python3
# eShop GraphQL helper (Python port of eshop.sh).
#
# Required packages:
#   requests    (pip install requests)
#   brotli      (pip install brotli) -- optional; needed to send the console's exact Accept-Encoding ("..., br")
#   graphql-core (pip install graphql-core) -- optional; prints/hashes queries exactly like the shop's Apollo client
# Everything else is standard library (Python >= 3.8). No curl / jq / bash needed.
# Client cert: PEM file (certificate + private key) given by CERT
# default: eshop_hac_prod.pem

import hashlib
import html
import itertools
import json
import os
import random
import re
import shlex
import signal
import sys
import threading
import time
import unicodedata
import urllib.parse
from contextlib import contextmanager

try:
    import requests
    import urllib3
except ImportError as _e:  # pragma: no cover
    raise ImportError(
        "Missing required package: requests (urllib3 is installed with it).\n"
        "Required packages: requests\n"
        "Install with: pip install requests"
    ) from _e

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:  # optional: exact Apollo-style query printing / hashing for persisted queries
    from graphql import parse as _gql_parse, print_ast as _gql_print, GraphQLError as _GraphQLError
except ImportError:  # pragma: no cover
    _gql_parse = _gql_print = None
    _GraphQLError = Exception

# Image / media fields on applicationItem (probed OK):
#   heroBannerUrl   — relative path e.g. /i/<hash>.jpg (banner). Confirmed live.
#   screenshotUrls  — list of screenshot paths (scalar list; not "screenshots"). Confirmed via fields.
#   movies          — object list; probe children: movieUrl, url, ...
#   ratingInfo.rating.svgImageUrl — age-rating badge SVG path (in EXTRA_FIELDS ratingInfo; titledb uses only age).
# There is no separate iconUrl on the item in probes so far; VGC imageUrl is sessionStorage-only
# (purchase-complete UI). First screenshot or heroBannerUrl is the practical stand-in for an icon.
# Absolute CDN host is environment-specific (not in the GraphQL payload).
#

def env(name, default=""):
    """${NAME:-default}: unset or empty -> default."""
    v = os.environ.get(name)
    return v if v else default


GQL = env("GQL", "https://hac.lp1.savanna.srv.nintendo.net/graphql")
CERT = env("CERT", "eshop_hac_prod.pem")
SHOP = int(env("SHOP", "4"))
COUNTRY = env("COUNTRY", "US")
LANG_CODE = env("LANG_CODE", "en")
REGION = env("REGION", "USA")
TIMEOUT = float(env("TIMEOUT", "60"))

UA = "Mozilla/5.0 (Nintendo Switch; ShopN; Nintendo Switch) AppleWebKit/613.0 (KHTML, like Gecko) NF/6.0.3.31.11 NintendoBrowser/5.1.0.55481"

H_CT = "Content-Type: application/json"
H_ACCEPT = "Accept: application/graphql-response+json,application/json;q=0.9"
# systemWeb: setAcceptEncoding("gzip, deflate, br") at browser init (23.0.1 0x7100741060). br needs `pip install brotli`.
H_ACCEPT_ENCODING = "Accept-Encoding: gzip, deflate, br"
# systemWeb: "<lang>[,<ui>;q=0.8],en;q=0.5[,<lang2>;q=0.1]" (23.0.1 0x71007382a8); English (US) console -> "en-US,en;q=0.5".
H_ACCEPT_LANGUAGE = "Accept-Language: en-US,en;q=0.5"
# The shop page is served from https://hac.%.savanna.srv.nintendo.net (systemWeb string), i.e. the same origin as GQL;
# WebKit sends Origin on POST fetches.
H_ORIGIN = "Origin: " + "/".join(GQL.split("/", 3)[:3])


class ApiError(Exception):
    """Raised on transport / GraphQL errors. Empty message = already reported on stderr."""


def err(*a):
    print(*a, file=sys.stderr, flush=True)


def compact(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def pretty(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


def out(obj):
    """One JSON value to stdout: compact one-liner, or indented when PRETTY=1."""
    print(pretty(obj) if env("PRETTY") else compact(obj), flush=True)


def dig(obj, *keys):
    for k in keys:
        if obj is None:
            return None
        try:
            obj = obj[k]
        except (KeyError, IndexError, TypeError):
            return None
    return obj

def genre(app):
    """applicationItem.genre ("Adventure / Action / RPG / Other") -> ["Adventure", "Action", ...] (titledb
    "category"). Empty parts are dropped; an absent genre gives []."""
    data = app.get("genre")
    if isinstance(data, str):
        data = data.split("/")
    if isinstance(data, list):
        return [str(g).strip() for g in data if g and str(g).strip()]
    return []


# Simplified and Traditional Chinese share isoCode "zh" (ApplicationItemLanguage has only isoCode / name; introspection
# is disabled and no other code field exists, probed live). The name, in the store's language, tells them apart:
# 中文 (簡體字), 中国語 (簡体字), Chinese (Simplified), Chinesisch (Vereinfacht), 중국어 (간체) ... (confirmed live).
_ZH_SCRIPT = (("zh-Hans", ("简", "簡", "simpl", "sempl", "vereinfacht", "vereenvoudigd", "упрощ", "간체")),
              ("zh-Hant", ("繁", "trad", "традиц", "번체")))


def language_code(row):
    """One applicationItem.languages row -> titledb code: isoCode, except "zh" -> "zh-Hans" / "zh-Hant" by its name
    (plain "zh" when the name says neither)."""
    code = row.get("isoCode")
    if code == "zh":
        name = (row.get("name") or "").lower()
        code = next((tag for tag, keys in _ZH_SCRIPT if any(k in name for k in keys)), code)
    return code


def language_codes(app):
    """applicationItem.languages -> [code, ...] (titledb-style, language_code; repeats dropped)."""
    out = []
    for row in app.get("languages") or []:
        if not isinstance(row, dict):
            continue
        code = language_code(row)
        if code and code not in out:
            out.append(code)
    return out


def publisher_name(app):
    """applicationItem.publisher -> name string (titledb-style)."""
    pub = app.get("publisher")
    if isinstance(pub, dict):
        return pub.get("name")
    if isinstance(pub, str):
        return pub
    return None


def rating_age(app):
    """applicationItem.ratingInfo.rating.age -> int (titledb-style "rating")."""
    info = app.get("ratingInfo") or {}
    if not isinstance(info, dict):
        return None
    rating = info.get("rating") or {}
    if not isinstance(rating, dict):
        return None
    age = rating.get("age")
    return age if age is not None else None

def rating_content(app):
    info = app.get("ratingInfo") or {}
    if not isinstance(info, dict):
        return None

    descriptors = info.get("contentDescriptors") or []
    if not isinstance(descriptors, list):
        return None

    content_ratings = [item.get("name") for item in descriptors if isinstance(item, dict) and item.get("name")]

    return content_ratings if content_ratings else None


def img_url(path):
    """Relative /i/... path -> absolute img-eshop CDN URL."""
    if not path:
        return None
    if isinstance(path, str) and path.startswith("http"):
        return path
    base = env("IMG_CDN", "https://img-eshop.cdn.nintendo.net").rstrip("/")
    if not str(path).startswith("/"):
        path = "/" + str(path)
    return base + path


def player_number_max(app):
    """Single int for titledb numberOfPlayers: offline max, else local, else online."""
    pn = app.get("playerNumber")
    if not isinstance(pn, dict):
        return None
    for hi_k, lo_k in (
        ("offlineMax", "offlineMin"),
        ("localMax", "localMin"),
        ("onlineMax", "onlineMin"),
    ):
        hi = pn.get(hi_k)
        if hi is None:
            hi = pn.get(lo_k)
        if hi is not None:
            return hi
    return None


def release_date_int(app):
    """YYYY-MM-DD or similar -> YYYYMMDD int."""
    raw = app.get("releaseDateOnEshop") or app.get("releaseDate")
    if raw is None:
        return None
    s = str(raw).strip()
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) >= 8:
        return int(digits[:8])
    return None


def title_id(app):
    for r in app.get("romRights") or []:
        if isinstance(r, dict) and r.get("titleId"):
            return str(r["titleId"]).upper()
    for r in app.get("applications") or []:
        if isinstance(r, dict) and r.get("id"):
            return str(r["id"]).upper()
        if isinstance(r, str) and r:
            return r.upper()
    return None

def is_demo_nsuid(ns):
    try:
        return str(int(ns)).startswith("7003")
    except (TypeError, ValueError):
        return False

def is_dlc(app, ns=None):
    """DlcItem rows (__typename) or a 7005... nsUid."""
    if isinstance(app, dict) and app.get("__typename") == "DlcItem":
        return True
    try:
        return str(int(ns)).startswith("7005")
    except (TypeError, ValueError):
        return False


def is_bundle(app, ns=None):
    """BundleItem rows (__typename) or a 7007... nsUid."""
    if isinstance(app, dict) and app.get("__typename") == "BundleItem":
        return True
    try:
        return str(int(ns)).startswith("7007")
    except (TypeError, ValueError):
        return False


def get_icon_url(app):
    for r in app.get("applications") or []:
        if isinstance(r, dict) and r.get("imageUrl"):
            return str(r["imageUrl"])
    return None


def rom_size(app):
    """applicationItem.romSizes { hac { totalRomSize { rawValue } ... } } -> titledb "size" (int bytes, or None).
    totalRomSize wins; estimatedRomSize is the fallback when it is absent/zero."""
    rs = app.get("romSizes")
    if isinstance(rs, list):
        rs = rs[0] if rs else None
    if isinstance(rs, dict) and isinstance(rs.get("hac"), (dict, int, str)):
        rs = rs["hac"]
    if isinstance(rs, (int, str)) and not isinstance(rs, bool):
        rs = {"totalRomSize": rs}
    if not isinstance(rs, dict):
        return None
    for k in ("totalRomSize", "estimatedRomSize"):
        v = rs.get(k)
        if isinstance(v, dict):  # { rawValue } (bytes)
            v = v.get("rawValue")
        try:
            v = int(v)
        except (TypeError, ValueError):
            continue
        if v > 0:
            return v
    return None


def titledb_record(app, nsuid=None):
    """
    Map applicationItem -> titledb entry (ordered keys).
    Unknown fields are null. iconUrl not available from Savanna GraphQL.
    """
    if not isinstance(app, dict):
        return None
    ns = app.get("nsUid") if app.get("nsUid") is not None else nsuid
    tid = title_id(app)
    rights = None
    if tid and len(tid) == 16:
        rights = tid + ("0" * 16)

    screens = []
    for p in app.get("screenshotUrls") or []:
        u = img_url(p)
        if u:
            screens.append(u)

    # titledb stores "no data" as null, not []
    dlc = is_dlc(app, ns)
    bundle = is_bundle(app, ns)
    if dlc:  # a DLC rights ID ends in the ticket's master key revision, which the API does not expose
        rights = None
    if bundle:  # a bundle has no title ID / rights ID of its own (romRights lists its contents)
        tid = rights = None
    rec = {
        "bannerUrl": img_url(app.get("heroBannerUrl")),
        "category": genre(app) or None,
        "description": _text_or_none(app.get("description")),
        "developer": None,
        "frontBoxArt": None,
        "iconUrl": img_url(get_icon_url(app)),
        "id": tid,
        "intro": _text_or_none(app.get("catchCopy") or None),
        "isDemo": is_demo_nsuid(ns),
        "key": None,
        "languages": language_codes(app) or None,
        "name": _text_or_none(app.get("formalName") or app.get("name"), False),
        "nsuId": int(ns) if ns is not None else None,
        "numberOfPlayers": player_number_max(app),
        "publisher": _text_or_none(publisher_name(app), False),
        "rating": rating_age(app),
        "ratingContent": rating_content(app),
        "region": None,
        "releaseDate": release_date_int(app),
        "rightsId": rights,
        "screenshots": screens or None,
        "size": rom_size(app),
        "version": None,
    }
    if dlc:  # titledb DLC entries carry "ids": [id] right after "id"
        out_rec = {}
        for k, v in rec.items():
            out_rec[k] = v
            if k == "id":
                out_rec["ids"] = [tid] if tid else None
        rec = out_rec
    if bundle:  # titledb bundles: ratingContent [] (not null), languages null
        rec["ratingContent"] = rec["ratingContent"] or []
        rec["languages"] = None
    return rec


def _with_parent_id(rec, parent):
    """Insert "parentId" after numberOfPlayers (titledb key order)."""
    out_rec = {}
    for k, v in rec.items():
        out_rec[k] = v
        if k == "numberOfPlayers":
            out_rec["parentId"] = parent
    return out_rec



def has_errors(r):
    return isinstance(r, dict) and r.get("errors") not in (None, False)


def _parse_pause(text):
    """SECONDS or MIN-MAX -> (lo, hi)."""
    try:
        lo, hi = (float(x) for x in text.split("-", 1)) if "-" in text else (float(text),) * 2
    except ValueError:
        raise ApiError(f"SLEEP must be SECONDS or MIN-MAX (a random pause), got {text!r}") from None
    return min(lo, hi), max(lo, hi)


def sleep_if():
    s = env("SLEEP")
    if s:
        time.sleep(random.uniform(*_parse_pause(s)))


def dedupe_nsuid(items):
    """awk '!seen[nsUid]++': first occurrence wins; items without nsUid are dropped."""
    seen = set()
    for it in items:
        ns = it.get("nsUid") if isinstance(it, dict) else None
        if ns is None or ns in seen:
            continue
        seen.add(ns)
        yield it


# ---------------------------------------------------------------- transport

_session = None


def _have_brotli():
    for mod in ("brotli", "brotlicffi"):
        try:
            __import__(mod)
            return True
        except ImportError:
            pass
    return False


# Automatic persisted queries, as the shop's Apollo client does them (PersistedQueryLink with
# useGETForHashedQueries: true, uri "/graphql"):
#   1. GET  ?operationName=..&variables=..&extensions={"persistedQuery":{"version":1,"sha256Hash":..}}  (no body)
#   2. on PersistedQueryNotFound: POST {operationName, variables, extensions, query}
#   on PersistedQueryNotSupported: POST {operationName, variables, query} from then on.
# The server (module YATA) answers step 1 with PersistedQueryNotFound (errorCode 1807) for any hash it was not
# deployed with, and does not register hashes from step 2, so for simba's own queries step 1 always fails.
# By default simba therefore sends step 2 directly (one request); APQ_GET=1 restores the GET-first flow.
# The hash is sha256 of graphql print() of the query (graphql-core's print_ast matches graphql-js), and only the
# variables the operation declares are sent (Apollo's includeUnusedVariables: false).
_apq_supported = True
_apq_cache = {}
APQ_GET = env("APQ_GET") == "1"


def _apq_document(query):
    """-> (printed query, sha256 hex, declared variable names or None without graphql-core)."""
    hit = _apq_cache.get(query)
    if hit is None:
        printed, declared = query, None
        if _gql_parse is not None:
            try:
                doc = _gql_parse(query)
                printed = _gql_print(doc)
                declared = {v.variable.name.value for d in doc.definitions
                            for v in (getattr(d, "variable_definitions", None) or ())}
            except _GraphQLError:
                pass  # deliberately malformed probes: send as-is, let the server report it
        hit = _apq_cache[query] = (printed, hashlib.sha256(printed.encode("utf-8")).hexdigest(), declared)
    return hit


def _pq_error(r, code):
    """True if a response carries the given persisted-query error (message or extensions.code)."""
    name = {"PERSISTED_QUERY_NOT_FOUND": "PersistedQueryNotFound",
            "PERSISTED_QUERY_NOT_SUPPORTED": "PersistedQueryNotSupported"}[code]
    for e in (r.get("errors") or []) if isinstance(r, dict) else []:
        if isinstance(e, dict) and (e.get("message") == name or (e.get("extensions") or {}).get("code") == code):
            return True
    return False


def _uri_component(s):
    """JS encodeURIComponent."""
    return urllib.parse.quote(s, safe="-_.!~*'()")


def _session_get():
    global _session
    if not os.path.isfile(CERT):
        raise ApiError(f"client certificate not found: {CERT} (set CERT=...)")
    if _session is None:
        _session = requests.Session()
        _session.verify = False  # curl --insecure
        _session.cert = CERT
        accept_encoding = H_ACCEPT_ENCODING.split(": ", 1)[1]
        if "br" in accept_encoding and not _have_brotli():
            # urllib3 can't decode a br body without it; advertise only what we can read
            err("warning: brotli not installed (pip install brotli); sending Accept-Encoding without br")
            accept_encoding = ", ".join(e for e in accept_encoding.split(", ") if e != "br")
        # Replace (not update) requests' defaults: the console sends no Connection header
        _session.headers.clear()
        _session.headers.update({
            "User-Agent": UA,
            "Content-Type": H_CT.split(": ", 1)[1],
            "Accept": H_ACCEPT.split(": ", 1)[1],
            "Accept-Encoding": accept_encoding,
            "Accept-Language": H_ACCEPT_LANGUAGE.split(": ", 1)[1],
        })
    return _session


def _debug_curl(method, url, body=None):
    lines = [
        f"curl -s --insecure --cert {shlex.quote(CERT)} \\",
        f"  -A {shlex.quote(UA)} \\",
        f"  -H {shlex.quote(H_CT)} \\",
        f"  -H {shlex.quote(H_ACCEPT)} \\",
        f"  -H {shlex.quote(H_ACCEPT_ENCODING)} --compressed \\",
        f"  -H {shlex.quote(H_ACCEPT_LANGUAGE)} \\",
    ]
    if method == "POST":
        lines += [f"  -H {shlex.quote(H_ORIGIN)} \\",
                  f"  -X POST {shlex.quote(url)} \\",
                  f"  -d {shlex.quote(pretty(body))} | jq ."]
    else:
        lines += [f"  {shlex.quote(url)} | jq ."]
    sys.stderr.write("\n".join(lines) + "\n\n")
    sys.stderr.flush()


def _send(method, url, body=None):
    session = _session_get()
    if env("DEBUG"):
        _debug_curl(method, url, body)
    try:
        if method == "GET":
            resp = session.get(url, timeout=TIMEOUT)
        else:
            # WebKit adds Origin to POST fetches, not to same-origin GETs
            resp = session.post(url, data=compact(body).encode("utf-8"), timeout=TIMEOUT,
                                headers={"Origin": H_ORIGIN.split(": ", 1)[1]})
    except requests.RequestException as e:
        raise ApiError(f"request failed: {e}") from e
    try:
        return resp.json()
    except ValueError as e:
        raise ApiError(f"non-JSON response (HTTP {resp.status_code}): {resp.text[:200]!r}") from e


def gq(body):
    """Send a GraphQL request ({operationName, query, variables}) the way the shop's Apollo client does (see
    _apq_document). DEBUG=1 prints the equivalent curl command(s) to stderr."""
    global _apq_supported
    op = body.get("operationName")
    printed, sha, declared = _apq_document(body["query"])
    variables = body.get("variables")
    if declared is not None and variables is not None:
        variables = {k: v for k, v in variables.items() if k in declared}

    post = {}
    if op:
        post["operationName"] = op
    if variables is not None:
        post["variables"] = variables

    if _apq_supported:
        ext = {"persistedQuery": {"version": 1, "sha256Hash": sha}}
        r = None
        if APQ_GET:
            params = [(k, post[k] if k == "operationName" else compact(post[k])) for k in post]
            params.append(("extensions", compact(ext)))
            url = GQL + ("&" if "?" in GQL else "?") + "&".join(f"{k}={_uri_component(v)}" for k, v in params)
            r = _send("GET", url)
            if not (_pq_error(r, "PERSISTED_QUERY_NOT_FOUND") or _pq_error(r, "PERSISTED_QUERY_NOT_SUPPORTED")):
                return r
        if r is None or not _pq_error(r, "PERSISTED_QUERY_NOT_SUPPORTED"):
            r = _send("POST", GQL, {**post, "extensions": ext, "query": printed})
            if not _pq_error(r, "PERSISTED_QUERY_NOT_SUPPORTED"):
                return r
        _apq_supported = False
    return _send("POST", GQL, {**post, "query": printed})


# Per-thread store override set by simba_context() (the Simba compatibility layer): {"country", "language", "region"}.
# Its language wins over a caller's explicit language (lookups pass store_language()); an explicit country wins
# over its country (country_of(region) asks about that region).
_ctx = threading.local()


def _ctx_get(key):
    return (getattr(_ctx, "v", None) or {}).get(key)


def rawreq(op, query, variables, language=None, country=None, use_ctx=True):
    """-> raw response JSON (dict)."""
    if use_ctx:
        language = _ctx_get("language") or language
        country = country or _ctx_get("country")
    body = {
        "operationName": op,
        "query": query,
        "variables": {"shopId": SHOP, "country": country or COUNTRY,
                      "language": language or LANG_CODE, **variables},
    }
    return gq(body)


def fail_errors(r):
    err(pretty(r))
    raise ApiError("")


def req(op, query, variables, language=None):
    """Prints the response (compact by default, PRETTY=1 for indented)."""
    r = rawreq(op, query, variables, language)
    if has_errors(r):
        fail_errors(r)
    print(pretty(r) if env("PRETTY") else compact(r), flush=True)


# ---------------------------------------------------------------- queries

Q_COUNTRY = 'query Country($shopId: Int!, $country: CountryCode!, $language: LanguageCode!) @inContext(shopId: $shopId, country: $country, language: $language) { country { availableLanguages { code } defaultLanguage { code } regionCode shopStatuses { hac { shopOpenStatus } } } }'

# romSizes { hac { totalRomSize { rawValue } estimatedRomSize { rawValue } } }: hac confirmed live; the leaves are a
# guess from the eShop JS (it reads `.rawValue` of totalRomSize/estimatedRomSize). Probe:
#   PARENT='romSizes { hac' python simba.py fields <nsUid> totalRomSize estimatedRomSize rawValue
# ROM_SIZES overrides the sub-selection inside romSizes { }; ROM_SIZES=off drops it (size becomes null).
_rs = env("ROM_SIZES", "hac { totalRomSize { rawValue } estimatedRomSize { rawValue } }")
ROM_SIZES_SEL = "" if _rs.lower() in ("off", "0", "none") else "romSizes { " + _rs + " } "

# Every field titledb_record() / simba_json() read, apart from nsUid / formalName (selected separately because DLC
# queries alias formalName as `name`), and nothing else (languages.name: language_code tells zh-Hans / zh-Hant apart
# by it): fields neither reads (ids, rating badge / system,
# publicStatus, labelPlatform, itemType ...) are left out of every titledb query. Shared by Q_ITEM, Q_SCRAPE and the
# DLC queries so applications, demos and DLC all yield the same titledb record. Applications-only: applications { id imageUrl }.
# DLC_RECORD_FIELDS is the DlcItem selection; trim it if `dlc-fields` reports a field as X.
RECORD_FIELDS = (ROM_SIZES_SEL + 'genre catchCopy heroBannerUrl screenshotUrls releaseDateOnEshop description publisher { name } '
                 'ratingInfo { rating { age } contentDescriptors { name } } '
                 'languages { isoCode name } '
                 'playerNumber { offlineMin offlineMax localMin localMax onlineMin onlineMax } '
                 'romRights { titleId }')
DLC_RECORD_FIELDS = env(
    "DLC_RECORD_FIELDS",
    # `languages`, `playerNumber` and `genre` are rejected on DlcItem (error 1802, confirmed live): left out, so a DLC
    # record has languages / category / numberOfPlayers null. `catchCopy` untested: probe with dlc-fields.
    # romSizes (-> size) is UNVERIFIED on DlcItem: DLC_ROM_SIZES=off drops it (apps keep theirs).
    ("" if env("DLC_ROM_SIZES").lower() in ("off", "0", "none") else ROM_SIZES_SEL) +
    'heroBannerUrl screenshotUrls releaseDateOnEshop description publisher { name } '
    'ratingInfo { rating { age } contentDescriptors { name } } '
    'romRights { titleId }')

_APP_SEL = "nsUid formalName applications { id imageUrl } " + RECORD_FIELDS

Q_ITEM = ('query ApplicationItemDetailV2($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $nsUid: NsUid!) @inContext(shopId: $shopId, country: $country, language: $language) { item { applicationItem(nsUid: $nsUid) { '
          + _APP_SEL + ' } } }')

Q_TITLE = 'query ApplicationItemsByTitleId($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $titleIds: [TitleId!]!, $publicStatuses: [RequestablePublicStatus!]!, $selectFirst: Boolean!) @inContext(shopId: $shopId, country: $country, language: $language) { item { itemsByTitleIdsV2(titleIds: $titleIds, publicStatuses: $publicStatuses, selectFirst: $selectFirst, type: APPLICATION) { nsUid itemV2 { ... on ApplicationItem { formalName heroBannerUrl romRights { titleId } } } } } }'

Q_DLC_TITLES = ('query DlcByTitleIds($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $titleIds: [TitleId!]!) @inContext(shopId: $shopId, country: $country, language: $language) { item { itemsByTitleIdsV2(titleIds: $titleIds, publicStatuses: [PUBLIC], selectFirst: false, type: DLC) { nsUid itemV2 { ... on DlcItem { '
                'formalName ' + DLC_RECORD_FIELDS + ' } } } } }')

# searchV4 rows: nsUid / __typename for every caller; the ApplicationItem fields are what scrape-all /
# update-titledb (releaseDateOnEshop) and searchPage / getLatest (simba_json) read. Q_SEARCH_IDS is the nsUid-only
# variant for callers that look every row up again anyway (latestNsuids, search-count): no item data and no bundle
# fragment, so the BundleItem schema probe never runs for them.
_SEARCH_HEAD = 'query Search($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $region: RequestableRegion!, $freeword: String, $itemTypes: [SearchItemType!], $labelPlatforms: [RequestableDeviceType!], $limit: Int!, $offset: Int!, $salesStatus: RequestableSearchSalesStatus, $sort: SearchSort!) @inContext(shopId: $shopId, country: $country, language: $language) { searchV4(region: $region, freeword: $freeword, itemTypes: $itemTypes, labelPlatforms: $labelPlatforms, limit: $limit, offset: $offset, salesStatus: $salesStatus, sort: $sort) { items { ... on Item { nsUid __typename '
_SEARCH_TAIL = '} } offsetInfo { length offset total } } }'
Q_SEARCH_APP = (_SEARCH_HEAD + '... on ApplicationItem { name: formalName releaseDateOnEshop heroBannerUrl '
                'romRights { titleId } } ' + _SEARCH_TAIL)
Q_SEARCH_IDS = _SEARCH_HEAD + _SEARCH_TAIL

# BundleItem rows of searchV4 (BUNDLE=1). BUNDLE_BASE is the eShop's own BundleItem fragment, trimmed to what
# titledb_record reads. The extras (description / catchCopy / publisher / romSizes / ratingInfo.contentDescriptors)
# are not in that fragment: each is checked once against the
# schema (validation-only search, limit 1) and only the accepted ones are requested. BUNDLE_FIELDS replaces the
# whole selection (no probing).
BUNDLE_BASE = ('screenshotUrls heroBannerUrl name: formalName releaseDateOnEshop '
               'ratingInfo { rating { age } } romRights { titleId }')
BUNDLE_EXTRAS = ["description", "catchCopy", "publisher { name }", "ratingInfo { contentDescriptors { name } }"] + ([ROM_SIZES_SEL.strip()] if ROM_SIZES_SEL else [])
_bundle_sel_cache = []
_probe_lock = threading.RLock()  # the one-time schema probes run once even when nut calls in from several threads


def _search_bundle_query(sel):
    return Q_SEARCH_APP.replace("... on ApplicationItem {", "... on BundleItem { " + sel + " } ... on ApplicationItem {", 1)


def bundle_selection():
    """BundleItem selection for the search query (probed once, cached)."""
    if _bundle_sel_cache:
        return _bundle_sel_cache[0]
    with _probe_lock:
        if not _bundle_sel_cache:
            _bundle_sel_cache.append(_bundle_selection())
    return _bundle_sel_cache[0]


def _bundle_selection():
    sel = env("BUNDLE_FIELDS")
    if not sel:
        ok = []
        base_vars = {**_search_vars("ONSALE_OR_PRE_ORDER", "RELEASE_DATE_DESC", "", env("PLATFORM", "HAC"), 1), "offset": 0}
        for extra in BUNDLE_EXTRAS:
            r = rawreq("Search", _search_bundle_query(BUNDLE_BASE + " " + extra), base_vars)
            if has_errors(r):
                err(f"bundle: field '{extra}' not accepted on BundleItem, left out")
            else:
                ok.append(extra)
        sel = " ".join([BUNDLE_BASE] + ok)
    return sel


def q_search_app():
    """Q_SEARCH_APP, with a BundleItem fragment unless BUNDLE=0."""
    return _search_bundle_query(bundle_selection()) if bundles_on() else Q_SEARCH_APP


Q_SEARCH_DLC = 'query Search($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $region: RequestableRegion!, $freeword: String, $itemTypes: [SearchItemType!], $limit: Int!, $offset: Int!, $sort: SearchSort!) @inContext(shopId: $shopId, country: $country, language: $language) { searchV4(region: $region, freeword: $freeword, itemTypes: $itemTypes, limit: $limit, offset: $offset, sort: $sort) { items { ... on Item { nsUid __typename ... on DlcItem { name: formalName releaseDateOnEshop heroBannerUrl romRights { titleId } } } } offsetInfo { length offset total } } }'

Q_SCRAPE = ('query ScrapeTitle($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $nsUid: NsUid!) @inContext(shopId: $shopId, country: $country, language: $language) { item { applicationItem(nsUid: $nsUid) { '
            + _APP_SEL + ' demoItems { nsUid name: formalName } } } }')

# demoItems rows: titledb demos carry rating / ratingContent / size (+ parentId, taken from the base title).
# Each extra is checked once against the schema (validation-only; the nsUid need not exist) and only accepted
# ones are requested. DEMO_FIELDS replaces the whole extra selection (no probing; empty/off = none).
DEMO_EXTRAS = ["ratingInfo { rating { age } }", "ratingInfo { contentDescriptors { name } }"] + (
    [ROM_SIZES_SEL.strip()] if ROM_SIZES_SEL else [])
_demo_sel_cache = []


def _scrape_query(extra):
    return Q_SCRAPE.replace("demoItems { nsUid name: formalName }",
                            "demoItems { nsUid name: formalName " + extra + " }", 1)


def _probe_demo_extras(extras):
    """The extras the schema accepts inside applicationItem.demoItems (validation-only, the nsUid need not exist)."""
    ok = []
    for extra in extras:
        r = rawreq("ScrapeTitle", _scrape_query(extra), {"nsUid": 70010000000025}, store_language())
        if has_errors(r):
            err(f"demo: field '{extra}' not accepted on demoItems, left out")
        else:
            ok.append(extra)
    return ok


def demo_selection():
    if _demo_sel_cache:
        return _demo_sel_cache[0]
    with _probe_lock:
        if not _demo_sel_cache:
            if "DEMO_FIELDS" in os.environ:
                v = os.environ["DEMO_FIELDS"]
                _demo_sel_cache.append("" if v.lower() in ("off", "0", "none") else v)
            else:
                _demo_sel_cache.append(" ".join(_probe_demo_extras(DEMO_EXTRAS)))
    return _demo_sel_cache[0]


# Extra DemoItem fields for the Simba compatibility demo lookup (getTitleByNsuid of a 7003 nsUid), probed on the
# demoItem(nsUid) root. DemoItem rejects heroBannerUrl, screenshotUrls, releaseDateOnEshop, description and catchCopy
# (confirmed live, on both demoItem and applicationItem.demoItems), so a demo carries only name, rating, ratingContent,
# size and publisher. DEMO_LOOKUP_FIELDS replaces the extras (off = none). Not used by scan-range / scrape-*, so
# titledb output is unchanged. romRights is left out on purpose: a demo's id stays null, as in titledb.
DEMO_LOOKUP_EXTRAS = ["publisher { name }"]
_demo_lookup_cache = []


def _probe_demo_root(extras, base):
    """The extras the schema accepts on demoItem(nsUid) next to `base` (validation-only, on an nsUid that does not
    exist). If `base` alone already errors there (a missing item may itself be an error), probing cannot tell
    fields apart and none are taken. One summary line on stderr."""
    def ok(sel):
        q, qv = alias_apps_query("DemoProbe", [70039999999999], sel, "demoItem")
        return not has_errors(rawreq("DemoProbe", q, qv, store_language()))
    if not ok(base):
        err("demo lookup: demoItem cannot be probed (an unknown nsUid errors), extra demo fields left out")
        return []
    good = [e for e in extras if ok(base + " " + e)]
    bad = [e for e in extras if e not in good]
    if bad:
        err("demo lookup: demoItem does not accept " + ", ".join(bad) + "; left out")
    return good


def demo_lookup_selection():
    if _demo_lookup_cache:
        return _demo_lookup_cache[0]
    with _probe_lock:
        if not _demo_lookup_cache:
            base = demo_selection()
            if "DEMO_LOOKUP_FIELDS" in os.environ:
                v = os.environ["DEMO_LOOKUP_FIELDS"]
                extra = "" if v.lower() in ("off", "0", "none") else v
            else:
                extra = " ".join(_probe_demo_root(DEMO_LOOKUP_EXTRAS, ("__typename nsUid formalName " + base).strip()))
            _demo_lookup_cache.append(" ".join(x for x in (base, extra) if x))
    return _demo_lookup_cache[0]


def q_scrape():
    return _scrape_query(demo_selection())

# Region list (from Simba.py regions(), plus the SEA stores MY PH SG TH). Override: REGIONS="US JP GB".
REGIONS = env("REGIONS", "AR BG BR CL CO CY CZ DK EE FI GR HR HU IE IL LT LV MT NL NO PE PL PT RO SE SI SK ZA RU CH CA IT LU BE FR AT DE CN MX ES HK KR JP NZ AU GB US MY PH SG TH").split()


# ---------------------------------------------------------------- country / languages

_country_cache = {}


def country_of(region):
    """-> .data.country dict, or None on transport/GraphQL error. Successful answers are cached per region.
    Always asked in LANG_CODE (not a simba_context language, which may not exist in that country)."""
    if region in _country_cache:
        return _country_cache[region]
    try:
        r = rawreq("Country", Q_COUNTRY, {}, country=region, use_ctx=False)
    except ApiError:
        return None
    if has_errors(r) or dig(r, "data", "country") is None:
        return None
    _country_cache[region] = r["data"]["country"]
    return r["data"]["country"]


def country_language(region):
    c = country_of(region)
    if c is None:
        return "en"
    code = dig(c, "defaultLanguage", "code") or "en"
    return code.split("_")[0]


def country_languages(region):
    c = country_of(region)
    if c is None:
        return [country_language(region)]
    res = []
    for l in c.get("availableLanguages") or []:
        code = (l.get("code") or "").split("_")[0]
        if code not in res:
            res.append(code)
    return res


# ---------------------------------------------------------------- search

def bundles_on():
    """BundleItem rows are kept by default; BUNDLE=0 (or off/false/no) filters them out."""
    return env("BUNDLE", "1").lower() not in ("0", "off", "false", "no")


def emit_search_items(r):
    """One item per element of .data.searchV4.items; BundleItem dropped only with BUNDLE=0."""
    bundle = bundles_on()
    for it in dig(r, "data", "searchV4", "items") or []:
        if bundle or not (isinstance(it, dict) and it.get("__typename") == "BundleItem"):
            yield it


# Largest page sizes the API accepts (confirmed live): searchV4 limit 100 (120+ rejected; the eShop client asks for 60,
# so the newest 1000 take 10 requests instead of 17, same items in the same order), dlcItems limit 100 (200 rejected).
# LIMIT overrides both.
SEARCH_LIMIT = 100
DLC_LIMIT = 100


def paged(query, variables, start, quiet=False):
    """Walks searchV4 pages until items is empty (offsets >= 1000 are rejected by the API)."""
    off = start
    lim = env("LIMIT", str(SEARCH_LIMIT))
    mx = int(env("MAX_PAGES", "1000"))
    offset_max = int(env("OFFSET_MAX", "1000"))
    page = 0
    total = "?"
    why = "max-pages"
    while page < mx:
        r = rawreq("Search", query, {**variables, "offset": off})
        if has_errors(r):
            err(f"search stopped: API error at offset {off} (page {page})")
            fail_errors(r)
        n = len(dig(r, "data", "searchV4", "items") or [])
        t = dig(r, "data", "searchV4", "offsetInfo", "total")
        total = t if t is not None else "?"
        if n == 0:
            why = "empty-page"
            break
        yield from emit_search_items(r)
        # step by what the server returned, so a server-side page size below LIMIT cannot skip items
        off += n
        page += 1
        if off >= offset_max:
            why = "offset-cap-1000"
            break
        if total != "?" and off >= total:
            why = "reached-total"
            break
        sleep_if()
    if not quiet:
        err(f"search done: {why} at offset {off} after {page} pages (offsetInfo.total={total}, LIMIT={lim})")


def _search_vars(sales, sort, freeword, platform, limit):
    return {"region": _ctx_get("region") or REGION, "freeword": freeword, "sort": sort, "labelPlatforms": [platform],
            "itemTypes": env("ITEM_TYPES", "APPLICATION").split(), "salesStatus": sales, "limit": limit}


def search(offset=0, *, sales=None, sort=None, freeword=None, platform=None,
           limit=None, all_pages=None, quiet=None, ids_only=False):
    """search / get-latest. Unset arguments fall back to env (SALES SORT FREEWORD PLATFORM LIMIT ALL QUIET).
    ids_only: rows carry only nsUid / __typename (Q_SEARCH_IDS), for callers that look each row up again."""
    sales = sales or env("SALES", "ONSALE_OR_PRE_ORDER")
    sort = sort or env("SORT", "RELEASE_DATE_DESC")
    freeword = freeword if freeword is not None else env("FREEWORD", "")
    platform = platform or env("PLATFORM", "HAC")
    limit = limit if limit is not None else int(env("LIMIT", str(SEARCH_LIMIT)))
    all_pages = all_pages if all_pages is not None else bool(env("ALL"))
    quiet = quiet if quiet is not None else bool(env("QUIET"))

    if sales == "ALL" or sort == "BOTH":
        sales_list = ["ONSALE_OR_PRE_ORDER", "COMING_SOON"] if sales == "ALL" else [sales]
        sorts_list = ["RELEASE_DATE_DESC", "RELEASE_DATE_ASC"] if sort == "BOTH" else [sort]

        def combos():
            for sv in sales_list:
                for so in sorts_list:
                    yield from search(offset, sales=sv, sort=so, freeword=freeword, platform=platform,
                                      limit=limit, all_pages=all_pages, quiet=quiet, ids_only=ids_only)
        yield from dedupe_nsuid(combos())
        return

    variables = _search_vars(sales, sort, freeword, platform, limit)
    query = Q_SEARCH_IDS if ids_only else q_search_app()
    if all_pages:
        yield from paged(query, variables, offset, quiet)
    else:
        r = rawreq("Search", query, {**variables, "offset": offset})
        if has_errors(r):
            fail_errors(r)
        yield from emit_search_items(r)


def search_count(*, sales=None, freeword=None, sort=None):
    """offsetInfo ({length, offset, total}) for the current FREEWORD / SORT / SALES / PLATFORM / REGION."""
    variables = _search_vars(
        sales or env("SALES", "ONSALE_OR_PRE_ORDER"),
        sort or env("SORT", "RELEASE_DATE_DESC"),
        freeword if freeword is not None else env("FREEWORD", ""),
        env("PLATFORM", "HAC"), 1)
    r = rawreq("Search", Q_SEARCH_IDS, {**variables, "offset": 0})
    if has_errors(r):
        fail_errors(r)
    return dig(r, "data", "searchV4", "offsetInfo")


def dlc_search(offset=0):
    """All DLC (itemTypes:[DLC]); no parent filter, no salesStatus."""
    variables = {"region": _ctx_get("region") or REGION, "freeword": env("FREEWORD", ""), "sort": env("SORT", "RELEASE_DATE_DESC"),
                 "itemTypes": ["DLC"], "limit": int(env("LIMIT", str(SEARCH_LIMIT)))}
    if env("ALL"):
        yield from paged(Q_SEARCH_DLC, variables, offset, bool(env("QUIET")))
    else:
        r = rawreq("Search", Q_SEARCH_DLC, {**variables, "offset": offset})
        if has_errors(r):
            fail_errors(r)
        yield from emit_search_items(r)


def shard_walk(sales, prefix):
    """FREEWORD is fuzzy, not a strict prefix match, so the depth is kept low. A prefix with more than
    SHARD_CAP results is split by appending each of SHARD_CHARS; at SHARD_DEPTH the prefix is walked with
    SORT=BOTH (DESC + ASC, up to ~2000, partial). The caller dedupes by nsUid."""
    cap = int(env("SHARD_CAP", "1000"))
    depth = int(env("SHARD_DEPTH", "3"))
    chars = env("SHARD_CHARS", "a b c d e f g h i j k l m n o p q r s t u v w x y z 0 1 2 3 4 5 6 7 8 9").split()
    try:
        total = int(search_count(sales=sales, freeword=prefix)["total"])
    except (ApiError, KeyError, TypeError, ValueError):
        err(f"shard {sales} '{prefix}': count failed")
        return
    if total <= 0:
        return
    try:
        if total <= cap:
            err(f"shard {sales} '{prefix}': {total}")
            yield from search(0, sales=sales, freeword=prefix, all_pages=True, quiet=True)
        elif len(prefix) >= depth:
            err(f"shard {sales} '{prefix}': {total} > cap at max depth, walking DESC+ASC only (partial)")
            yield from search(0, sales=sales, freeword=prefix, all_pages=True, quiet=True, sort="BOTH")
        else:
            for c in chars:
                yield from shard_walk(sales, prefix + c)
    except ApiError:
        pass


def search_all():
    """Every item: SALES (default ALL) x FREEWORD prefix shards, deduped by nsUid."""
    sales = env("SALES", "ALL")
    sales_list = ["ONSALE_OR_PRE_ORDER", "COMING_SOON"] if sales == "ALL" else [sales]

    def walk():
        for sv in sales_list:
            yield from shard_walk(sv, "")
    yield from dedupe_nsuid(walk())


def get_latest():
    """Newest page only (offset 0), plain defaults; paging/filter env vars are ignored.
    PLATFORM (and SHOP/COUNTRY/LANG_CODE/REGION) are respected."""
    for k in ("ALL", "FREEWORD", "SORT", "SALES", "LIMIT", "BUNDLE", "MAX_PAGES"):
        os.environ.pop(k, None)
    yield from search(0)


def alias_apps_query(op, nsuids, sel, root="applicationItem"):
    """One request for many applicationItems: aliases a0.. with the nsUids passed as variables $n0.. (a literal
    nsUid beyond Int32 is rejected with error 1802). -> (query, variables)."""
    decl = "".join(f", $n{i}: NsUid!" for i in range(len(nsuids)))
    body = "".join(f"a{i}: {root}(nsUid: $n{i}) {{ {sel} }} " for i in range(len(nsuids)))
    q = (f"query {op}($shopId: Int!, $country: CountryCode!, $language: LanguageCode!{decl}) "
         "@inContext(shopId: $shopId, country: $country, language: $language) { item { " + body + "} }")
    return q, {f"n{i}": int(n) for i, n in enumerate(nsuids)}


def _hms(sec):
    sec = int(sec)
    return f"{sec // 3600}h{sec % 3600 // 60:02d}m{sec % 60:02d}s" if sec >= 3600 else f"{sec // 60}m{sec % 60:02d}s"


# nsUid prefix -> (root field, selection). The root fields were found with lookup-probe.
def _scan_target(prefix):
    if prefix == "7003":
        return "demoItem", "__typename nsUid name: formalName " + demo_selection()
    if prefix == "7005":
        return "dlcItem", "__typename nsUid name: formalName " + DLC_RECORD_FIELDS
    if prefix == "7007":
        return "bundleItem", "__typename nsUid " + bundle_selection()
    return "applicationItem", "nsUid formalName releaseDateOnEshop romRights { titleId }"


def scan_range(frm, to):
    """Walk nsUids FROM..TO directly (no search, so no 1000-item depth limit), BATCH lookups per request.
    The root field follows the nsUid prefix: 7001 applicationItem, 7003 demoItem, 7005 dlcItem, 7007 bundleItem
    (FROM and TO must share the prefix). 7001 yields search-shaped rows; the others yield full-data typed rows
    that scrape-all turns into titledb entries directly."""
    bsz = int(env("BATCH", "25"))
    prefix = str(frm)[:4]
    if str(to)[:4] != prefix:
        raise ApiError(f"FROM and TO must share the nsUid prefix ({prefix}... vs {str(to)[:4]}...)")
    root, sel = _scan_target(prefix)
    found = 0
    total = to - frm + 1
    t0 = time.time()
    tty = sys.stderr.isatty()
    every = int(env("PROGRESS_EVERY", "20"))  # batches between progress lines when stderr is not a terminal
    for bi, b in enumerate(range(frm, to + 1, bsz)):
        e = min(b + bsz - 1, to)
        q, qv = alias_apps_query("Scan", list(range(b, e + 1)), sel, root)
        r = rawreq("Scan", q, qv, store_language())
        if has_errors(r):
            err(f"scan stopped: API error in batch {b}..{e} (try a smaller BATCH)")
            fail_errors(r)
        for v in (dig(r, "data", "item") or {}).values():
            if v is None:
                continue
            found += 1
            if root != "applicationItem":
                yield v
                continue
            yield {"nsUid": v.get("nsUid"), "__typename": "ApplicationItem", "name": v.get("formalName"),
                   "releaseDateOnEshop": v.get("releaseDateOnEshop"), "romRights": v.get("romRights")}
        if not env("QUIET") and (tty or (bi + 1) % every == 0):
            done = e - frm + 1
            eta = (time.time() - t0) / done * (total - done)
            msg = (f"scan {e}/{to}  {100 * done / total:.1f}%  {found} found  "
                   f"elapsed {_hms(time.time() - t0)}  eta {_hms(eta)}")
            print(("\r" + msg + "\033[K") if tty else msg, end="" if tty else "\n", file=sys.stderr, flush=True)
        sleep_if()
    if tty and not env("QUIET"):
        err()  # end the progress line
    err(f"scan done: {frm}..{to}, {found} items ({root}), {_hms(time.time() - t0)}")


# ---------------------------------------------------------------- items / DLC / titles

def item(ns, language=None):
    r = rawreq("ApplicationItemDetailV2", Q_ITEM, {"nsUid": int(ns)}, language or store_language())
    if has_errors(r):
        fail_errors(r)
    app = dig(r, "data", "item", "applicationItem")
    if app is None:
        fail_errors(r if has_errors(r) else {"errors": [{"message": f"no applicationItem for {ns}"}]})
    rec = titledb_record(app, nsuid=int(ns))
    out_obj = {str(int(ns)): rec}
    out(out_obj)


def item_root(ns):
    """item.<root>(nsUid) for an nsUid: ROOT if set, else by prefix (7001 applicationItem, 7003 demoItem,
    7005 dlcItem, 7007 bundleItem; anything else applicationItem)."""
    return env("ROOT") or _EXTRA_ROOT.get(str(int(ns))[:4], _EXTRA_ROOT["7001"])[1]


def raw(ns, selection, language=None):
    q = ("query R($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $nsUid: NsUid!) "
         "@inContext(shopId: $shopId, country: $country, language: $language) "
         "{ item { " + item_root(ns) + "(nsUid: $nsUid) { " + selection + " } } }")
    req("R", q, {"nsUid": int(ns)}, language or store_language())


def gql(selection, language=None):
    """Run any root-level selection in the store context (SHOP / COUNTRY / LANG_CODE, the @inContext every query
    here uses) and print the response. For what the item-scoped commands cannot reach: root fields other than
    item { <root>(nsUid) } (membership, country, searchV4 with its own arguments), lookups that do not take an nsUid
    (item { ticketItemGroup(ticketItemGroupId: N) }) and several roots in one request. Queries that need a
    signed-in user ($idToken: prices, rights, tickets owned) are not possible."""
    q = ("query G($shopId: Int!, $country: CountryCode!, $language: LanguageCode!) "
         "@inContext(shopId: $shopId, country: $country, language: $language) { " + selection + " }")
    req("G", q, {}, language or store_language())


def fields(ns, names):
    """Field-name oracle on item.<root>(nsUid) (item_root: by nsUid prefix, or ROOT): unknown field -> error,
    known -> accepted."""
    parent = env("PARENT")
    opn = close = ""
    if parent:
        opn = parent + " {"
        close = "} " * opn.count("{")
        if not names:
            names = ["__typename", "nsUid", "formalName", "items", "edges", "nodes", "totalCount",
                     "total", "estimated", "bytes", "size", "sizes", "value", "romSize", "rom", "platform",
                     "type", "nsUid", "titleId", "totalSize", "estimatedSize", "fileSize", "totalBytes",
                     "... on ApplicationItem", "... on DlcItem", "... on BundleItem"]
    elif not names:
        names = ["titleId", "romRights", "upgradeInfo", "dlcItems", "dlcItemsV2", "dlcs", "dlc", "aocs",
                 "aocItems", "aocList", "relatedDlcs", "relatedItems", "extraContents", "additionalContents",
                 "addOnContents", "parentItem", "bundleItems",
                 # images (banner confirmed as heroBannerUrl; icon* names are probes)
                 "heroBannerUrl", "screenshotUrls", "iconUrl", "imageUrl", "productImageUrl", "squareIconUrl",
                 "screenshots", "bannerUrl", "thumbnails", "images", "movies",
                 "description", "publisher", "ratingInfo", "languages", "genre", "catchCopy",
                 "romSize", "totalRomSize", "fileSize", "totalFileSize", "size", "dataSize", "downloadSize", "contentSize", "installSize", "packageSize", "requiredStorage", "storageSize", "capacity", "romCapacity", "fileSizeBytes", "downloadFileSize", "romFileSize",
                 "playerNumberDescription", "miscDescription", "networkFeatureDescription"]
    for f in names:
        ok = None
        for sel in (f, f + " { __typename }"):
            q = ("query F($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $nsUid: NsUid!) "
                 "@inContext(shopId: $shopId, country: $country, language: $language) "
                 "{ item { " + item_root(ns) + "(nsUid: $nsUid) { " + f"{opn} {sel} {close}" + " } } }")
            r = rawreq("F", q, {"nsUid": int(ns)}, store_language())
            if not has_errors(r):
                ok = sel
                break
        print(f"{f} -> OK  ({ok})" if ok else f"{f} -> X", flush=True)


def dlc_fields(title_id_, names):
    """Field-name oracle on DlcItem (itemsByTitleIdsV2 type DLC): unknown field -> error, known -> accepted.
    Validates against the schema only, so the title ID does not need to exist."""
    if not names:
        names = ["formalName", "labelPlatform", "heroBannerUrl", "screenshotUrls", "releaseDateOnEshop",
                 "description", "publisher", "ratingInfo", "languages", "playerNumber", "genre", "catchCopy", "romRights", "romSizes",
                 "isMembershipRequired", "applications", "movies",
                 "romSize", "totalRomSize", "fileSize", "totalFileSize", "size", "dataSize", "downloadSize", "contentSize", "installSize", "packageSize", "requiredStorage", "storageSize", "capacity", "romCapacity", "fileSizeBytes", "downloadFileSize", "romFileSize"]
    for f in names:
        ok = None
        for sel in (f, f + " { __typename }"):
            q = ("query DF($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $titleIds: [TitleId!]!) "
                 "@inContext(shopId: $shopId, country: $country, language: $language) "
                 "{ item { itemsByTitleIdsV2(titleIds: $titleIds, publicStatuses: [PUBLIC], selectFirst: false, type: DLC) "
                 "{ nsUid itemV2 { ... on DlcItem { " + sel + " } } } } }")
            r = rawreq("DF", q, {"titleIds": [title_id_]}, store_language())
            if not has_errors(r):
                ok = sel
                break
        print(f"{f} -> OK  ({ok})" if ok else f"{f} -> X", flush=True)


def bundle_fields(names):
    """Field-name oracle on BundleItem via a validation-only searchV4 (bundles cannot be looked up by nsUid)."""
    if not names:
        names = ["isNew", "screenshotUrls", "movies", "heroBannerUrl", "formalName", "releaseDateOnEshop",
                 "labelPlatform", "ratingInfo", "romRights", "itemsV2", "description", "catchCopy", "publisher",
                 "genre", "languages", "playerNumber", "romSizes", "applications", "targetApplicationItems",
                 "isMembershipRequired", "price", "upgradeInfo"]
    v = {**_search_vars("ONSALE_OR_PRE_ORDER", "RELEASE_DATE_DESC", "", env("PLATFORM", "HAC"), 1), "offset": 0}
    for f in names:
        ok = None
        for sel in (f, f + " { __typename }"):
            r = rawreq("Search", _search_bundle_query(sel), v)
            if not has_errors(r):
                ok = sel
                break
        print(f"{f} -> OK  ({ok})" if ok else f"{f} -> X", flush=True)


def lookup_probe(names):
    """Which root fields of `item` accept an nsUid (validation-only; the nsUid need not exist). Tries each name
    with nsUid: N and nsUids: [N]; prints the accepted call shapes. A numeric argument is used as N (and the
    default field list is tried), so `lookup-probe 70050000000183` works."""
    ns = next((n for n in names if n.isdigit()), "70010000000025")
    names = [n for n in names if not n.isdigit()]
    if not names:
        names = ["applicationItem", "demoItem", "dlcItem", "bundleItem", "item", "itemByNsUid", "itemsByNsUid",
                 "itemsByNsUids", "itemV2", "itemsV2", "itemByNsUidV2", "itemsByNsUidsV2", "demoItems", "dlcItems",
                 "bundleItems", "applicationItems"]
    for f in names:
        hits = []
        for args in (f"nsUid: {ns}", f"nsUids: [{ns}]"):
            q = ("query L($shopId: Int!, $country: CountryCode!, $language: LanguageCode!) "
                 "@inContext(shopId: $shopId, country: $country, language: $language) "
                 "{ item { " + f"{f}({args}) {{ __typename }}" + " } }")
            r = rawreq("L", q, {}, store_language())
            if not has_errors(r):
                hits.append(args)
        print(f"{f} -> " + ("OK  (" + "; ".join(hits) + ")" if hits else "X"), flush=True)


def title(title_ids):
    r = rawreq("ApplicationItemsByTitleId", Q_TITLE,
               {"titleIds": list(title_ids), "publicStatuses": ["PUBLIC"], "selectFirst": False})
    if has_errors(r):
        fail_errors(r)
    for it in dig(r, "data", "item", "itemsByTitleIdsV2") or []:
        out(it)


def dlc_titles(title_ids):
    """DLC items by DLC title ID; yields one dict per item. Unknown IDs are not listed."""
    r = rawreq("DlcByTitleIds", Q_DLC_TITLES, {"titleIds": list(title_ids)})
    if has_errors(r):
        fail_errors(r)
    yield from dig(r, "data", "item", "itemsByTitleIdsV2") or []


def dlc_items_selection(off, lim, ps, ss, ib):
    """The dlcItems(...) { items { ... } } field of an applicationItem (also used by reprocess_titledb.py)."""
    return (f"dlcItems(offset: {off}, limit: {lim}, publicStatuses: [{ps.replace(',', ', ')}], "
            f"salesStatuses: [{ss.replace(',', ', ')}], isIncludeBundleItem: {ib}) "
            "{ items { __typename ... on Item { nsUid } "
            "... on DlcItem { name: formalName " + DLC_RECORD_FIELDS + " } "
            "... on BundleItem { romRights { titleId } } } }")


def _dlc_note(r, ns, items, off):
    """CLI only: say why nothing came back (an empty result is otherwise silent)."""
    if dig(r, "data", "item", "applicationItem") is None:
        err(f"dlc: no applicationItem for nsUid {ns} - dlc needs the base application's nsUid "
            "(is this a DLC / other item?)")
    elif not items and off == 0:
        err(f"dlc: no DLC returned for {ns} with SALES_STATUSES={env('SALES_STATUSES', 'ONSALE,PRE_ORDER')} "
            "(try SALES_STATUSES=ONSALE,PRE_ORDER,SALES_TERMINATION,UNRELEASED)")


def dlc(ns, offset=0, *, all_pages=None, sales_statuses=None, note=False):
    """applicationItem(nsUid).dlcItems(...) (aocs equivalent). ALL=1 pages until a page comes back short (every page
    but the last holds exactly LIMIT rows, confirmed live on titles with 194 and 265 rows) or empty."""
    lim = env("LIMIT", str(DLC_LIMIT))
    ps = env("PUBLIC_STATUSES", "PUBLIC")
    ss = sales_statuses or env("SALES_STATUSES", "ONSALE,PRE_ORDER")
    ib = env("INCLUDE_BUNDLES", "true")
    all_pages = all_pages if all_pages is not None else bool(env("ALL"))
    if not (re.fullmatch(r"[A-Z_,]+", f"{ps},{ss}") and re.fullmatch(r"true|false", ib)
            and re.fullmatch(r"[0-9]+", f"{lim}{offset}")):
        raise ApiError("invalid PUBLIC_STATUSES / SALES_STATUSES / INCLUDE_BUNDLES / LIMIT / offset")
    lim = int(lim)

    def dlcq(off):
        return ("query DlcItems($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $nsUid: NsUid!) "
                "@inContext(shopId: $shopId, country: $country, language: $language) "
                "{ item { applicationItem(nsUid: $nsUid) { nsUid "
                + dlc_items_selection(off, lim, ps, ss, ib) + " } } }")

    nv = {"nsUid": int(ns)}
    off = int(offset)
    if all_pages:
        mx = int(env("MAX_PAGES", "1000"))
        page = 0
        while page < mx:
            r = rawreq("DlcItems", dlcq(off), nv, store_language())
            if has_errors(r):
                fail_errors(r)
            items = dig(r, "data", "item", "applicationItem", "dlcItems", "items") or []
            if note:
                _dlc_note(r, ns, items, off)
            if not items:
                break
            yield from items
            if len(items) < lim:  # the last page: no need to ask for an empty one
                break
            off += lim
            page += 1
            sleep_if()
    else:
        r = rawreq("DlcItems", dlcq(off), nv, store_language())
        if has_errors(r):
            fail_errors(r)
        items = dig(r, "data", "item", "applicationItem", "dlcItems", "items") or []
        if note:
            _dlc_note(r, ns, items, off)
        yield from items


# ---------------------------------------------------------------- scraping

def _fetch_scrape_app(ns, quiet=False):
    """ScrapeTitle query -> applicationItem dict, or None (error / no such application)."""
    r = rawreq("ScrapeTitle", q_scrape(), {"nsUid": int(ns)}, store_language())
    if has_errors(r):
        if not quiet:
            err(pretty(r))
        return None
    app = dig(r, "data", "item", "applicationItem")
    if app is None and not quiet:
        err(f"no application item for nsUid {ns}")
    return app


def scrape_title(ns, quiet=False):
    """Application + each DLC + each demo as separate titledb records: [base, *dlc, *demos]
    (None on failure). DLC = every sales status (SCRAPE_SALES_STATUSES overrides) plus dlc-titles over every
    romRights titleId found (resolves DLC inside BundleItems). Title IDs ending in 800 are skipped."""
    app = _fetch_scrape_app(ns, quiet)
    if app is None:
        return None
    base = titledb_record(app, nsuid=int(ns))
    dlc_recs = [titledb_record(m) for m in _collect_dlc(ns)]

    demo_recs = []
    parent = title_id(app)  # titledb demos carry parentId = the base title ID (no id / rightsId of their own)
    for d in app.get("demoItems") or []:
        dn = d.get("nsUid")
        if dn is None:
            continue
        rec = titledb_record({**d, "nsUid": dn}, nsuid=int(dn))
        rec["isDemo"] = True
        demo_recs.append(_with_parent_id(rec, parent))

    return [base] + dlc_recs + demo_recs


def _collect_dlc(ns, first_page=None):
    """DlcItem dicts of application `ns`: its dlcItems rows (every sales status; SCRAPE_SALES_STATUSES overrides)
    plus dlc-titles over every romRights titleId found (resolves DLC inside BundleItems). Unique by nsUid, sorted
    by nsUid; title IDs ending in 800 are skipped. Errors go to stderr; whatever was fetched is returned.
    first_page: the rows of the first dlcItems page (offset 0, SCRAPE_DLC_LIMIT rows) when the caller already
    fetched them with the application (scrapeNsuids); only the pages after it are requested."""
    ss = env("SCRAPE_SALES_STATUSES", "ONSALE,PRE_ORDER,SALES_TERMINATION,UNRELEASED")
    dlc_items = []
    try:
        if first_page is None:
            dlc_items.extend(dlc(ns, 0, all_pages=True, sales_statuses=ss))
        else:
            dlc_items.extend(first_page)
            if len(first_page) >= SCRAPE_DLC_LIMIT:  # a full first page: there may be more
                dlc_items.extend(dlc(ns, SCRAPE_DLC_LIMIT, all_pages=True, sales_statuses=ss))
    except ApiError as e:
        if str(e):
            err(str(e))

    # dlc-titles only for title IDs no DlcItem row already carries, i.e. DLC that is listed only inside a BundleItem
    # (asking for the others returned nothing new, confirmed live: 5 requests -> 1 on 12 titles, same DLC set)
    def rights(rows):
        return {rr["titleId"] for it in rows for rr in (it.get("romRights") or [])
                if rr.get("titleId") and not rr["titleId"].endswith("800")}
    ids = sorted(rights(it for it in dlc_items if it.get("__typename") == "BundleItem")
                 - rights(it for it in dlc_items if it.get("__typename") == "DlcItem"))
    resolved = []
    for i in range(0, len(ids), 25):  # xargs -n 25
        try:
            resolved.extend(dlc_titles(ids[i:i + 25]))
        except ApiError as e:
            if str(e):
                err(str(e))

    # DLC as GraphQL DlcItem dicts (dlcItems rows first, then dlc-titles results). Rows carry `name`
    # (alias) or `formalName`; titledb_record accepts both.
    merged = [it for it in dlc_items if it.get("__typename") == "DlcItem"]
    for it in resolved:
        merged.append({**(it.get("itemV2") or {}), "nsUid": it.get("nsUid")})
    # jq unique_by(.nsUid): sorted by nsUid, first of each kept
    merged.sort(key=lambda m: (m.get("nsUid") is None, m["nsUid"] if m.get("nsUid") is not None else 0))
    res, seen = [], set()
    for m in merged:
        ns_d = m.get("nsUid")
        if (dig(m, "romRights", 0, "titleId") or "").endswith("800") or ns_d in seen:
            continue
        seen.add(ns_d)
        res.append(m)
    return res


def emit_records(recs, seen=None):
    """One titledb entry per line, {"<nsUid>": record}, as `item` / `dlc` print. `seen` (a set) drops
    nsUids already emitted."""
    for rec in recs:
        ns = rec.get("nsuId")
        if ns is None or (seen is not None and ns in seen):
            continue
        if seen is not None:
            seen.add(ns)
        out({str(ns): rec})


def read_ndjson(src):
    """JSON values from a file/stdin: one per line, or indented multi-line (PRETTY=1 output)."""
    fh = sys.stdin if src in (None, "-") else open(src, "r", encoding="utf-8")
    buf = ""
    try:
        for line in fh:
            if not buf and not line.strip():
                continue
            if not buf and line.lstrip()[0] not in "{[":
                err(f"skipping non-JSON line: {line.strip()[:80]!r}")
                continue
            buf += line
            try:
                val = json.loads(buf)
            except ValueError:
                continue  # incomplete (indented object): keep reading
            buf = ""
            yield val
        if buf.strip():
            err(f"skipping incomplete JSON at end of input: {buf.strip()[:80]!r}")
    finally:
        if fh is not sys.stdin:
            fh.close()


def _is_full_typed_row(it):
    """DlcItem / DemoItem row carrying record data (scan-range output), not a bare dlc-search row."""
    return (it.get("__typename") in ("DlcItem", "DemoItem")
            and any(k in it for k in ("screenshotUrls", "ratingInfo", "romSizes", "description")))


def scrape_all(items):
    """scrape_title for every .nsUid in an iterable of search-shaped dicts; prints titledb entries
    (application, DLC and demos each on their own line). Duplicates skipped; failures go to stderr and the
    run continues. If a record has no releaseDate, the search item's releaseDateOnEshop fills it.
    Progress / ETA go to stderr (a list input knows its total; a stream shows counts only): a line per item
    on a terminal, else every PROGRESS_EVERY=10 items; QUIET=1 = none."""
    seen_out = set()
    total = None
    if isinstance(items, list):
        items = list(dedupe_nsuid(items))
        total = len(items)
    stream = items if total is not None else dedupe_nsuid(items)
    t0 = time.time()
    tty = sys.stderr.isatty()
    every = int(env("PROGRESS_EVERY", "10"))
    n_done = n_failed = 0

    def progress(last=False):
        if env("QUIET") or not (tty or last or n_done % every == 0):
            return
        msg = f"scrape {n_done}" + (f"/{total}  {100 * n_done / max(1, total):.1f}%" if total else "")
        msg += f"  {len(seen_out)} entries" + (f"  {n_failed} failed" if n_failed else "")
        msg += f"  elapsed {_hms(time.time() - t0)}"
        if total and n_done:
            msg += f"  eta {_hms((time.time() - t0) / n_done * (total - n_done))}"
        print(("\r" + msg + "\033[K") if tty else msg, end="" if tty else "\n", file=sys.stderr, flush=True)

    for it in stream:
        n_done += 1
        ns = it["nsUid"]
        if _is_full_typed_row(it):  # scan-range rows of demos / DLC: the row itself is the record
            rec = titledb_record(it)
            emit_records([_with_parent_id(rec, it.get("parentId")) if it.get("__typename") == "DemoItem" else rec],
                         seen_out)
        elif is_bundle(it, ns):  # no lookup by nsUid exists for bundles: the search row is the record
            emit_records([titledb_record(it)], seen_out)
        else:
            try:
                recs = scrape_title(ns)
            except ApiError:
                recs = None
            if recs is None:
                n_failed += 1
                if tty and not env("QUIET"):
                    err()
                err(f"scrape-title {ns} failed")
            else:
                if recs[0].get("releaseDate") is None:
                    recs[0]["releaseDate"] = release_date_int({"releaseDateOnEshop": it.get("releaseDateOnEshop")})
                emit_records(recs, seen_out)
            sleep_if()
        progress()
    if n_done and not env("QUIET"):
        if tty:
            err()
        if not tty and n_done % every:
            progress(last=True)
        err(f"scrape-all done: {n_done} titles, {len(seen_out)} entries" + (f", {n_failed} failed" if n_failed else "")
            + f", {_hms(time.time() - t0)}")


def _titledb_entries(val):
    """One parsed JSON value -> {nsUid: record} or None if it is not titledb-shaped. Accepts a whole titledb
    object, a {"<nsUid>": record} line, or a bare record (keyed by its nsuId)."""
    if isinstance(val, dict) and val.get("nsuId") is not None:
        return {str(val["nsuId"]): val}
    if isinstance(val, dict) and all(k.isdigit() for k in val) and all(isinstance(v, dict) for v in val.values()):
        return val
    return None


def load_titledb_entries(src, keep="last"):
    """File (or "-" = stdin) with a titledb object and/or NDJSON / indented entry lines -> ({nsUid: record},
    skipped). keep="last": a later duplicate replaces an earlier one (position kept); "first": the first wins."""
    entries, skipped = {}, 0

    def values():
        if src not in (None, "-"):
            try:  # a whole titledb file parses in one go (much faster than line-by-line accumulation)
                with open(src, encoding="utf-8") as f:
                    yield json.load(f)
                return
            except ValueError:
                pass
        yield from read_ndjson(src)

    for val in values():
        found = _titledb_entries(val)
        if found is None:
            skipped += 1
            continue
        for k, v in found.items():
            if keep == "last" or k not in entries:
                entries[k] = v
    return entries, skipped


def titledb_text(entries, indent=False):
    """{nsUid: record} -> file text: one entry per line, or fully indented."""
    if indent:
        return pretty(entries) + "\n"
    if entries:
        return "{\n" + ",\n".join(f"{json.dumps(k)}:{compact(v)}" for k, v in entries.items()) + "\n}\n"
    return "{}\n"


def write_text_atomic(dst, text):
    d = os.path.dirname(dst)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = dst + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, dst)


def _read_titledb(path):
    """Existing titledb.json -> ({nsUid: record}, indented?). Raises ApiError (file untouched) if it is
    missing or not a JSON object."""
    if not os.path.isfile(path):
        raise ApiError(f"{path} not found (create it first, e.g. with process-titledb)")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        entries = json.loads(text)
    except (OSError, ValueError) as e:
        raise ApiError(f"cannot read {path}: {e}") from e
    if not isinstance(entries, dict):
        raise ApiError(f"{path} is not a titledb JSON object")
    lines = text.split("\n", 2)
    return entries, bool(env("PRETTY")) or (len(lines) > 1 and lines[1].startswith("  "))


def process_titledb(src, dst):
    """NDJSON / indented stream of {"<nsUid>": record} entries (scrape-*, dlc, item output) -> one JSON object
    {"<nsUid>": record, ...}. Later entries replace earlier ones with the same nsUid (so appended runs merge,
    keeping first-seen order). Bare titledb records (with "nsuId") are keyed by it; anything else is skipped.
    Default layout is one entry per line; PRETTY=1 indents fully. dst None / "-" = stdout. src may equal dst."""
    entries, skipped = load_titledb_entries(src, keep="last")
    cleaned = 0
    if env("CLEAN_TEXT").lower() not in ("0", "off", "false", "no"):  # CLEAN_TEXT=0 keeps the text as scraped
        cleaned = sum(1 for rec in entries.values() if isinstance(rec, dict) and clean_record(rec))
    text = titledb_text(entries, bool(env("PRETTY")))
    if dst in (None, "-"):
        sys.stdout.write(text)
    else:
        write_text_atomic(dst, text)
    err(f"process-titledb: {len(entries)} entries" + (f", {cleaned} text-cleaned" if cleaned else "")
        + (f", {skipped} skipped (not titledb-shaped)" if skipped else "")
        + ("" if dst in (None, "-") else f" -> {dst}"))


def sort_entries(entries, force=False):
    """{nsUid: record} sorted by nsUid ascending (numeric keys first, others after, by text). Unless `force`
    (reorder-titledb), TITLEDB_SORT=0 turns sorting off and the order is returned unchanged."""
    if not force and env("TITLEDB_SORT", "1").lower() in ("0", "off", "false", "no"):
        return entries
    return dict(sorted(entries.items(), key=lambda kv: (0, int(kv[0]), kv[0]) if kv[0].isdigit() else (1, 0, kv[0])))


def reorder_titledb(src, dst=None):
    """Sort a titledb.json by nsUid key, ascending (numeric). Entries are not changed. Layout (one per line /
    indented) is kept; PRETTY=1 forces indented. dst defaults to src (rewritten atomically), "-" = stdout."""
    entries, indent = _read_titledb(src)
    dst = dst or src
    ordered = sort_entries(entries, force=True)
    moved = sum(1 for a, b in zip(entries, ordered) if a != b)
    text = titledb_text(ordered, indent)
    if dst == "-":
        sys.stdout.write(text)
    else:
        write_text_atomic(dst, text)
    err(f"reorder-titledb: {len(ordered)} entries, " + (f"{moved} moved" if moved else "already sorted")
        + ("" if dst == "-" else f" -> {dst}"))


def update_titledb(path):
    """scrape-latest (ALL=1: the whole search, up to 1000 titles) appended to an existing titledb.json. Only
    entries whose nsUid is not in the file are added; existing entries are never changed. Titles already in
    the file are not scraped again (so DLC added later to a known title is not picked up). The file is only
    rewritten when something was added; its layout (one per line / indented) is kept."""
    entries, indent = _read_titledb(path)
    total_before = len(entries)
    if env("ALL"):  # the whole search (searchV4 stops at 1000)
        source = search(0)
    else:  # newest UPDATE_COUNT (default 150) titles, fetched in pages of SEARCH_LIMIT (get-latest itself is one page)
        source = itertools.islice(search(0, limit=SEARCH_LIMIT, all_pages=True), int(env("UPDATE_COUNT", "150")))
    added = {"titles": 0, "DLC": 0, "demos": 0, "bundles": 0}
    checked = failed = 0
    problem = None
    try:
        for it in dedupe_nsuid(source):
            checked += 1
            if str(it["nsUid"]) in entries:
                continue
            if is_bundle(it, it["nsUid"]):  # the search row itself is the record
                recs = [titledb_record(it)]
                added["bundles"] += 1
                entries[str(it["nsUid"])] = recs[0]
                continue
            try:
                recs = scrape_title(it["nsUid"])
            except ApiError:
                recs = None
            if recs is None:
                failed += 1
                err(f"scrape-title {it['nsUid']} failed")
                sleep_if()
                continue
            if recs[0].get("releaseDate") is None:
                recs[0]["releaseDate"] = release_date_int({"releaseDateOnEshop": it.get("releaseDateOnEshop")})
            for i, rec in enumerate(recs):
                key = str(rec["nsuId"]) if rec.get("nsuId") is not None else None
                if key is None or key in entries:
                    continue
                entries[key] = rec
                added["titles" if i == 0 else "demos" if rec.get("isDemo") else "DLC"] += 1
            sleep_if()
    except ApiError as e:  # the search itself failed (details already on stderr)
        problem = str(e) or "the search request failed"
    n = sum(added.values())
    if n:
        write_text_atomic(path, titledb_text(sort_entries(entries), indent))
        print(f"{path}: added {n} entries ({added['titles']} titles, {added['DLC']} DLC, {added['demos']} demos"
              + (f", {added['bundles']} bundles" if added["bundles"] else "") + "); "
              f"{len(entries)} total" + (f"; {failed} title(s) failed to scrape" if failed else "")
              + (f"; stopped early: {problem}" if problem else ""), flush=True)
    elif problem or failed:
        raise ApiError(f"update-titledb failed: " + (problem or f"{failed} title(s) could not be scraped")
                       + f"; {path} unchanged")
    else:
        print(f"{path}: up to date, no new entries (checked {checked} latest titles, all already present; "
              f"{total_before} total)", flush=True)


def update_titledb_file(path, other):
    """Merge `other` (a titledb file; NDJSON entry lines also work) into `path`: only nsUids not already in
    `path` are added, existing entries are never changed, and a nsUid repeated in `other` is added once (first
    wins). The file is only rewritten when something was added; its layout is kept."""
    entries, indent = _read_titledb(path)
    if not os.path.isfile(other):
        raise ApiError(f"{other} not found")
    new, skipped = load_titledb_entries(other, keep="first")
    add = {k: v for k, v in new.items() if k not in entries}
    present = len(new) - len(add)
    note = (f"; {skipped} line(s) in {other} were not titledb-shaped" if skipped else "")
    if add:
        if env("CLEAN_TEXT").lower() not in ("0", "off", "false", "no"):  # new entries only
            for rec in add.values():
                if isinstance(rec, dict):
                    clean_record(rec)
        entries.update(add)
        write_text_atomic(path, titledb_text(sort_entries(entries), indent))
        print(f"{path}: added {len(add)} entries from {other} ({present} already present, not changed); "
              f"{len(entries)} total{note}", flush=True)
    elif new:
        print(f"{path}: up to date, no new entries ({present} in {other}, all already present){note}", flush=True)
    else:
        raise ApiError(f"update-titledb-file failed: no titledb entries found in {other}")


# ---------------------------------------------------------------- text clean-up

_ESC_U = re.compile(r"(?:\\u[0-9a-fA-F]{4})+")
_ENTITY = re.compile(r"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]{1,31});")
_LINE_TERM = re.compile(r"\r\n|[\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029]")
_CONTROL = re.compile(r"[\x00-\x08\x0e-\x1b\x1f\x7f-\x9f\u00ad\u200b\u2060-\u2064\ufeff]")
_SPACES = re.compile(r"[\u00a0\u1680\u2000-\u200a\u202f\u205f]")
_TRAIL = re.compile(r"[ \t]+(?=\n)")
TEXT_FIELDS = ("name", "description", "intro", "publisher", "developer")


_ASCII_MAP = {"\u2018": "'", "\u2019": "'", "\u201a": "'", "\u2032": "'", "\u201b": "'", "\u00b4": "'",
              "\u02bc": "'", "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u2033": '"', "\u201f": '"',
              "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u2015": "-",
              "\u2212": "-", "\u2026": "...", "\u3000": " "}


def _ascii_level():
    """TEXT_ASCII: 0 off; 1 / on = punctuation and width forms; 2 / latin = + accents dropped from
    Latin letters (default when unset)."""
    v = env("TEXT_ASCII").lower()
    if v == "":
        return 2
    if v in ("0", "off", "false", "no"):
        return 0
    return {"2": 2, "latin": 2}.get(v, 1)


def _ascii_fold(text, level):
    # 1: typographic quotes / dashes / ellipsis, ideographic space, fullwidth ASCII forms (！ＡＢＣ～ -> !ABC~),
    #    Roman-numeral characters (Ⅱ -> II); letters, kana / kanji and symbols such as TM and R stay
    out_chars = []
    for ch in text:
        o = ord(ch)
        if ch in _ASCII_MAP:
            out_chars.append(_ASCII_MAP[ch])
        elif 0xFF01 <= o <= 0xFF5E:
            out_chars.append(chr(o - 0xFEE0))
        elif 0x2160 <= o <= 0x217F:
            out_chars.append(unicodedata.normalize("NFKC", ch))
        else:
            out_chars.append(ch)
    text = "".join(out_chars)
    if level >= 2:  # 2: accents dropped where an ASCII base letter remains (e-acute -> e, o-macron -> o)
        folded = []
        for ch in text:
            if ord(ch) > 127:
                base = "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c))
                if base and base.isascii():
                    ch = base
            folded.append(ch)
        text = "".join(folded)
    return text


def _replacements():
    """TEXT_REPLACE='src=dst;src=dst' (own substitutions, empty dst deletes; applied before TEXT_ASCII)."""
    pairs = []
    for item in env("TEXT_REPLACE").split(";"):
        if "=" in item:
            src, dst = item.split("=", 1)
            if src:
                pairs.append((src, dst))
    return pairs


def _unescape_u(m):
    try:  # \ud83d\ude00 pairs are decoded together; a lone surrogate is left as it was
        txt = json.loads('"' + m.group(0) + '"')
        txt.encode("utf-8")
        return txt
    except (ValueError, UnicodeEncodeError):
        return m.group(0)


def clean_text(text, stats=None, multiline=True):
    """Normalise text from the eShop: literal \\uXXXX escapes and HTML entities decoded, NFC, every line
    terminator (CRLF, CR, VT, FF, NEL, LS U+2028, PS U+2029) -> "\\n", control / zero-width / BOM / soft-hyphen
    characters removed, no-break and other odd spaces -> " ", trailing spaces dropped, ends stripped.
    `stats` (a dict) counts the kinds of change; multiline=False also turns line breaks into spaces.
    Non-strings are returned unchanged."""
    if not isinstance(text, str):
        return text
    cur = _clean_once(text, stats, multiline)
    for _ in range(4):  # a step can enable another (accent folding leaves a mark NFC then composes): to a fixed point
        nxt = _clean_once(cur, None, multiline)
        if nxt == cur:
            break
        cur = nxt
    return cur


def _clean_once(text, stats, multiline):
    cur = text

    def step(name, new):
        nonlocal cur
        if new != cur:
            if stats is not None:
                stats[name] = stats.get(name, 0) + 1
            cur = new

    step("escaped unicode", _ESC_U.sub(_unescape_u, cur))
    step("html entities", _ENTITY.sub(lambda m: html.unescape(m.group(0)), cur))
    step("normalization (NFC)", unicodedata.normalize("NFC", cur))
    new = cur
    for src, dst in _replacements():
        new = new.replace(src, dst)
    step("replaced characters (TEXT_REPLACE)", new)
    level = _ascii_level()
    if level:
        step(f"ASCII folding (TEXT_ASCII={level})", _ascii_fold(cur, level))
    step("line terminators", _LINE_TERM.sub("\n", cur))
    step("control / invisible characters", _CONTROL.sub("", cur))
    step("odd spaces", _SPACES.sub(" ", cur))
    step("trailing whitespace", _TRAIL.sub("", cur).strip())
    if not multiline:  # single-line fields (name, publisher, developer): a line break becomes a space
        step("line break in a single-line field", re.sub(r"[ \t]*\n\s*", " ", cur))
    return cur


_WS_CONTROL = re.compile(r"[\x00-\x08\x0e-\x1f\x7f-\x9f﻿]")
# True: _text_or_none only does the layout clean-up (clean_whitespace), never replaces characters. nut sets it.
WHITESPACE_ONLY = False


def clean_whitespace(text, multiline=True):
    """Layout-only clean-up: literal \\uXXXX escapes decoded, every line terminator (CRLF, CR, VT, FF, NEL, LS, PS)
    -> "\\n", control characters and BOM removed, trailing spaces dropped, ends stripped; multiline=False also turns
    line breaks into spaces. No other character is replaced (no NFC, entity decoding, odd-space or ASCII folding).
    Non-strings are returned unchanged."""
    if not isinstance(text, str):
        return text
    text = _ESC_U.sub(_unescape_u, text)
    text = _LINE_TERM.sub("\n", text)
    text = _WS_CONTROL.sub("", text)
    text = _TRAIL.sub("", text).strip()
    if not multiline:
        text = re.sub(r"[ \t]*\n\s*", " ", text)
    return text


def _text_or_none(text, multiline=True):
    """clean_text (clean_whitespace if WHITESPACE_ONLY) for an optional field: empty after cleaning -> None.
    CLEAN_TEXT=0 disables the clean-up."""
    if env("CLEAN_TEXT").lower() in ("0", "off", "false", "no"):
        return text
    out_text = (clean_whitespace if WHITESPACE_ONLY else clean_text)(text, multiline=multiline)
    return out_text if out_text else (None if text is not None else text)


def clean_record(rec, stats=None):
    """clean_text on the text fields of a titledb record, in place; -> number of fields changed."""
    changed = 0
    for k in TEXT_FIELDS:
        v = rec.get(k)
        if isinstance(v, str):
            new = clean_text(v, stats, multiline=k in ("description", "intro"))
            if new == "" and k != "name":
                new = None
            if new != v:
                rec[k] = new
                changed += 1
                if stats is not None:
                    stats["field " + k] = stats.get("field " + k, 0) + 1
    return changed


def clean_titledb(src, dst=None):
    """Normalise name / description / intro / publisher / developer of every entry of a titledb file (see
    clean_text). dst defaults to src (in place; only rewritten if something changed). Order and layout kept."""
    entries, indent = _read_titledb(src)
    stats = {}
    n_changed = sum(1 for rec in entries.values() if isinstance(rec, dict) and clean_record(rec, stats))
    dst = dst or src
    if n_changed or dst != src:
        text = titledb_text(entries, indent)
        if dst == "-":
            sys.stdout.write(text)
        else:
            write_text_atomic(dst, text)
    err(f"clean-titledb: {n_changed} of {len(entries)} entries changed"
        + ("" if not n_changed else " -> " + ("stdout" if dst == "-" else dst)))
    for k in sorted(stats):
        err(f"  {k}: {stats[k]}")


# ---------------------------------------------------------------- reprocess-titledb

_GROUPS = {"base": "7001", "demo": "7003", "dlc": "7005", "bundle": "7007"}


class _Fetcher:
    """Batched alias lookups with bisection: a failing batch is split to isolate the rejected nsUids; if both
    halves then succeed the batch was too big and the size is lowered for the rest of the run."""

    def __init__(self, batch, op="Reprocess"):
        self.batch = batch
        self.op = op
        self.requests = 0
        self.failed = []
        self.successes = 0
        self.last_error = ""

    def call(self, query, variables):
        if self.requests:
            sleep_if()
        self.requests += 1
        try:
            r = rawreq(self.op, query, variables, store_language())
        except ApiError as e:
            self.last_error = str(e)
            return None
        if has_errors(r):
            first = (r.get("errors") or [{}])[0]
            self.last_error = f"{first.get('message')} {dig(first, 'extensions', 'errorCode') or ''}".strip()
            col = dig(first, "locations", 0, "column")
            if col:  # the offending part of the query
                self.last_error += f" at column {col}: {query[col - 1:col + 40]!r}"
            return None
        return r

    def fetch(self, chunk, fn):
        if fn(chunk):
            self.successes += 1
            return True
        if len(chunk) == 1:
            self.failed.append(chunk[0])
            err(f"  request failed for {chunk[0]}: {self.last_error}")
            if not self.successes and len(self.failed) >= 3:
                raise ApiError("the first requests all fail, so the query itself is rejected (see the error "
                               "above); stopping, nothing was fetched")
            return False
        mid = len(chunk) // 2
        ok_a = self.fetch(chunk[:mid], fn)
        ok_b = self.fetch(chunk[mid:], fn)
        if ok_a and ok_b and self.batch > mid:
            self.batch = max(1, mid)
            err(f"  batch of {len(chunk)} rejected ({self.last_error}); batch size now {self.batch}")
        return ok_a and ok_b


def _reprocess_load(src):
    """Input -> ({nsUid: old record}, is_dump). A titledb file / NDJSON of entries gives its own records; an old
    scrape-all dump (one base title per line with nested "dlc" / "demos" lists) gives records rebuilt from the
    little it holds (the fallback when the API returns nothing)."""
    if not os.path.isfile(src):
        raise ApiError(f"{src} not found")
    entries, _skipped = load_titledb_entries(src, keep="first")
    if entries:
        return {int(k): v for k, v in entries.items() if k.isdigit()}, False
    olds = {}
    with open(src, encoding="utf-8") as f:
        for line in f:
            try:
                b = json.loads(line)
            except ValueError:
                continue
            if not isinstance(b, dict) or b.get("nsUid") is None:
                continue
            parent = (b.get("titleId") or "").upper() or None
            rights = b.get("romRights") or ([{"titleId": b["titleId"]}] if b.get("titleId") else [])
            olds.setdefault(int(b["nsUid"]), titledb_record(
                {"nsUid": b["nsUid"], "formalName": b.get("name"), "releaseDateOnEshop": b.get("releaseDateOnEshop"),
                 "romRights": rights}, nsuid=int(b["nsUid"])))
            for d in b.get("dlc") or []:
                if isinstance(d, dict) and d.get("nsUid") is not None:
                    olds.setdefault(int(d["nsUid"]), titledb_record(
                        {"nsUid": d["nsUid"], "formalName": d.get("name"),
                         "romRights": [{"titleId": d["titleId"]}] if d.get("titleId") else []},
                        nsuid=int(d["nsUid"])))
            for d in b.get("demos") or []:
                if isinstance(d, dict) and d.get("nsUid") is not None:
                    olds.setdefault(int(d["nsUid"]), _with_parent_id(titledb_record(
                        {"nsUid": d["nsUid"], "formalName": d.get("name")}, nsuid=int(d["nsUid"])), parent))
    if not olds:
        raise ApiError(f"{src}: no titledb entries and no scrape-all dump lines found")
    return olds, True


def _keep_old(new, old):
    """A refreshed record never loses data: where the API gave nothing (null) but the old entry had a value
    (rightsId, version, iconUrl, key, parentId ...), the old value stays. Keys end up in titledb (sorted) order."""
    if not old:
        return new
    out = dict(new)
    for k, v in old.items():
        if out.get(k) is None and v is not None:
            out[k] = v
    return {k: out[k] for k in sorted(out)}


def reprocess_titledb(src, dst=None, nsuids=()):
    """Re-fetch entries of a titledb file (or an old scrape-all dump) and write them back in the current format.
      SCOPE    all (default) | base,demo,dlc,bundle (comma list): which entry types (nsUid prefix 7001/3/5/7)
      nsUids   (extra arguments) only these entries ("targeted"); they need not be in the input
      UPDATE=1 afterwards run update-titledb on the result (adds the newest titles that are missing)
      SLEEP    pause between requests, SECONDS or MIN-MAX (default 1-2); BATCH nsUids per request (25)
    Entries are looked up by nsUid with the type's own root field (applicationItem / demoItem / dlcItem /
    bundleItem), so no parent listing or title-ID search is needed. Entries not re-fetched stay untouched;
    entries the API does not return keep their old data. dst defaults to src (in place); an old dump needs an
    explicit dst. Progress is saved next to dst (.reprocess.ndjson), so an interrupted run resumes."""
    olds, is_dump = _reprocess_load(src)
    if dst is None:
        if is_dump:
            raise ApiError("an old scrape-all dump needs an output file: reprocess-titledb <dump> <titledb.json>")
        dst = src
    if not env("SLEEP"):
        os.environ["SLEEP"] = "1-2"
    names = [x for x in env("SCOPE", "all").lower().replace(" ", "").split(",") if x]
    bad = [x for x in names if x != "all" and x not in _GROUPS]
    if bad:
        raise ApiError(f"SCOPE: unknown {','.join(bad)} (use all or base,demo,dlc,bundle)")
    prefixes = set(_GROUPS.values()) if "all" in names else {_GROUPS[x] for x in names}

    if nsuids:
        if not all(str(n).isdigit() for n in nsuids):
            raise ApiError("targeted nsUids must be numbers")
        targets = sorted({int(n) for n in nsuids})
        unsupported = [n for n in targets if str(n)[:4] not in _GROUPS.values()]
        if unsupported:
            raise ApiError(f"no lookup for nsUid prefix of {unsupported[0]} (7001, 7003, 7005, 7007 only)")
    else:
        targets = sorted(n for n in olds if str(n)[:4] in prefixes)

    # entries the output starts from, then whatever an interrupted run already refreshed
    if os.path.isfile(dst):
        final, indent = _read_titledb(dst)
    elif is_dump:
        final, indent = {}, bool(env("PRETTY"))
    else:
        final, indent = {str(k): v for k, v in olds.items()}, bool(env("PRETTY"))
    sidecar = dst + ".reprocess.ndjson"
    done = {}
    if os.path.isfile(sidecar):
        done, _ = load_titledb_entries(sidecar, keep="last")
        final.update(done)
        err(f"resuming: {len(done)} entries already refreshed ({sidecar})")
    err(f"reprocess: {len(targets)} entries to refresh" + ("" if nsuids else f" (SCOPE={','.join(names)})")
        + (f", {len([n for n in targets if str(n) in done])} already done" if done else ""))

    fetcher = _Fetcher(max(1, int(env("BATCH", "25"))))
    stats = {}  # prefix -> [refreshed, kept old, from old data only]
    t0 = time.time()
    tty = sys.stderr.isatty()
    out = open(sidecar, "a", encoding="utf-8")
    try:
        for prefix in sorted(prefixes if not nsuids else {str(n)[:4] for n in targets}):
            todo = [n for n in targets if str(n)[:4] == prefix and str(n) not in done]
            if not todo:
                continue
            sel = _APP_SEL if prefix == "7001" else _scan_target(prefix)[1]
            root = _scan_target(prefix)[0]
            st = stats.setdefault(prefix, [0, 0, 0])
            i = 0
            nchunk = 0
            while i < len(todo):
                chunk = todo[i:i + fetcher.batch]
                i += len(chunk)
                nchunk += 1
                got = {}

                def fn(c):
                    q, qv = alias_apps_query("Reprocess", c, sel, root)
                    r = fetcher.call(q, qv)
                    if r is None:
                        return False
                    data = dig(r, "data", "item") or {}
                    for k, n in enumerate(c):
                        got[n] = data.get(f"a{k}")
                    return True

                fetcher.fetch(chunk, fn)
                for n in chunk:
                    row, old = got.get(n), olds.get(n)
                    if row:
                        rec = titledb_record(row, nsuid=n)
                        if prefix == "7003":  # the lookup does not say which title a demo belongs to
                            rec = _with_parent_id(rec, (old or {}).get("parentId"))
                        rec = _keep_old(rec, old)
                        final[str(n)] = rec
                        out.write(compact({str(n): rec}) + "\n")
                        st[0] += 1
                    elif is_dump and old:  # nothing from the API: the entry rebuilt from the old dump
                        final[str(n)] = old
                        out.write(compact({str(n): old}) + "\n")
                        st[2] += 1
                    else:
                        st[1] += 1
                out.flush()
                if not env("QUIET") and (tty or nchunk % 10 == 0):
                    d = min(i, len(todo))
                    eta = (time.time() - t0) / max(1, sum(x[0] + x[1] + x[2] for x in stats.values())) * (len(todo) - d)
                    msg = f"[{_GROUPS_REV[prefix]}] {d}/{len(todo)}  elapsed {_hms(time.time() - t0)}  eta {_hms(eta)}"
                    print(("\r" + msg + "\033[K") if tty else msg, end="" if tty else "\n", file=sys.stderr, flush=True)
            if tty:
                err()
    except KeyboardInterrupt:
        out.close()
        err(f"\ninterrupted; progress kept in {sidecar}. Re-run the same command to resume.")
        raise SystemExit(130)
    finally:
        if not out.closed:
            out.close()

    write_text_atomic(dst, titledb_text(sort_entries(final), indent))
    if os.path.isfile(sidecar):
        os.remove(sidecar)
    for prefix, (n, kept, fb) in stats.items():
        err(f"{_GROUPS_REV[prefix]}: {n} refreshed" + (f", {kept} kept as they were (API returned nothing)" if kept else "")
            + (f", {fb} from the old dump only" if fb else ""))
    if fetcher.failed:
        err(f"{len(fetcher.failed)} nsUid(s) the API rejected outright")
    err(f"reprocess-titledb: {len(final)} entries -> {dst} ({fetcher.requests} requests)")
    if env("UPDATE"):
        update_titledb(dst)


_GROUPS_REV = {v: k for k, v in _GROUPS.items()}


# ---------------------------------------------------------------- Simba compatibility (replaces a shogun client)
#
# The bugyo/shogun REST API is gone. The camelCase functions below keep a shogun client's names, arguments and return
# shapes as Simba JSON (the legacy shogun format that nut's Title.parseSimbaJson reads), built from Savanna data.
# They are pure library code: nothing here imports nut (nut's Titles-filling scrape functions live in nut/Eshop.py),
# e.g.
#   title.parseSimbaJson(simba.getTitleByNsuid(nsuid, 'US', 'en'), 'US', 'en')
# region / language are the legacy ones ("US", "en"); shop_id and force are accepted and ignored (Savanna uses SHOP,
# there is no disk cache). Lookups return None where Shogun returned None (error / unknown nsUid).

def savanna_language(region, language):
    """Legacy language ("en") -> the code the store of `region` lists in availableLanguages ("en" or "en_GB"): an
    exact match, else the first code with the same prefix; the input itself if nothing matches."""
    if not language:
        return language
    c = country_of(region) or {}
    codes = [l.get("code") for l in c.get("availableLanguages") or [] if isinstance(l, dict) and l.get("code")]
    if language in codes:
        return language
    want = language.split("_")[0].lower()
    return next((code for code in codes if code.split("_")[0].lower() == want), language)


def store_language():
    """Language for item lookups: the store's own code for LANG_CODE ("en" -> "en_CA" in CA, "ja" in JP), or the
    simba_context language. Lookups ignore any code the store does not list (even "xx_YY" is accepted) and answer in
    the store default, so "en_US" outside the US store silently gave the default; confirmed live (CA + fr_CA is
    French, CA + fr / en_US is English). searchV4 is the opposite: it needs the short code, not this one."""
    return _ctx_get("language") or savanna_language(_ctx_get("country") or COUNTRY, LANG_CODE)


@contextmanager
def simba_context(region=None, language=None, map_language=True):
    """Requests made inside the block (this thread only) go to store `region` in `language` (savanna_language; as
    given with map_language=False), and searchV4 uses the region's regionCode. Nests; the previous context is
    restored on exit."""
    prev = getattr(_ctx, "v", None)
    v = {}
    if region:
        v["country"] = region
        rc = (country_of(region) or {}).get("regionCode")
        if rc:
            v["region"] = rc
    if language:
        v["language"] = savanna_language(region or COUNTRY, language) if map_language else language
    _ctx.v = v
    try:
        yield
    finally:
        _ctx.v = prev


def _date_dashed(app):
    d = release_date_int(app)
    return f"{d // 10000:04d}-{d // 100 % 100:02d}-{d % 100:02d}" if d else None


def simba_json(app, nsuid=None):
    """Savanna item dict (application / demo / DLC / bundle) -> Simba JSON, the legacy shogun format that
    Title.parseSimbaJson reads. Keys without data are left out (parseSimbaJson tests `in`); text is cleaned as in titledb_record.
    Extra keys read by the scrape functions: "id" (nsUid), "applications" [{id, image_url}] (applications only),
    "title_ids" [{id}] (DLC), "demos" [{id}] (applications). "target_titles" is never emitted."""
    if not isinstance(app, dict):
        return None
    ns = app.get("nsUid") if app.get("nsUid") is not None else nsuid
    dlc_, bundle = is_dlc(app, ns), is_bundle(app, ns)
    demo = is_demo_nsuid(ns) or app.get("__typename") == "DemoItem"
    j = {}

    def put(k, v):
        if v not in (None, "", [], {}):
            j[k] = v

    put("id", int(ns) if ns is not None else None)
    put("formal_name", _text_or_none(app.get("formalName") or app.get("name"), False))
    put("hero_banner_url", img_url(app.get("heroBannerUrl")))
    put("release_date_on_eshop", _date_dashed(app))
    put("screenshots", [{"images": [{"url": u}]} for u in (img_url(p) for p in app.get("screenshotUrls") or []) if u])
    if not bundle:
        put("languages", [{"iso_code": c} for c in language_codes(app)])
    put("genre", " / ".join(genre(app)))
    put("total_rom_size", rom_size(app))

    rating = {}
    age = rating_age(app)
    if age is not None:
        rating["rating"] = {"age": age}
    content = rating_content(app)
    if content or bundle:  # titledb bundles carry ratingContent [] rather than null
        rating["content_descriptors"] = [{"name": n} for n in content or []]
    if rating:
        j["rating_info"] = rating

    pn = app.get("playerNumber")
    if isinstance(pn, dict):  # parseSimbaJson: offline_max overrides local_max (= player_number_max)
        local = pn.get("localMax") if pn.get("localMax") is not None else pn.get("localMin")
        offline = pn.get("offlineMax") if pn.get("offlineMax") is not None else pn.get("offlineMin")
        if local is None and offline is None:
            local = pn.get("onlineMax") if pn.get("onlineMax") is not None else pn.get("onlineMin")
        players = {}
        if local is not None:
            players["local_max"] = local
        if offline is not None:
            players["offline_max"] = offline
        put("player_number", players)

    pub = _text_or_none(publisher_name(app), False)
    if pub:
        j["publisher"] = {"name": pub}

    tid = title_id(app)
    if not (dlc_ or bundle or demo):
        apps = []
        for a in app.get("applications") or []:
            if isinstance(a, dict) and a.get("id"):
                e = {"id": str(a["id"]).upper()}
                if a.get("imageUrl"):
                    e["image_url"] = img_url(a["imageUrl"])
                apps.append(e)
        if not apps and tid:
            apps = [{"id": tid}]
        apps.sort(key=lambda e: e["id"] != tid)  # the titledb id (romRights first) leads, as titledb_record picks it
        put("applications", apps)
    if dlc_:
        tids = []
        for r in app.get("romRights") or []:
            t = str(r.get("titleId") or "").upper() if isinstance(r, dict) else ""
            if t and not t.endswith("800") and t not in tids:
                tids.append(t)
        put("title_ids", [{"id": t} for t in tids])

    put("catch_copy", _text_or_none(app.get("catchCopy") or None))
    put("description", _text_or_none(app.get("description")))
    if not (dlc_ or bundle or demo):
        put("demos", [{"id": int(d["nsUid"])} for d in app.get("demoItems") or []
                      if isinstance(d, dict) and d.get("nsUid") is not None])
    return j


def _lookup_target(prefix):
    """nsUid prefix -> (root field, selection) for a full single-item lookup."""
    if prefix == "7003":
        return "demoItem", "__typename nsUid formalName " + demo_lookup_selection()
    if prefix in ("7005", "7007"):
        return _scan_target(prefix)
    return "applicationItem", _APP_SEL + " demoItems { nsUid }"


def _lookup(nsuid, prefix=None):
    """One item by nsUid with the root field of its prefix (or `prefix`) -> dict, or None (error / not found)."""
    root, sel = _lookup_target(prefix or str(int(nsuid))[:4])
    q, qv = alias_apps_query("Lookup", [int(nsuid)], sel, root)
    try:
        r = rawreq("Lookup", q, qv, store_language())
    except ApiError as e:
        err(f"lookup {nsuid}: {e}")
        return None
    if has_errors(r):
        first = (r.get("errors") or [{}])[0]
        err(f"lookup {nsuid}: {first.get('message')} {dig(first, 'extensions', 'errorCode') or ''}".rstrip())
        return None
    return dig(r, "data", "item", "a0")


# extra fields (known to exist, not used by titledb). Also the full form of fields titledb reads only part of
# (ratingInfo / publisher: titledb selects age + contentDescriptors / name), and fields
# dropped from the titledb queries as unused (itemType, labelPlatform, publicStatus, isNew, isMembershipRequired),
# so every field found to exist stays listed and fetchable with `extra`. All confirmed live.

_X_DOMINANTCOLORS = 'dominantColors { backgroundColor textColor1 textColor2 }'
_X_ITEMSTATUSES = 'itemStatuses { bee { publicStatus salesStatus } hac { publicStatus salesStatus } }'
_X_MOVIES = 'movies { ... on EshopMovie { movieUrl thumbnailUrl } ... on NemoMovie { isInline movieMetaId } }'
_X_NOTICES = 'notices { text type }'
_X_PRICE = 'price { nsUid discountPrice { currency endDatetime formattedValue id rawValue startDatetime } giftGoldPoints { basic { point rate } conditionals { applicableCondition endDatetime id startDatetime targetScope totalPoint } extra { applicableCondition endDatetime id startDatetime targetScope totalPoint } total { point rate } } itemStatuses { bee { publicStatus salesStatus } hac { publicStatus salesStatus } } monthlyPrice { currency formattedValue rawValue } preOrderInfoV2 { isDownloadReady settlementDate } purchaseTimeLimitV2 { endDatetime limitCount remainingCount } regularPrice { currency formattedValue id rawValue } tradeDiscountRates { currency id ticketItemGroupId unitMinutes value } }'
_X_PRICEV2 = 'priceV2 { hasOwnerDiscountPrice nsUid itemStatuses { bee { publicStatus salesStatus } hac { publicStatus salesStatus } } monthlyPrice { currency formattedValue rawValue } preOrderInfoV2 { isDownloadReady settlementDate } purchaseTimeLimitV3 { endDatetime limitCount } regularPrice { currency formattedValue id rawValue } termDiscountPrice { currency endDatetime formattedValue id rawValue startDatetime } tradeDiscountRates { currency id ticketItemGroupId unitMinutes value } }'
_X_RATINGINFO = 'ratingInfo { rating { id name age svgImageUrl } ratingSystem { id } contentDescriptors { name } }'  # the selection titledb queries carried before trimming
_X_TAGS = 'tags { name subCategoryId tagId subCategory { categoryId name subCategoryId tagIds } }'
_X_UPGRADEINFO = 'upgradeInfo { baseApplicationItemNsUid upgradeApplicationItemNsUid upgradeDlcItemNsUid }'

EXTRA_FIELDS = {
    "application": {
        "accessoryDescription": 'accessoryDescription',
        "classicGameType": 'classicGameType',
        "cloudBackupType": 'cloudBackupType',
        "copyrightText": 'copyrightText',
        "disclaimer": 'disclaimer',
        "dominantColors": _X_DOMINANTCOLORS,
        "features": 'features { id imageUrl name }',
        "freePlayDeliveryInfos": 'freePlayDeliveryInfos { freePlayType isFeatureLimited nsUid requiredMembershipType dlTerm { end start } playTerm { end start } promotion { description } }',
        "includedCatalogTicketIds": 'includedCatalogTicketIds',
        "isFreeForExMembership": 'isFreeForExMembership',
        "isInAppPurchase": 'isInAppPurchase',
        "isMembershipRequired": 'isMembershipRequired',
        "isNew": 'isNew',
        "itemStatuses": _X_ITEMSTATUSES,
        "itemType": 'itemType',
        "labelPlatform": 'labelPlatform',
        "miscDescription": 'miscDescription',
        "movies": _X_MOVIES,
        "networkFeatureDescription": 'networkFeatureDescription',
        "notices": _X_NOTICES,
        "playStyles": 'playStyles { id imageUrl name }',
        "playerNumberDescription": 'playerNumberDescription',
        "price": _X_PRICE,
        "priceV2": _X_PRICEV2,
        "publicStatus": 'publicStatus',
        "publisher": 'publisher { id name }',
        "ratingInfo": _X_RATINGINFO,
        "relatedItems": 'relatedItems { itemType nsUid }',
        "strongDisclaimer": 'strongDisclaimer',
        "tagIds": 'tagIds',
        "tags": _X_TAGS,
        "upgradeDescription": 'upgradeDescription',
        "upgradeInfo": _X_UPGRADEINFO,
    },
    "demo": {
        "isFreeForExMembership": 'isFreeForExMembership',
        "itemType": 'itemType',
        "labelPlatform": 'labelPlatform',
        "price": _X_PRICE,
        "priceV2": _X_PRICEV2,
        "publicStatus": 'publicStatus',
        "publisher": 'publisher { id name }',
        "tagIds": 'tagIds',
        "tags": _X_TAGS,
    },
    "dlc": {
        "catchCopy": 'catchCopy',
        "copyrightText": 'copyrightText',
        "disclaimer": 'disclaimer',
        "dominantColors": _X_DOMINANTCOLORS,
        "isFreeForExMembership": 'isFreeForExMembership',
        "isMembershipRequired": 'isMembershipRequired',
        "isNew": 'isNew',
        "isUpgrade": 'isUpgrade',
        "itemStatuses": _X_ITEMSTATUSES,
        "labelPlatform": 'labelPlatform',
        "movies": _X_MOVIES,
        "notices": _X_NOTICES,
        "price": _X_PRICE,
        "priceV2": _X_PRICEV2,
        "publicStatus": 'publicStatus',
        "publisher": 'publisher { id name }',
        "ratingInfo": _X_RATINGINFO,
        "strongDisclaimer": 'strongDisclaimer',
        "tagIds": 'tagIds',
        "tags": _X_TAGS,
        "upgradeDescription": 'upgradeDescription',
        "upgradeInfo": _X_UPGRADEINFO,
    },
    "bundle": {
        "copyrightText": 'copyrightText',
        "disclaimer": 'disclaimer',
        "dominantColors": _X_DOMINANTCOLORS,
        "hasUnreleasedItems": 'hasUnreleasedItems',
        "isFreeForExMembership": 'isFreeForExMembership',
        "isMembershipRequired": 'isMembershipRequired',
        "isNew": 'isNew',
        "itemStatuses": _X_ITEMSTATUSES,
        "itemType": 'itemType',
        "labelPlatform": 'labelPlatform',
        "movies": _X_MOVIES,
        "notices": _X_NOTICES,
        "price": _X_PRICE,
        "priceV2": _X_PRICEV2,
        "publicStatus": 'publicStatus',
        "ratingInfo": 'ratingInfo { rating { id name age svgImageUrl } ratingSystem { id } }',
        "strongDisclaimer": 'strongDisclaimer',
        "tagIds": 'tagIds',
        "tags": _X_TAGS,
    },
    "country": {
        "balanceLimit": 'balanceLimit { currency formattedValue rawValue }',
        "caTaxLocations": 'caTaxLocations { geoCode state }',
        "currency": 'currency',
        "goldPointExchangeRate": 'goldPointExchangeRate',
        "id": 'id',
        "isCreditCardAvailable": 'isCreditCardAvailable',
        "isKakaopayAvailable": 'isKakaopayAvailable',
        "isPaypalAvailable": 'isPaypalAvailable',
        "isPrepaidCardAvailable": 'isPrepaidCardAvailable',
        "isTaxExcludedCountry": 'isTaxExcludedCountry',
        "isTaxFreeCountry": 'isTaxFreeCountry',
        "isoCode": 'isoCode',
        "minimumCurrencyUnit": 'minimumCurrencyUnit',
        "name": 'name',
        "priceFormat": 'priceFormat { negativePrefix negativeSuffix positivePrefix positiveSuffix formats { patternId formats { digit format } } }',
        "replenishAmounts": 'replenishAmounts { currency formattedValue rawValue }',
    },
}

_EXTRA_ROOT = {"7001": ("application", "applicationItem"), "7003": ("demo", "demoItem"),
               "7005": ("dlc", "dlcItem"), "7007": ("bundle", "bundleItem")}


def extra_fields(kind=None):
    """Field names in EXTRA_FIELDS: {kind: [names]}, or the list of one kind (application demo dlc bundle country)."""
    if kind:
        if kind not in EXTRA_FIELDS:
            raise ApiError(f"unknown kind {kind!r} (one of {', '.join(EXTRA_FIELDS)})")
        return sorted(EXTRA_FIELDS[kind])
    return {k: sorted(v) for k, v in EXTRA_FIELDS.items()}


def _extra_run(kind, names, run_query, label):
    """Fetch `names` with run_query(selection) -> row dict or None (error); a failing group is split until the
    field that fails is alone. -> {name: value}; None for a field that errors."""
    table, res = EXTRA_FIELDS[kind], {}

    def go(group):
        row = run_query(" ".join(table[n] for n in group))
        if row is not None:
            for n in group:
                res[n] = row.get(n)
        elif len(group) == 1:
            res[group[0]] = None
        else:
            mid = len(group) // 2
            go(group[:mid])
            go(group[mid:])

    go(list(names))
    return res


def _extra_names(kind, fields):
    names = list(fields) if fields else list(EXTRA_FIELDS[kind])
    bad = [n for n in names if n not in EXTRA_FIELDS[kind]]
    if bad:
        raise ApiError(f"not an extra {kind} field: {', '.join(bad)} (extra-fields {kind} lists them)")
    return names


def item_extra(nsuid, fields=None, region=None, language=None):
    """The extra fields (all, or the names in `fields`) of one item; the root follows the nsUid prefix
    (7001 application, 7003 demo, 7005 DLC, 7007 bundle). -> {field: value}; None where the server errors."""
    kind, root = _EXTRA_ROOT.get(str(int(nsuid))[:4], _EXTRA_ROOT["7001"])
    names = _extra_names(kind, fields)

    def run_query(sel):
        q, qv = alias_apps_query("Extra", [int(nsuid)], sel, root)
        try:
            with simba_context(region, language):
                r = rawreq("Extra", q, qv, store_language())
        except ApiError as e:
            err(f"extra {nsuid}: {e}")
            return None
        return None if has_errors(r) else (dig(r, "data", "item", "a0") or {})

    return _extra_run(kind, names, run_query, nsuid)


def country_extra(fields=None, region=None, language=None):
    """The extra fields of the store (`country`: currency, price format, payment methods, tax flags ...) -> {field: value}."""
    names = _extra_names("country", fields)

    def run_query(sel):
        q = ("query CountryExtra($shopId: Int!, $country: CountryCode!, $language: LanguageCode!) "
             "@inContext(shopId: $shopId, country: $country, language: $language) { country { " + sel + " } }")
        try:
            with simba_context(region, language):
                r = rawreq("CountryExtra", q, {}, store_language())
        except ApiError as e:
            err(f"extra country: {e}")
            return None
        return None if has_errors(r) else (dig(r, "data", "country") or {})

    return _extra_run("country", names, run_query, "country")


def _snake(s):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()


def __getattr__(name):
    """get_<kind>_<field_in_snake_case>: get_application_play_styles(nsuid), get_dlc_price_v2(nsuid),
    get_country_currency(). One function per extra field, made on demand."""
    m = re.fullmatch(r"get_(application|demo|dlc|bundle|country)_(\w+)", name)
    if m:
        field = {_snake(f): f for f in EXTRA_FIELDS[m.group(1)]}.get(m.group(2))
        if field:
            if m.group(1) == "country":
                return lambda region=None, language=None: country_extra([field], region, language).get(field)
            return lambda nsuid, region=None, language=None: item_extra(nsuid, [field], region, language).get(field)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")



def country(region="US", shop_id=4):
    """Legacy shogun/v1/country: {region_code, default_language_code, available_language_codes} (short codes,
    "en" not "en_US"), or None."""
    c = country_of(region)
    if c is None:
        return None
    return {"region_code": c.get("regionCode"),
            "default_language_code": country_language(region),
            "available_language_codes": country_languages(region)}


def countryLanguage(region="US"):
    return country_language(region)


def countryLanguages(region="US"):
    return country_languages(region)


def saveLanguages(fileName="titledb/languages.json"):
    save_languages(fileName)


def saveRegions(fileName="titledb/cdn.regions.json"):
    save_regions(fileName)


def getTitleByNsuid(nsuId, region="US", language="en", shop_id=3, force=False):
    """Any item by nsUid (7001 application, 7003 demo, 7005 DLC, 7007 bundle; others as application) -> Simba JSON."""
    with simba_context(region, language):
        return simba_json(_lookup(nsuId), nsuid=int(nsuId))


def getDlcByNsuid(nsuId, region="US", language="en", shop_id=3, force=False):
    """DLC by nsUid -> Simba JSON (always looked up as dlcItem, as shogun's /aocs/ endpoint)."""
    with simba_context(region, language):
        return simba_json(_lookup(nsuId, "7005"), nsuid=int(nsuId))


def getAocs(baseNsuid, region="US", language="en", shop_id=3, force=False, first_page=None):
    """Legacy titles/{nsUid}/aocs: {"contents": [Simba JSON of each DLC, with "id"], "total": n}. Full DLC data, so
    no getDlcByNsuid per entry is needed; same DLC set as scrape-title. first_page: see _collect_dlc."""
    with simba_context(region, language):
        contents = [simba_json(m) for m in _collect_dlc(baseNsuid, first_page)]
    return {"contents": contents, "total": len(contents)}


def searchPage(language="en", region="US", page=1, per_page=None):
    """Legacy wg/v1/search page (newest first, PLATFORM, on sale or pre-order): {"contents": [Simba JSON + "ns_uid"],
    "total", "total_pages", "page", "per_page"}, or None on error. page is 1-based (<= 1 = first page); per_page
    defaults to LIMIT (SEARCH_LIMIT, 100), the search page size used everywhere else. searchV4 does not page past offset 999, so
    total_pages covers at most the newest 1000 items."""
    page = max(1, int(page))
    per_page = int(per_page) if per_page is not None else int(env("LIMIT", str(SEARCH_LIMIT)))
    # searchV4 matches nothing for a region-qualified language ("en_US" -> 0 items, confirmed live) while item lookups
    # need the store's own code (store_language), so the context sets only the store / regionCode here and the search
    # gets the short code.
    with simba_context(region):
        variables = _search_vars("ONSALE_OR_PRE_ORDER", "RELEASE_DATE_DESC", "", env("PLATFORM", "HAC"), per_page)
        try:
            r = rawreq("Search", q_search_app(), {**variables, "offset": (page - 1) * per_page},
                       (language or LANG_CODE).split("_")[0])
        except ApiError as e:
            err(f"search page {page}: {e}")
            return None
    if has_errors(r):
        first = (r.get("errors") or [{}])[0]
        err(f"search page {page}: {first.get('message')}")
        return None
    total = dig(r, "data", "searchV4", "offsetInfo", "total") or 0
    contents = []
    for it in emit_search_items(r):
        if isinstance(it, dict) and it.get("nsUid") is not None:
            contents.append({**simba_json(it), "ns_uid": int(it["nsUid"])})
    return {"contents": contents, "total": total, "total_pages": -(-min(int(total), 1000) // per_page),
            "page": page, "per_page": per_page}


def getLatest(language="en", region="US", cont="NA", force=False):
    """Newest search page (cont is ignored: the search region is the regionCode of `region`)."""
    return searchPage(language, region, 1)


def ids(titleIds, type="title", region="US", language="en", shop_id=4, force=False):
    """Legacy contents/ids: title IDs (list or comma string) -> {"id_pairs": [{"title_id", "id"}]} via
    itemsByTitleIdsV2 (type "title" = APPLICATION, "aoc" = DLC; public items only), or None on error."""
    wanted = [t.strip().upper() for t in (titleIds.split(",") if isinstance(titleIds, str) else titleIds) if t.strip()]
    kind, frag = ("DLC", "DlcItem") if str(type).lower() in ("aoc", "aocs", "dlc") else ("APPLICATION", "ApplicationItem")
    label = ",".join(wanted) if len(wanted) <= 3 else f"{len(wanted)} title IDs ({wanted[0]}..{wanted[-1]})"
    q = ("query TitleIds($shopId: Int!, $country: CountryCode!, $language: LanguageCode!, $titleIds: [TitleId!]!) "
         "@inContext(shopId: $shopId, country: $country, language: $language) { item { itemsByTitleIdsV2("
         f"titleIds: $titleIds, publicStatuses: [PUBLIC], selectFirst: false, type: {kind}) "
         f"{{ nsUid itemV2 {{ ... on {frag} {{ romRights {{ titleId }} }} }} }} }} }}")
    with simba_context(region, language):
        try:
            r = rawreq("TitleIds", q, {"titleIds": wanted})
        except ApiError as e:
            err(f"ids {label}: {e}")
            return None
    if has_errors(r):
        first = (r.get("errors") or [{}])[0]
        err(f"ids {label}: {first.get('message')}")
        return None
    pairs = []
    for row in dig(r, "data", "item", "itemsByTitleIdsV2") or []:
        if not isinstance(row, dict) or row.get("nsUid") is None:
            continue
        rights = [str(x.get("titleId")).upper() for x in dig(row, "itemV2", "romRights") or []
                  if isinstance(x, dict) and x.get("titleId")]
        tid = next((t for t in rights if t in wanted), None)
        if tid is None:
            tid = wanted[0] if len(wanted) == 1 else (rights[0] if rights else None)
        if tid:
            pairs.append({"title_id": tid, "id": int(row["nsUid"])})
    return {"id_pairs": pairs}


# itemsByTitleIdsV2 batch size: title IDs the server has not looked up recently fail above ~225 per request (250
# rejected at once with error 5200 UNKNOWN_ERROR; recently looked-up IDs pass up to ~480), confirmed live; 200 leaves a
# margin and idsBatched splits a rejected batch anyway. The id pairs do not depend on the language (confirmed live),
# so one lookup per store serves all its languages.
IDS_BATCH = 200


def idsBatched(titleIds, type="title", region="US", language="en", batch=None, label=None):
    """ids() for any number of title IDs, IDS_BATCH (200) per request -> {"id_pairs": [...]}. A rejected batch (e.g.
    a malformed ID) is split in halves until the bad ID is alone; that ID is reported and skipped. label: progress
    on stderr ("<label>: 2000/27007 title ids looked up, ...") every 10 batches and at the end."""
    batch = max(1, int(batch or env("IDS_BATCH", str(IDS_BATCH))))
    wanted = [t.strip().upper() for t in (titleIds.split(",") if isinstance(titleIds, str) else titleIds) if t.strip()]
    pairs = []

    def go(chunk):
        r = ids(chunk, type, region, language)
        if r is not None:
            pairs.extend(r["id_pairs"])
        elif len(chunk) > 1:
            go(chunk[:len(chunk) // 2])
            go(chunk[len(chunk) // 2:])

    total, start = len(wanted), time.time()
    for i in range(0, total, batch):
        go(wanted[i:i + batch])
        done = min(i + batch, total)
        if label and (done % (batch * 10) == 0 or done == total):
            err(f"{label}: {done}/{total} title ids looked up, {len(pairs)} found ({time.time() - start:.0f}s)")
    return {"id_pairs": pairs}


# Batched application fetches for scraping many titles (nut's Eshop.scrapeNsuids is built on this). Applications are
# fetched SCRAPE_BATCH per request (aliases, as reprocess-titledb), each with its first SCRAPE_DLC_LIMIT dlcItems rows
# and its demoItems nsUids. The API rejects such a query above ~18 applications (error 1806, extensions.title
# QUERY_COST_LIMIT_EXCEEDED, confirmed live with 25-row DLC pages), so the default is 15; a rejected batch is split
# and the size lowered (_Fetcher).
SCRAPE_DLC_LIMIT = 25


def _scrape_batch_selection():
    ss = env("SCRAPE_SALES_STATUSES", "ONSALE,PRE_ORDER,SALES_TERMINATION,UNRELEASED")
    ps, ib = env("PUBLIC_STATUSES", "PUBLIC"), env("INCLUDE_BUNDLES", "true")
    if not (re.fullmatch(r"[A-Z_,]+", f"{ps},{ss}") and re.fullmatch(r"true|false", ib)):
        raise ApiError("invalid PUBLIC_STATUSES / SCRAPE_SALES_STATUSES / INCLUDE_BUNDLES")
    return _APP_SEL + " demoItems { nsUid } " + dlc_items_selection(0, SCRAPE_DLC_LIMIT, ps, ss, ib)


def fetch_apps(nsuids, region=None, language=None):
    """applicationItems for many application nsUids (7001...), SCRAPE_BATCH (15) per request. Yields, batch by batch
    in input order, (nsUid, row, ok): row is the applicationItem dict (simba_json takes it; row["dlcItems"]["items"]
    is its first SCRAPE_DLC_LIMIT DLC rows, the `first_page` of getAocs / _collect_dlc) or None when the store has no
    such application; ok is False for an nsUid the API rejected even on its own (row None; a single lookup reports
    why). region / language as in simba_context (legacy "US", "en"); None = COUNTRY / LANG_CODE."""
    fetcher = _Fetcher(max(1, int(env("SCRAPE_BATCH", "15"))), op="ScrapeBatch")
    sel = _scrape_batch_selection()
    nsuids = [int(n) for n in nsuids]
    i = 0
    while i < len(nsuids):
        chunk = nsuids[i:i + fetcher.batch]
        i += len(chunk)
        got = {}

        def fn(c):
            q, qv = alias_apps_query("ScrapeBatch", c, sel, "applicationItem")
            r = fetcher.call(q, qv)
            if r is None:
                return False
            data = dig(r, "data", "item") or {}
            for k, n in enumerate(c):
                got[n] = data.get(f"a{k}")
            return True

        with simba_context(region, language):  # not held across the yields below
            fetcher.fetch(chunk, fn)
        for n in chunk:
            yield n, got.get(n), n in got


def fetch_items(nsuids, region=None, language=None):
    """Any items by nsUid (7001 application, 7003 demo, 7005 DLC, 7007 bundle), BATCH (25) per request with the root
    field and selection of each prefix (the same data as getTitleByNsuid, one request per batch instead of per item).
    Yields (nsUid, row, ok) as fetch_apps does, grouped by prefix in input order."""
    groups = {}
    for n in nsuids:
        n = int(n)
        p = str(n)[:4] if str(n)[:4] in ("7003", "7005", "7007") else "7001"
        groups.setdefault(p, []).append(n)
    fetcher = _Fetcher(max(1, int(env("BATCH", "25"))), op="LookupBatch")
    for prefix, todo in groups.items():
        root, sel = _lookup_target(prefix)
        i = 0
        while i < len(todo):
            chunk = todo[i:i + fetcher.batch]
            i += len(chunk)
            got = {}

            def fn(c):
                q, qv = alias_apps_query("LookupBatch", c, sel, root)
                r = fetcher.call(q, qv)
                if r is None:
                    return False
                data = dig(r, "data", "item") or {}
                for k, n in enumerate(c):
                    got[n] = data.get(f"a{k}")
                return True

            with simba_context(region, language):
                fetcher.fetch(chunk, fn)
            for n in chunk:
                yield n, got.get(n), n in got


# latestNsuids results per (store, platform, count): the list does not depend on the language (confirmed live, US
# en/es and CA en/fr), so a store's other languages reuse it. Kept LATEST_CACHE_SECONDS (3600).
_latest_cache = {}


def latestNsuids(language="en", region="US"):
    """The newest titles of one store/language, listed as scrape-all-latest lists them: one searchV4 walk over every
    page (offsets of LIMIT up to 1000), deduped by nsUid, newest LATEST_COUNT (1000) -> [nsUid, ...], or None if the
    search failed. The search gets the short language code (it matches nothing for "en_US"). Cached per store
    (_latest_cache)."""
    key = (region, env("PLATFORM", "HAC"), int(env("LATEST_COUNT", "1000")))
    hit = _latest_cache.get(key)
    if hit and time.time() - hit[0] < float(env("LATEST_CACHE_SECONDS", "3600")):
        return list(hit[1])
    with simba_context(region, (language or LANG_CODE).split("_")[0], map_language=False):
        try:
            items = list(itertools.islice(dedupe_nsuid(search(
                0, sales="ONSALE_OR_PRE_ORDER", sort="RELEASE_DATE_DESC", freeword="", platform=env("PLATFORM", "HAC"),
                all_pages=True, quiet=True, ids_only=True)), int(env("LATEST_COUNT", "1000"))))
        except ApiError as e:
            err(f"{region} {language}: search failed" + (f": {e}" if str(e) else ""))
            return None
    res = [int(it["nsUid"]) for it in items]
    _latest_cache[key] = (time.time(), res)
    return list(res)


def simba_cli(a):
    """`simba <what> ...`: print the Simba JSON the compatibility functions build (store COUNTRY, language LANG_CODE)."""
    what, rest = (a[0], a[1:]) if a else ("", [])
    need = {"title": 1, "dlc": 1, "aocs": 1, "ids": 1}
    if what not in ("title", "dlc", "aocs", "latest", "ids", "country") or len(rest) < need.get(what, 0):
        usage()
    if what in ("title", "dlc", "aocs") and not rest[0].isdigit():
        raise ApiError("nsUid must be a number")
    if what == "title":
        res = getTitleByNsuid(int(rest[0]), COUNTRY, LANG_CODE)
    elif what == "dlc":
        res = getDlcByNsuid(int(rest[0]), COUNTRY, LANG_CODE)
    elif what == "aocs":
        res = getAocs(int(rest[0]), COUNTRY, LANG_CODE)
    elif what == "latest":
        res = searchPage(LANG_CODE, COUNTRY, int(rest[0]) if rest else 1)
    elif what == "ids":
        res = ids(",".join(rest), env("TYPE", "title"), COUNTRY, LANG_CODE)
    else:
        res = country(rest[0] if rest else COUNTRY)
    if res is None:
        raise ApiError(f"simba {what}: no result")
    out(res)


# ---------------------------------------------------------------- CLI

def usage():
    err(f"""usage: {sys.argv[0]} <command> [args]
  country                     shop/country info (regionCode, languages, shop status)
  regions                     list REGIONS, one per line
  language [CC]               default language code of country CC (default COUNTRY; 'en' on error)
  languages [CC]              available language codes of CC, JSON array
  save-languages [file]       {{country: [languages]}} for all REGIONS (titledb/languages.json)
  save-regions [file]         {{regionCode: [countries]}} for all REGIONS (titledb/cdn.regions.json)
  item <nsUid> [language]     application item by nsUid (default: the store's code for LANG_CODE)
  title <titleId>...          application items by title ID
  extra <nsUid|country> [field...]  fields the schema has that nothing else here uses (all, or the named ones)
  extra-fields [kind]         list them (application demo dlc bundle country)
  fields <nsUid> [name...]    probe which field names exist on item.applicationItem / demoItem / dlcItem /
                              bundleItem (by nsUid prefix 7001/7003/7005/7007; ROOT=<field> overrides)
                              (PARENT=relatedItems fields ... probes inside a field)
  dlc-fields <titleId> [name...]  probe which field names exist on DlcItem (set DLC_RECORD_FIELDS to trim)
  lookup-probe [name...]      which item {{ <field>(nsUid: N) }} root fields exist (demo/DLC/bundle lookup by nsUid)
  bundle-fields [name...]     probe which field names exist on BundleItem (via a validation-only search)
  raw <nsUid> '<selection>'   run item.<root>(nsUid) {{ <selection> }} (root as for fields), print response
  gql '<selection>' [lang]    run any root-level {{ <selection> }} in the store context, print response: for root
                              fields other than item.<root>(nsUid) and lookups not keyed by nsUid, e.g.
                              gql 'membership {{ membershipItems {{ nsUid imageUrl }} }}'
                              gql 'item {{ ticketItemGroup(ticketItemGroupId: N) {{ id formalName }} }}'
                              (queries needing a signed-in user's idToken are not possible)
  dlc <nsUid> [offset]        DLC of an application (aocs equivalent) as titledb records, one {{nsUid: record}}
                              per line, bundles skipped; RAW=1 = raw GraphQL rows; ALL=1 for every page
  dlc-titles <titleId>...     DLC items by DLC title ID
  search [offset]             newest Switch 1 applications (searchV4); one page of LIMIT
  dlc-search [offset]         all DLC (searchV4); one page of LIMIT
  scan-range <from> <to>      exact nsUid scan (batched aliases), no search depth limit; root by prefix: 7001
                              applicationItem (search-shaped rows), 7003 demoItem, 7005 dlcItem, 7007 bundleItem
                              (full-data rows; pipe into scrape-all for titledb entries); progress/ETA on stderr
                              (a line per batch on a terminal, else every PROGRESS_EVERY=20 batches; QUIET=1 = none)
  search-count                offsetInfo (total) for the current FREEWORD / SORT / SALES, one request
  get-latest                  alias of search: newest page only (offset 0), no options
  search-all                  every item: SALES x FREEWORD-prefix shards (a single search stops at offset 999)
  reorder-titledb [file] [out]  sort a titledb.json by nsUid ascending (default titledb.json, in place; out - = stdout)
  clean-titledb [file] [out]  normalise text of every entry (name, description, intro, publisher, developer):
                              \\uXXXX escapes and HTML entities decoded, NFC, line / paragraph separators (U+2028,
                              U+2029, NEL, CR, VT, FF) -> newline, control / zero-width / BOM characters removed,
                              odd spaces -> space; in place by default, offline. New entries (item, dlc, scrape-*,
                              reprocess, process-titledb, and the entries update-titledb-file adds) are cleaned
                              automatically; CLEAN_TEXT=0 turns that off.
                              TEXT_ASCII (default 2): 0 = off; 1 = typographic quotes / dashes / ellipsis, fullwidth
                              forms, Roman numerals -> ASCII; 2 also drops accents (e-acute -> e);
                              TEXT_REPLACE='src=dst;...'
                              = own substitutions (empty dst deletes), e.g. TEXT_REPLACE='™=;•=-'
  reprocess-titledb <in> [out] [nsUid...]
                              re-fetch entries of a titledb file (or an old scrape-all dump) and rewrite them in
                              the current format; entries looked up by nsUid per type (7001 base, 7003 demo,
                              7005 DLC, 7007 bundle); nsUids = only those (targeted). out defaults to in (in
                              place; a dump needs out). SCOPE=all|base,demo,dlc,bundle  UPDATE=1 = then run
                              update-titledb  SLEEP=1-2 (default)  BATCH=25. Fields the API returns null keep
                              their old value; unreturned entries stay as they were; resumable
  process-titledb [in] [out]  merge {{nsUid: record}} entries (scrape-*, dlc, item output; file or stdin) into one
                              JSON object {{"nsUid": record, ...}}; out = file (may equal in), default stdout;
                              later duplicates win; PRETTY=1 = fully indented (offline, no cert needed)
  update-titledb [titledb.json]
                              scrape-latest, adding only entries not already in the file (never changes existing
                              ones); newest UPDATE_COUNT (150) titles, ALL=1 = the whole search (max 1000); prints how many were added;
                              result sorted by nsUid (TITLEDB_SORT=0 = append instead)
  update-titledb-file <titledb.json> <other>
                              add entries of another titledb file that are not already in the first; result sorted by nsUid, TITLEDB_SORT=0 = append (offline)
  scrape-all [file]           scrape-title for each nsUid of NDJSON search output (file or stdin)
  scrape-latest               get-latest piped into scrape-all (newest page only)
  scrape-all-latest           the newest 1000 titles (one search, every page, no shards) piped into scrape-all
  scrape-title <nsUid>        application, each DLC (dlc -> dlc-titles chain) and each demo as titledb entries,
                              one {{nsUid: record}} per line
  simba <what> [args]         Simba JSON (the legacy shogun format nut's Title.parseSimbaJson reads), built from
                              GraphQL, for store COUNTRY in LANG_CODE: title <nsUid> (any type) | dlc <nsUid> | aocs <baseNsUid> |
                              latest [page] (LIMIT per page) | ids <titleId>... (TYPE=title|aoc) | country [CC]
  (list commands always emit one compact JSON item per line; ALL=1 walks every page)

env: CERT GQL SHOP COUNTRY LANG_CODE REGION TIMEOUT
     DEBUG=1  print the full curl command of every request to stderr (stdout stays clean)
     PRETTY=1  indented multi-line JSON instead of one compact line per item (all commands; scrape-all
               also reads indented input)
     search / dlc-search:
             SORT (RELEASE_DATE_DESC; BOTH = DESC + ASC passes, deduped) PLATFORM (HAC) SALES (ONSALE_OR_PRE_ORDER)
             FREEWORD ("") LIMIT (100, the API maximum) ALL (unset; 1 = fetch every page) MAX_PAGES (1000) SLEEP (0)
             ITEM_TYPES (search only; APPLICATION; space-separated SearchItemType values, e.g. TICKET)
             BUNDLE (default 1 = keep BundleItem rows, as full data rows; BUNDLE=0 filters them out; scrape-all and
             update-titledb turn them into titledb bundle entries; BUNDLE_FIELDS = own selection, skips probing)
     sort values: RELEASE_DATE_DESC RELEASE_DATE_ASC SALES_AMOUNT_DESC DL_COUNT_DESC
                  PRICE_ASC PRICE_DESC PRICE_END_AT_ASC RELEVANCE
     PLATFORM: HAC | BEE   SALES: ONSALE_OR_PRE_ORDER | ONSALE | COMING_SOON | ALL (first + COMING_SOON, deduped;
                                                   default for search-all only)
     dlc: LIMIT (100, the API maximum) PUBLIC_STATUSES (PUBLIC) SALES_STATUSES (ONSALE,PRE_ORDER) INCLUDE_BUNDLES (true)
          SALES_STATUSES also takes SALES_TERMINATION, UNRELEASED""")
    sys.exit(1)


def emit_all(it):
    for x in it:
        out(x)


def write_json_file(path, obj):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(pretty(obj) + "\n")
    err(f"wrote {path}")


def save_languages(path="titledb/languages.json"):
    """{country: [language codes]} for every REGIONS entry -> path."""
    res = {}
    for r in REGIONS:
        res[r] = country_languages(r)
        sleep_if()
    write_json_file(path, res)


def save_regions(path="titledb/cdn.regions.json"):
    """{regionCode: [countries]} for every REGIONS entry -> path (REGION_ORDER sets the key order)."""
    rows = []
    for r in REGIONS:
        c = country_of(r)
        if c and c.get("regionCode"):
            rows.append({"region": c["regionCode"], "country": r})
        else:
            err(f"nintendo region ({r}) error: {compact(c) if c else 'no response'}")
        sleep_if()
    order = env("REGION_ORDER", "USA EUR CHN TWN KOR JPN AUS SEA").split()
    groups = {}
    for row in rows:
        groups.setdefault(row["region"], []).append(row["country"])
    keys = sorted(groups, key=lambda k: (order.index(k) if k in order else 999, k))
    write_json_file(path, {k: groups[k] for k in keys})


def main(argv):
    cmd = argv[0].replace("_", "-") if argv else ""  # process_titledb == process-titledb
    a = argv[1:]

    # Client certificate must exist before any command that talks to the API (CERT overrides the path).
    if cmd not in ("", "regions", "process-titledb", "reorder-titledb", "clean-titledb", "update-titledb-file", "extra-fields") and not os.path.isfile(CERT):
        err(f"error: client certificate '{CERT}' not found (set CERT=/path/to/file.pem)")
        sys.exit(1)

    if cmd == "country":
        req("Country", Q_COUNTRY, {})
    elif cmd == "regions":
        print("\n".join(REGIONS))
    elif cmd == "language":
        print(country_language(a[0] if a else COUNTRY))
    elif cmd == "languages":
        print(compact(country_languages(a[0] if a else COUNTRY)))
    elif cmd == "save-languages":
        save_languages(a[0] if a else "titledb/languages.json")
    elif cmd == "save-regions":
        save_regions(a[0] if a else "titledb/cdn.regions.json")
    elif cmd == "simba":
        simba_cli(a)
    elif cmd == "process-titledb":
        process_titledb(a[0] if a else "-", a[1] if len(a) > 1 else None)
    elif cmd == "reorder-titledb":
        reorder_titledb(a[0] if a else "titledb.json", a[1] if len(a) > 1 else None)
    elif cmd == "clean-titledb":
        clean_titledb(a[0] if a else "titledb.json", a[1] if len(a) > 1 else None)
    elif cmd == "reprocess-titledb":
        if not a:
            usage()
        reprocess_titledb(a[0], a[1] if len(a) > 1 and a[1] != "-" else None, a[2:])
    elif cmd == "update-titledb":
        update_titledb(a[0] if a else "titledb.json")
    elif cmd == "update-titledb-file":
        if len(a) < 2:
            usage()
        update_titledb_file(a[0], a[1])
    elif cmd == "scrape-all":
        scrape_all(list(read_ndjson(a[0])) if a and a[0] != "-" else read_ndjson("-"))
    elif cmd == "scrape-latest":
        scrape_all(list(get_latest()))
    elif cmd == "scrape-all-latest":
        scrape_all(list(search(0, all_pages=True)))
    elif cmd == "scrape-title":
        if not a:
            usage()
        res = scrape_title(a[0])
        if res is None:
            raise ApiError("")
        emit_records(res)
    elif cmd == "item":
        if not a:
            usage()
        item(a[0], a[1] if len(a) > 1 else None)
    elif cmd == "fields":
        if not a:
            usage()
        fields(a[0], a[1:])
    elif cmd == "lookup-probe":
        lookup_probe(a)
    elif cmd == "bundle-fields":
        bundle_fields(a)
    elif cmd == "dlc-fields":
        if not a:
            usage()
        dlc_fields(a[0], a[1:])
    elif cmd == "extra-fields":
        out(extra_fields(a[0] if a else None))
    elif cmd == "extra":
        if not a:
            usage()
        out(country_extra(a[1:] or None) if a[0] == "country" else item_extra(a[0], a[1:] or None))
    elif cmd == "raw":
        if len(a) < 2:
            usage()
        raw(a[0], a[1], a[2] if len(a) > 2 else None)
    elif cmd == "gql":
        if not a:
            usage()
        gql(a[0], a[1] if len(a) > 1 else None)
    elif cmd == "title":
        if not a:
            usage()
        title(a)
    elif cmd == "dlc":
        if not a:
            usage()
        rows = dlc(a[0], int(a[1]) if len(a) > 1 else 0, note=True)
        if env("RAW"):
            emit_all(rows)
        else:  # titledb record per DlcItem, keyed by nsUid like `item`; bundles are skipped
            seen = {}
            for row in rows:
                t = row.get("__typename")
                seen[t] = seen.get(t, 0) + 1
                if t == "DlcItem":
                    rec = titledb_record(row)
                    out({str(rec["nsuId"]): rec})
            if seen and "DlcItem" not in seen:
                err(f"dlc: {sum(seen.values())} item(s) returned but none is a DlcItem {seen} (RAW=1 shows them)")
    elif cmd == "dlc-titles":
        if not a:
            usage()
        emit_all(dlc_titles(a))
    elif cmd == "search-all":
        emit_all(search_all())
    elif cmd == "get-latest":
        emit_all(get_latest())
    elif cmd == "search":
        emit_all(search(int(a[0]) if a else 0))
    elif cmd == "search-count":
        out(search_count())
    elif cmd == "dlc-search":
        emit_all(dlc_search(int(a[0]) if a else 0))
    elif cmd == "scan-range":
        if len(a) < 2:
            usage()
        if not (a[0].isdigit() and a[1].isdigit()):
            raise ApiError("FROM and TO must be numbers")
        emit_all(scan_range(int(a[0]), int(a[1])))
    else:
        usage()


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):  # CLI only: `simba.py ... | head` exits quietly; an importer (nut) keeps its own
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    try:
        main(sys.argv[1:])
    except ApiError as e:
        if str(e):
            err(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)