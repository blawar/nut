#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import traceback

import nut_impl
import server

from bs4 import BeautifulSoup
from nut_impl import config, nsps, printer, status
from server import gdrive, network


def _success(request, response, s):
    response.write(json.dumps({'success': True, 'result': s}))

# TODO: remove unused method
def _error(request, response, s):
    response.write(json.dumps({'success': False, 'result': s}))


def getScan(request, response):
    _success(request, response, nut_impl.scan())


def getSearch(request, response):
    nsp = []
    nsx = []
    nsz = []
    xci = []
    xcz = []

    nut_impl.scan()

    for _, f in nsps.files.items():
        name = f.fileName()
        if name.endswith('.nsp'):
            nsp.append({
                'id': f.titleId,
                'name': f.fileName(),
                'version': int(f.version) if f.version else None
            })
        elif name.endswith('.nsz'):
            nsz.append({
                'id': f.titleId,
                'name': f.fileName(),
                'version': int(f.version) if f.version else None
            })
        elif name.endswith('.nsx'):
            nsx.append({
                'id': f.titleId,
                'name': f.fileName(),
                'version': int(f.version) if f.version else None
            })
        elif name.endswith('.xci'):
            xci.append({
                'id': f.titleId,
                'name': f.fileName(),
                'version': int(f.version) if f.version else None
            })
        elif name.endswith('.xcz'):
            xcz.append({
                'id': f.titleId,
                'name': f.fileName(),
                'version': int(f.version) if f.version else None
            })

    o = nsz + nsp + xcz + xci + nsx
    response.write(json.dumps(o))


def getInfo(request, response):
    try:
        nsp = nsps.getByTitleId(request.bits[2])
        t = {'id': request.bits[2]}
        t['size'] = nsp.getFileSize()
        t['mtime'] = nsp.getFileModified()
        response.write(json.dumps(t))
    except BaseException as e:
        response.write(json.dumps({'success': False, 'message': str(e)}))


def _serveFile(response, path, filename=None, start=None, end=None):
    try:
        if start is not None:
            start = int(start)

        if end is not None:
            end = int(end)

        if not filename:
            filename = os.path.basename(path)

        response.attachFile(filename)

        chunkSize = 0x400000

        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if start and end:
                if end is None:
                    end = size - 1
                else:
                    end = int(end)

                if start is None:
                    start = size - end
                else:
                    start = int(start)

                if start >= size or start < 0 or end <= 0:
                    return server.Response400(
                        None,
                        response,
                        'Invalid range request %d - %d' % (start, end)
                    )

                response.setStatus(206)

            else:
                if start is None:
                    start = 0
                if end is None:
                    end = size

            if end >= size:
                end = size

                if end <= start:
                    response.write(b'')
                    return

            printer.info('ranged request for %d - %d' % (start, end))
            f.seek(start, 0)

            response.setMime(path)
            response.setHeader('Accept-Ranges', 'bytes')
            response.setHeader(
                'Content-Range',
                f'bytes {start}-{end-1}/{size}'
            )
            response.setHeader('Content-Length', str(end - start))
            response.sendHeader()

            if not response.head:
                size = end - start

                i = 0
                progress = status.create(
                    size,
                    'Downloading ' + os.path.basename(path)
                )

                while i < size:
                    chunk = f.read(min(size-i, chunkSize))
                    i += len(chunk)

                    progress.add(len(chunk))

                    if chunk:
                        pass
                        response.write(chunk)
                    else:
                        break
                progress.close()
    except BaseException as e:
        printer.error('File download exception: ' + str(e))
        traceback.print_exc(file=sys.stdout)

    if response.bytesSent == 0:
        response.write(b'')


# TODO: very similar to _serveFile, can be refactored
def getDownload(request, response, start=None, end=None):
    try:
        nsp = nsps.getByTitleId(request.bits[2])
        response.attachFile(nsp.titleId + '.nsp')

        if len(request.bits) >= 5:
            start = int(request.bits[-2])
            end = int(request.bits[-1])

        chunkSize = 0x400000

        with open(nsp.path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if 'Range' in request.headers:
                _range = request.headers.get('Range').strip()
                start, end = _range.strip('bytes=').split('-')

                if end == '':
                    end = size - 1
                else:
                    end = int(end) + 1

                if start == '':
                    start = size - end
                else:
                    start = int(start)

                if start >= size or start < 0 or end <= 0:
                    return server.Response400(
                        request,
                        response,
                        f'Invalid range request {start} - {end}'
                    )

                response.setStatus(206)

            else:
                if start is None:
                    start = 0
                if end is None:
                    end = size

            if end >= size:
                end = size

                if end <= start:
                    response.write(b'')
                    return

            printer.info('ranged request for %d - %d' % (start, end))
            f.seek(start, 0)

            response.setMime(nsp.path)
            response.setHeader('Accept-Ranges', 'bytes')
            response.setHeader(
                'Content-Range',
                f'bytes {start}-{end-1}/{size}'
            )
            response.setHeader('Content-Length', str(end - start))
            response.sendHeader()

            if not response.head:
                size = end - start

                i = 0
                progress = status.create(
                    size,
                    'Downloading ' + os.path.basename(nsp.path)
                )

                while i < size:
                    chunk = f.read(min(size-i, chunkSize))
                    i += len(chunk)

                    progress.add(len(chunk))

                    if chunk:
                        pass
                        response.write(chunk)
                    else:
                        break
                progress.close()
    except BaseException as e:
        printer.error('NSP download exception: ' + str(e))
        traceback.print_exc(file=sys.stdout)
    if response.bytesSent == 0:
        response.write(b'')


def _isWindows():
    if "win" in sys.platform[:3].lower():
        return True
    else:
        return False


def _listDrives():
    drives = []
    for label, _ in config.paths.mapping().items():
        drives.append(label)
    if _isWindows():
        import ctypes
        import string
        kernel32 = ctypes.windll.kernel32
        bitmask = kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(letter)
            bitmask >>= 1
        return drives

    drives.append('root')

    return drives


def _isBlocked(path):
    path = path.lower()

    whitelist = [
        '.nro',
        '.xci',
        '.nsp',
        '.nsx',
        '.nsz',
        '.xcz',
        '.conf',
        '.json',
        '.db',
        '.tfl',
        '.jpg',
        '.gif',
        '.png',
        '.bin',
        '.enc',
        '.ini',
        '.ips',
        '.txt',
        '.pdf',
    ]

    for ext in whitelist:
        if path.endswith(ext):
            return False

    return True


def _isNetworkPath(url):
    return url.startswith('http://') or url.startswith('https://')


def _cleanPath(path=None):
    if not path:
        return None

    bits = path.replace('\\', '/').split('/')
    drive = bits[0]
    bits = bits[1:]

    if drive in config.paths.mapping():
        url = config.paths.mapping()[drive]
        if _isNetworkPath(url):
            path = os.path.join(url, '/'.join(bits))
        else:
            path = os.path.abspath(
                os.path.join(
                    os.path.abspath(url),
                    '/'.join(bits)
                )
            )
    elif _isWindows():
        path = os.path.abspath(os.path.join(drive+':/', '/'.join(bits)))
    else:
        path = os.path.abspath('/'.join(bits))

    return path


def _resolveRelativeUrl(path, parent):
    if path[0] == '/':
        if len(path) > 1:
            return path[1:]
    return path


def getTeamDriveId(service, path):
    return gdrive.get_team_gdrive_id(service, path)


def getGdriveToken(request, response):
    creds = gdrive.get_token()

    r = {}
    r['access_token'] = creds.token
    r['refresh_token'] = creds.refresh_token

    with open(config.getGdriveCredentialsFile(), 'r') as f:
        r['credentials'] = json.loads(f.read())

    if response is not None:
        response.write(json.dumps(r))


def getDirectoryList(request, response):
    try:
        path = ''

        if len(request.bits) > 2:
            virtualDir = request.bits[2]
        else:
            virtualDir = ''

        if virtualDir == 'gdrive':
            for i in request.bits[3:]:
                path = os.path.join(path, i)
            r = gdrive.listGdriveDir(path)
            response.write(json.dumps(r))
            return

        for i in request.bits[2:]:
            path = os.path.join(path, i)

        path = _cleanPath(path)

        r = {'dirs': [], 'files': []}

        if not path:
            for d in _listDrives():
                r['dirs'].append({'name': d})
            response.write(json.dumps(r))
            return

        if _isNetworkPath(path):
            x = network.makeRequest('GET', path)
            soup = BeautifulSoup(x.text, 'html.parser')
            items = soup.select('a')

            for a in items:
                href = a['href']

                if href.endswith('/'):
                    r['dirs'].append({
                        'name': _resolveRelativeUrl(href, virtualDir)
                    })
                    continue

                r['files'].append({
                    'name': _resolveRelativeUrl(href, virtualDir)
                })

        else:
            for name in os.listdir(path):
                abspath = os.path.join(path, name)

                if os.path.isdir(abspath):
                    r['dirs'].append({'name': name})
                elif os.path.isfile(abspath):
                    if not _isBlocked(abspath) and not nsps.is_file_hidden(abspath):
                        r['files'].append({
                            'name': name,
                            'size': os.path.getsize(abspath),
                            'mtime': os.path.getmtime(abspath)
                        })

        response.write(json.dumps(r))
    except:
        raise IOError('dir list access denied')


def getFile(request, response, start=None, end=None):
    try:
        path = ''

        if len(request.bits) > 2:
            virtualDir = request.bits[2]
        else:
            virtualDir = ''

        for i in request.bits[2:]:
            path = os.path.join(path, i)
        path = _cleanPath(path)

        if _isBlocked(path):
            raise IOError('access denied')

        if 'Range' in request.headers:
            _range = request.headers.get('Range').strip()
            start, end = _range.strip('bytes=').split('-')

            if end != '':
                end = int(end) + 1

            if start != '':
                start = int(start)

        if virtualDir == 'gdrive':
            path = ''
            for i in request.bits[3:]:
                path = os.path.join(path, i)
            return gdrive.downloadGdriveFile(response, path, start=start, end=end)

        elif _isNetworkPath(path):
            network.downloadProxyFile(path, response, start=start, end=end)
        else:
            return _serveFile(response, path, start=start, end=end)
    except:
        raise IOError('file read access denied')


def getFileSize(request, response):
    t = {}
    path = ''
    for i in request.bits[2:]:
        path = os.path.join(path, i)
    path = _cleanPath(path)
    try:
        t['size'] = os.path.getsize(path)
        t['mtime'] = os.path.getmtime(path)
        response.write(json.dumps(t))
    except BaseException as e:
        response.write(json.dumps({'success': False, 'message': str(e)}))
