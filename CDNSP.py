#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import base64
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from binascii import hexlify as hx, unhexlify as uhx
from hashlib import sha256
from struct import pack as pk, unpack as upk
from io import TextIOWrapper
from tqdm import tqdm

import requests
import unidecode
import urllib3

#Global Vars
noaria = False
titlekey_list = []
quiet = False
truncateName = False
tinfoil = False
enxhop = False

def print_(*info):
    if not quiet:
        print(' '.join(map(str,info)))

def read_at(f, off, len):
    f.seek(off)
    return f.read(len)

def read_u8(f, off):
    return upk('<B', read_at(f, off, 1))[0]


def read_u16(f, off):
    return upk('<H', read_at(f, off, 2))[0]


def read_u32(f, off):
    return upk('<I', read_at(f, off, 4))[0]


def read_u48(f, off):
    s = upk('<HI', read_at(f, off, 6))
    return 0x10000 * s[1] + s[0]


def read_u64(f, off):
    return upk('<Q', read_at(f, off, 8))[0]

def calc_sha256(fPath):
    f = open(fPath, 'rb')
    fSize = os.path.getsize(fPath)
    hash = sha256()
    
    if fSize >= 10000:
        t = tqdm(total=fSize, unit='B', unit_scale=True, desc=os.path.basename(fPath), leave=False)
        while True:
            buf = f.read(4096)
            if not buf:
                break
            hash.update(buf)
            t.update(len(buf))
        t.close()
    else:
        hash.update(f.read())
    f.close()
    return hash.hexdigest()


def bytes2human(n, f='%(value).3f %(symbol)s'):
    n = int(n)
    if n < 0:
        raise ValueError("n < 0")
    symbols = ('B', 'KB', 'MB', 'GB', 'TB')
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i + 1) * 10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return f % locals()
    return f % dict(symbol=symbols[0], value=n)


def load_config(fPath):
    dir = os.path.dirname(__file__)

    config = {'Paths': {
        'hactoolPath': 'hactool',
        'keysPath': 'keys.txt',
        'NXclientPath': 'nx_tls_client_cert.pem',
        'ShopNPath': 'ShopN.pem'},
        'Values': {
            'Region': 'US',
            'Firmware': '5.1.0-0',
            'DeviceID': '0000000000000000',
            'Environment': 'lp1',
            'TitleKeysURL': '',
            'NspOut': '_NSPOUT',
            'AutoUpdatedb': 'False'}}
    try:
        f = open(fPath, 'r')
    except FileNotFoundError:
        f = open(fPath, 'w')
        json.dump(config, f)
        f.close()
        f = open(fPath, 'r')

    j = json.load(f)

    hactoolPath = j['Paths']['hactoolPath']
    keysPath = j['Paths']['keysPath']
    NXclientPath = j['Paths']['NXclientPath']
    ShopNPath = j['Paths']['ShopNPath']

    reg = j['Values']['Region']
    fw = j['Values']['Firmware']
    did = j['Values']['DeviceID']
    env = j['Values']['Environment']
    dbURL = j['Values']['TitleKeysURL']
    nspout = j['Values']['NspOut']
    autoUpdatedb = j['Values']['AutoUpdatedb']

    if platform.system() == 'Linux':
        hactoolPath = './' + hactoolPath + '_linux'

    if platform.system() == 'Darwin':
        hactoolPath = './' + hactoolPath + '_mac'

    return hactoolPath, keysPath, NXclientPath, ShopNPath, reg, fw, did, env, dbURL, nspout, autoUpdatedb


def make_request(method, url, certificate='', hdArgs={}):
    if certificate == '':  # Workaround for defining errors
        certificate = NXclientPath

    reqHd = {'User-Agent': 'NintendoSDK Firmware/%s (platform:NX; eid:%s)' % (fw, env),
             'Accept-Encoding': 'gzip, deflate',
             'Accept': '*/*',
             'Connection': 'keep-alive'}
    reqHd.update(hdArgs)

    r = requests.request(method, url, cert=certificate, headers=reqHd, verify=False, stream=True)

    if r.status_code == 403:
        print_('Request rejected by server! Check your cert.')
        return r

    return r


def get_info(tid, silent=False):
    info = ''
    name = get_name(tid)
    if tid.endswith('000'):
        baseTid = tid
        updateTid = '%s800' % tid[:-3]
    elif tid.endswith('800'):
        baseTid = '%s000' % tid[:-3]
        updateTid = tid
    elif not tid.endswith('00'):
        baseTid = '%016x' % (int(tid, 16) - 0x1000 & 0xFFFFFFFFFFFFF000)
        updateTid = '%s800' % baseTid[:-3]
    else:
        info = 'Not a valid title'
        return info

    rid = get_rid(tid)

    info = '\nName: ' + name + '\n' + 'Titleid: ' + tid + '\n'  + 'Rightsid: ' + rid + '\n' + 'Versions: ' + ' '.join(
        get_versions(tid)) + '\n' + 'Update Titleid: ' + updateTid + '\n' + 'Versions: ' + ' '.join(
        get_versions(updateTid)) + '\n'

    if not silent:
        print_(info)
    return info


def get_versions(tid):
    # url = 'https://tagaya.hac.%s.eshop.nintendo.net/tagaya/hac_versionlist' % env
    url = 'https://superfly.hac.%s.d4c.nintendo.net/v1/t/%s/dv' % (env, tid)
    r = make_request('GET', url)
    j = r.json()

    try:
        if j['error']:
            return ['none']
    except Exception as e:
        pass
    try:
        lastestVer = j['version']
        if lastestVer < 65536:
            return ['%s' % lastestVer]
        else:
            versionList = ('%s' % "-".join(str(i) for i in range(0x10000, lastestVer + 1, 0x10000))).split('-')
            if tid.endswith("00"):
                return versionList
            return [versionList[0]]
    except Exception as e:
        return ['none']

def get_name_old(tid):
    tid = tid.lower()
    lines = titlekey_list
    for line in lines:
        if line == None:
            return
        temp = line.split("|")
        if tid.endswith('800'):
            tid = '%s000' % tid[:-3]
        if tid.strip() == temp[0].strip():
            return re.sub(r'[/\\:*?!"|™©®]+', "", unidecode.unidecode(temp[2].strip()))
    return 'Unknown Title'

def get_name(tid):
    tid = tid.lower()
    name = get_name_control(tid)
    if name == "":
        name = get_name_old(tid)

    return re.sub(r'[/\\:*?!"|™©®]+', "", unidecode.unidecode(name)) 



def download_file_aria(url, fPath):
    # Adds a new sub function to do the actual downloading with aria2c
    # Certain config values are hardcoded
    def _dl(cmd):
        popen = subprocess.Popen(shlex.split(cmd), universal_newlines=True,
                                 cwd=os.path.dirname(os.path.realpath(__file__)))
        return_code = popen.wait()


    dlheaders = {
        'User-Agent': 'NintendoSDK Firmware/%s (platform:NX; eid:%s)' % (fw,env),
        'Accept-Encoding': 'gzip, deflate',
        'Accept': '*/*',
        'Connection': 'keep-alive'}
    dlheaders_list = list(map(lambda a: "--header=\"%s: %s\"" % (a, dlheaders[a]), dlheaders))
    dlheaders_args = " ".join(dlheaders_list)

    #quiet aria output if needed
    q = ''
    if quiet:
        q = '-q'

    ariaBin = 'aria2c'
  
    dlcommand = '%s --file-allocation=none --auto-file-renaming=false --check-certificate=false ' \
                '--certificate=nx_tls_client_cert.pem %s --private-key=nx_tls_client_cert.pem -x16 -s16 -k5M %s "%s" ' \
                '--dir="%s" -o "%s"' % (ariaBin,q,
                    dlheaders_args, url, os.path.dirname(fPath), os.path.basename(fPath))

    if platform.system() == 'Windows' and platform.architecture() == '32bit':
        pass #ariaBin = 'aria2c_win32'

    if platform.system() != 'Windows':
        dlcommand = "./" + dlcommand

    _dl(dlcommand)
    return fPath


def download_file(url, fPath):
    fName = os.path.basename(fPath).split()[0]

    if os.path.exists(fPath):
        dlded = os.path.getsize(fPath)
        r = make_request('GET', url, hdArgs={'Range': 'bytes=%s-' % dlded})

        if r.headers.get('Server') != 'openresty/1.9.7.4':
            print_('\nDownload is already complete, skipping!')
            return fPath
        elif r.headers.get('Content-Range') == None:  # CDN doesn't return a range if request >= filesize
            fSize = int(r.headers.get('Content-Length'))
        else:
            fSize = dlded + int(r.headers.get('Content-Length'))

        if dlded == fSize:
            print_('\nDownload is already complete, skipping!')
            return fPath
        elif dlded < fSize:
            print_('\nResuming download...')
            f = open(fPath, 'ab')
        else:
            print_('\nExisting file is bigger than expected (%s/%s), restarting download...' % (dlded, fSize))
            dlded = 0
            f = open(fPath, "wb")
    else:
        dlded = 0
        r = make_request('GET', url)
        fSize = int(r.headers.get('Content-Length'))
        f = open(fPath, 'wb')

    chunkSize = 1000
    if tqdmProgBar == True and fSize >= 10000:
        for chunk in tqdm(r.iter_content(chunk_size=chunkSize), initial=dlded // chunkSize, total=fSize // chunkSize,
                          desc=fName, unit='kb', smoothing=1, leave=False):
            f.write(chunk)
            dlded += len(chunk)
    elif fSize >= 10000:
        for chunk in r.iter_content(
                chunkSize):  # https://stackoverflow.com/questions/15644964/python-progress-bar-and-downloads
            f.write(chunk)
            dlded += len(chunk)
            done = int(50 * dlded / fSize)
            sys.stdout.write('\r%s:  [%s%s] %d/%d b' % (fName, '=' * done, ' ' * (50 - done), dlded, fSize))
            sys.stdout.flush()
        sys.stdout.write('\033[F')
    else:
        f.write(r.content)
        dlded += len(r.content)

    if fSize != 0 and dlded != fSize:
        raise ValueError('Downloaded data is not as big as expected (%s/%s)!' % (dlded, fSize))

    f.close()
    print_('\r\nSaved to %s!' % f.name)
    return fPath


def decrypt_NCA(fPath, outDir=''):
    fName = os.path.basename(fPath).split()[0]

    if outDir == '':
        outDir = os.path.splitext(fPath)[0]
    os.makedirs(outDir, exist_ok=True)

    commandLine = hactoolPath + ' "' + fPath + '"' + keysArg \
                  + ' --exefsdir="' + outDir + os.sep + 'exefs"' \
                  + ' --romfsdir="' + outDir + os.sep + 'romfs"' \
                  + ' --section0dir="' + outDir + os.sep + 'section0"' \
                  + ' --section1dir="' + outDir + os.sep + 'section1"' \
                  + ' --section2dir="' + outDir + os.sep + 'section2"' \
                  + ' --section3dir="' + outDir + os.sep + 'section3"' \
                  + ' --header="' + outDir + os.sep + 'Header.bin"'

    try:
        subprocess.check_output(commandLine, shell=True)
        if os.listdir(outDir) == []:
            raise subprocess.CalledProcessError('\nDecryption failed, output folder %s is empty!' % outDir)
    except subprocess.CalledProcessError:
        print_('\nDecryption failed!')
        raise

    return outDir


def verify_NCA(ncaFile, titleKey):
    commandLine = hactoolPath + ' "' + ncaFile + '"' + keysArg + ' --titlekey="' + titleKey + '"'

    try:
        output = str(subprocess.check_output(commandLine, stderr=subprocess.STDOUT, shell=True))
    except subprocess.CalledProcessError as exc:
        print_("Status : FAIL", exc.returncode, exc.output)
        return False
    else:
        if "Error: section 0 is corrupted!" in output or "Error: section 1 is corrupted!" in output:
            print_("\nNCA Verification failed. Probably a bad titlekey.")
            return False
    print_("\nTitlekey verification successful.")
    return True


def get_biggest_file(path):
    try:
        objects = os.listdir(path)
        sofar = 0
        name = ""
        for item in objects:
            size = os.path.getsize(os.path.join(path, item))
            if size > sofar:
                sofar = size
                name = item
        return os.path.join(path, name)
    except Exception as e:
        print_(e)


def download_cetk(rightsID, fPath):
    url = 'https://atum.hac.%s.d4c.nintendo.net/r/t/%s?device_id=%s' % (env, rightsID, did)
    r = make_request('HEAD', url)
    id = r.headers.get('X-Nintendo-Content-ID')

    url = 'https://atum.hac.%s.d4c.nintendo.net/c/t/%s?device_id=%s' % (env, id, did)
    cetk = download_file(url, fPath)

    return cetk


def download_title(gameDir, tid, ver, tkey='', nspRepack=False, n='', verify=False):
    print_('\n%s v%s:' % (tid, ver))
    tid = tid.lower();
    tkey = tkey.lower();
    if len(tid) != 16:
        tid = (16 - len(tid)) * '0' + tid

    url = 'https://atum%s.hac.%s.d4c.nintendo.net/t/a/%s/%s?device_id=%s' % (n, env, tid, ver, did)
    print_(url)
    try:
        r = make_request('HEAD', url)
    except Exception as e:
        print_("Error downloading title. Check for incorrect titleid or version.")
        return
    CNMTid = r.headers.get('X-Nintendo-Content-ID')

    if CNMTid == None:
        print_('title not available on CDN')
        return

    print_('\nDownloading CNMT (%s.cnmt.nca)...' % CNMTid)
    url = 'https://atum%s.hac.%s.d4c.nintendo.net/c/a/%s?device_id=%s' % (n, env, CNMTid, did)
    fPath = os.path.join(gameDir, CNMTid + '.cnmt.nca')
    cnmtNCA = download_file(url, fPath)
    cnmtDir = decrypt_NCA(cnmtNCA)
    CNMT = cnmt(os.path.join(cnmtDir, 'section0', os.listdir(os.path.join(cnmtDir, 'section0'))[0]),
                os.path.join(cnmtDir, 'Header.bin'))

    if nspRepack == True:
        outf = os.path.join(gameDir, '%s.xml' % os.path.basename(cnmtNCA.strip('.nca')))
        cnmtXML = CNMT.gen_xml(cnmtNCA, outf)

        rightsID = '%s%s%s' % (tid, (16 - len(CNMT.mkeyrev)) * '0', CNMT.mkeyrev)

        tikPath = os.path.join(gameDir, '%s.tik' % rightsID)
        certPath = os.path.join(gameDir, '%s.cert' % rightsID)
        if CNMT.type == 'Application' or CNMT.type == 'AddOnContent':
            shutil.copy(os.path.join(os.path.dirname(__file__), 'Certificate.cert'), certPath)

            if tkey != '':
                with open(os.path.join(os.path.dirname(__file__), 'Ticket.tik'), 'rb') as intik:
                    data = bytearray(intik.read())
                    data[0x180:0x190] = uhx(tkey)
                    data[0x286] = int(CNMT.mkeyrev)
                    data[0x2A0:0x2B0] = uhx(rightsID)

                    with open(tikPath, 'wb') as outtik:
                        outtik.write(data)
                print_('\nGenerated %s and %s!' % (os.path.basename(certPath), os.path.basename(tikPath)))
            else:
                print_('\nGenerated %s!' % os.path.basename(certPath))
        elif CNMT.type == 'Patch':
            print_('\nDownloading cetk...')

            with open(download_cetk(rightsID, os.path.join(gameDir, '%s.cetk' % rightsID)), 'rb') as cetk:
                cetk.seek(0x180)
                tkey = hx(cetk.read(0x10)).decode()
                print_('\nTitlekey: %s' % tkey)

                with open(tikPath, 'wb') as tik:
                    cetk.seek(0x0)
                    tik.write(cetk.read(0x2C0))

                with open(certPath, 'wb') as cert:
                    cetk.seek(0x2C0)
                    cert.write(cetk.read(0x700))

            print_('\nExtracted %s and %s from cetk!' % (os.path.basename(certPath), os.path.basename(tikPath)))

    NCAs = {}
    for type in [0, 3, 4, 5, 1, 2, 6]:  # Download smaller files first
        for ncaID in CNMT.parse(CNMT.ncaTypes[type]):
            print_('\nDownloading %s entry (%s.nca)...' % (CNMT.ncaTypes[type], ncaID))
            url = 'https://atum%s.hac.%s.d4c.nintendo.net/c/c/%s?device_id=%s' % (n, env, ncaID, did)
            fPath = os.path.join(gameDir, ncaID + '.nca')
            NCAs.update({type: download_file(url, fPath)})
            if verify:
                if calc_sha256(fPath) != CNMT.parse(CNMT.ncaTypes[type])[ncaID][2]:
                    print_('\n\n%s is corrupted, hashes don\'t match!' % os.path.basename(fPath))
                else:
                    print_('\nVerified %s...' % os.path.basename(fPath))

    if nspRepack == True:
        files = []
        files.append(certPath)
        if tkey != '':
            files.append(tikPath)
        for key in [1, 5, 2, 4, 6]:
            try:
                files.append(NCAs[key])
            except KeyError:
                pass
        files.append(cnmtNCA)
        files.append(cnmtXML)
        try:
            files.append(NCAs[3])
        except KeyError:
            pass

        return files

def download_title_tinfoil(gameDir, tid, ver, tkey='', nspRepack=False, n='', verify=False):
    print_('\n%s v%s:' % (tid, ver))
    tid = tid.lower();
    tkey = tkey.lower();
    if len(tid) != 16:
        tid = (16 - len(tid)) * '0' + tid

    url = 'https://atum%s.hac.%s.d4c.nintendo.net/t/a/%s/%s?device_id=%s' % (n, env, tid, ver, did)
    print_(url)
    try:
        r = make_request('HEAD', url)
    except Exception as e:
        print_("Error downloading title. Check for incorrect titleid or version.")
        return
    CNMTid = r.headers.get('X-Nintendo-Content-ID')

    if CNMTid == None:
        print_('title not available on CDN')
        return

    print_('\nDownloading CNMT (%s.cnmt.nca)...' % CNMTid)
    url = 'https://atum%s.hac.%s.d4c.nintendo.net/c/a/%s?device_id=%s' % (n, env, CNMTid, did)
    fPath = os.path.join(gameDir, CNMTid + '.cnmt.nca')
    cnmtNCA = download_file(url, fPath)
    cnmtDir = decrypt_NCA(cnmtNCA)
    CNMT = cnmt(os.path.join(cnmtDir, 'section0', os.listdir(os.path.join(cnmtDir, 'section0'))[0]),
                os.path.join(cnmtDir, 'Header.bin'))

    if nspRepack == True:
        outf = os.path.join(gameDir, '%s.xml' % os.path.basename(cnmtNCA.strip('.nca')))
        cnmtXML = CNMT.gen_xml_tinfoil(cnmtNCA, outf)

        rightsID = '%s%s%s' % (tid, (16 - len(CNMT.mkeyrev)) * '0', CNMT.mkeyrev)

        tikPath = os.path.join(gameDir, '%s.tik' % rightsID)
        certPath = os.path.join(gameDir, '%s.cert' % rightsID)
        if CNMT.type == 'Application' or CNMT.type == 'AddOnContent':
            shutil.copy(os.path.join(os.path.dirname(__file__), 'Certificate.cert'), certPath)

            if tkey != '':
                with open(os.path.join(os.path.dirname(__file__), 'Ticket.tik'), 'rb') as intik:
                    data = bytearray(intik.read())
                    data[0x180:0x190] = uhx(tkey)
                    data[0x286] = int(CNMT.mkeyrev)
                    data[0x2A0:0x2B0] = uhx(rightsID)

                    with open(tikPath, 'wb') as outtik:
                        outtik.write(data)
                print_('\nGenerated %s and %s!' % (os.path.basename(certPath), os.path.basename(tikPath)))
            else:
                print_('\nGenerated %s!' % os.path.basename(certPath))
        elif CNMT.type == 'Patch':
            print_('\nDownloading cetk...')

            with open(download_cetk(rightsID, os.path.join(gameDir, '%s.cetk' % rightsID)), 'rb') as cetk:
                cetk.seek(0x180)
                tkey = hx(cetk.read(0x10)).decode()
                print_('\nTitlekey: %s' % tkey)

                with open(tikPath, 'wb') as tik:
                    cetk.seek(0x0)
                    tik.write(cetk.read(0x2C0))

                with open(certPath, 'wb') as cert:
                    cetk.seek(0x2C0)
                    cert.write(cetk.read(0x700))

            print_('\nExtracted %s and %s from cetk!' % (os.path.basename(certPath), os.path.basename(tikPath)))

    NCAs = {}
    for type in [3]:  # Download smaller files first
        for ncaID in CNMT.parse(CNMT.ncaTypes[type]):
            print_('\nDownloading %s entry (%s.nca)...' % (CNMT.ncaTypes[type], ncaID))
            url = 'https://atum%s.hac.%s.d4c.nintendo.net/c/c/%s?device_id=%s' % (n, env, ncaID, did)
            fPath = os.path.join(gameDir, ncaID + '.nca')
            NCAs.update({type: download_file(url, fPath)})
            if verify:
                if calc_sha256(fPath) != CNMT.parse(CNMT.ncaTypes[type])[ncaID][2]:
                    print_('\n\n%s is corrupted, hashes don\'t match!' % os.path.basename(fPath))
                else:
                    print_('\nVerified %s...' % os.path.basename(fPath))

    if nspRepack == True:
        files = []
        files.append(certPath)
        if tkey != '':
            files.append(tikPath)
        files.append(cnmtXML)
        try:
            files.append(NCAs[3])
        except KeyError:
            pass

        return files


def get_tik(tid, ver, tkey='', nspRepack=True, n='n'):
    print_('\n%s v%s:' % (tid, ver))
    gameDir = os.path.join(os.path.dirname(__file__), tid)
    tikDir = os.path.join(os.path.dirname(__file__), '_TIKOUT')
    os.makedirs(gameDir, exist_ok=True)
    os.makedirs(tikDir, exist_ok=True)
    tid = tid.lower()
    tkey = tkey.lower()
    if len(tid) != 16:
        tid = (16 - len(tid)) * '0' + tid

    url = 'https://atum%s.hac.%s.d4c.nintendo.net/t/a/%s/%s?device_id=%s' % (n, env, tid, ver, did)
    print_(url)
    try:
        r = make_request('HEAD', url)
    except Exception as e:
        print_("Error downloading title. Check for incorrect titleid or version.")
        return
    CNMTid = r.headers.get('X-Nintendo-Content-ID')

    print_('\nDownloading CNMT (%s.cnmt.nca)...' % CNMTid)
    url = 'https://atum%s.hac.%s.d4c.nintendo.net/c/a/%s?device_id=%s' % (n, env, CNMTid, did)
    fPath = os.path.join(gameDir, CNMTid + '.cnmt.nca')
    cnmtNCA = download_file(url, fPath)
    cnmtDir = decrypt_NCA(cnmtNCA)
    CNMT = cnmt(os.path.join(cnmtDir, 'section0', os.listdir(os.path.join(cnmtDir, 'section0'))[0]),
                os.path.join(cnmtDir, 'Header.bin'))

    rightsID = '%s%s%s' % (tid, (16 - len(CNMT.mkeyrev)) * '0', CNMT.mkeyrev)
    name = get_name(tid)
    if name != 'Unknown Title':
        tikPath = os.path.join(gameDir, '%s [%s][v%s].tik' % (name, tid, ver))
    else:
        tikPath = os.path.join(gameDir, '%s[v%s].tik' % (tid, ver))

    if CNMT.type == 'Application' or CNMT.type == 'AddOnContent':
        if tkey != '':
            with open(os.path.join(os.path.dirname(__file__), 'Ticket.tik'), 'rb') as intik:
                data = bytearray(intik.read())
                data[0x180:0x190] = uhx(tkey)
                data[0x286] = int(CNMT.mkeyrev)
                data[0x2A0:0x2B0] = uhx(rightsID)

                with open(tikPath, 'wb') as outtik:
                    outtik.write(data)
            print_('\nGenerated %s!' % (os.path.basename(tikPath)))
            shutil.copy(tikPath, tikDir)
            shutil.rmtree(gameDir)
            print_('cleaned up downloaded content')
        else:
            print_("Can't get tik without titlekey")

def get_rid(tid, ver=0, tkey='',n='n'):
    global quiet
    quiet = True
    print_('\n%s v%s:' % (tid, ver))
    gameDir = os.path.join(os.path.dirname(__file__), tid)
    os.makedirs(gameDir, exist_ok=True)
    tid = tid.lower()
    tkey = tkey.lower()
    if len(tid) != 16:
        tid = (16 - len(tid)) * '0' + tid

    url = 'https://atum%s.hac.%s.d4c.nintendo.net/t/a/%s/%s?device_id=%s' % (n, env, tid, ver, did)
    print_(url)
    try:
        r = make_request('HEAD', url)
    except Exception as e:
        print_("Error downloading title. Check for incorrect titleid or version.")
        return ''
    CNMTid = r.headers.get('X-Nintendo-Content-ID')

    print_('\nDownloading CNMT (%s.cnmt.nca)...' % CNMTid)
    url = 'https://atum%s.hac.%s.d4c.nintendo.net/c/a/%s?device_id=%s' % (n, env, CNMTid, did)
    fPath = os.path.join(gameDir, CNMTid + '.cnmt.nca')
    cnmtNCA = download_file(url, fPath)
    cnmtDir = decrypt_NCA(cnmtNCA)
    CNMT = cnmt(os.path.join(cnmtDir, 'section0', os.listdir(os.path.join(cnmtDir, 'section0'))[0]),
                os.path.join(cnmtDir, 'Header.bin'))

    rightsID = '%s%s%s' % (tid, (16 - len(CNMT.mkeyrev)) * '0', CNMT.mkeyrev)
    shutil.rmtree(gameDir)
    quiet = False
    return rightsID

def get_control_nca(tid, ver, tkey='', n='n'):
    tempDir = '_TEMP'
    os.makedirs(tempDir, exist_ok=True)
    controlDir = '_CONTROLOUT'
    os.makedirs(controlDir, exist_ok=True)
    tid = tid.lower();
    if tkey != '' and tkey != None:
        tkey = tkey.lower();
    if len(tid) != 16:
        tid = (16 - len(tid)) * '0' + tid

    url = 'https://atum%s.hac.%s.d4c.nintendo.net/t/a/%s/%s?device_id=%s' % (n, env, tid, ver, did)
    print_(url)
    try:
        r = make_request('HEAD', url)
    except Exception as e:
        print_("Error downloading title. Check for incorrect titleid or version.")
        return ''
    CNMTid = r.headers.get('X-Nintendo-Content-ID')

    print_('\nDownloading CNMT (%s.cnmt.nca)...' % CNMTid)
    url = 'https://atum%s.hac.%s.d4c.nintendo.net/c/a/%s?device_id=%s' % (n, env, CNMTid, did)
    if CNMTid == None:
        return ''
    fPath = os.path.join(tempDir, CNMTid + '.cnmt.nca')
    cnmtNCA = download_file(url, fPath)
    cnmtDir = decrypt_NCA(cnmtNCA)
    CNMT = cnmt(os.path.join(cnmtDir, 'section0', os.listdir(os.path.join(cnmtDir, 'section0'))[0]),
                os.path.join(cnmtDir, 'Header.bin'))

    for ncaID in CNMT.parse(CNMT.ncaTypes[3]):
        print_('\nDownloading %s entry (%s.nca)...' % (CNMT.ncaTypes[3], ncaID))
        url = 'https://atum%s.hac.%s.d4c.nintendo.net/c/c/%s?device_id=%s' % (n, env, ncaID, did)
        fPath = os.path.join(controlDir, ncaID + '.nca')
        ncaPath = download_file(url, fPath)
        shutil.rmtree(tempDir)
        return ncaPath

def extract_control_nca(ncaFile):
    extractDir = '_NCAEXTRACT'
    command = '%s %s %s --section0dir="%s"' % (hactoolPath,keysArg,ncaFile,extractDir)
    try:
        output = str(subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True))
    except subprocess.CalledProcessError as exc:
        print_("Status : FAIL", exc.returncode, exc.output)
        return False
    print_("\nNCA extraction successful.")
    return extractDir




def get_name_control(tid):
    global quiet
    quiet = True
    basetid = tid
    if tid.endswith('000'):  # Base game
        pass
    elif tid.endswith('800'):  # Update
        basetid = '%s000' % tid[:-3]
    else:  # DLC
        basetid = '%016x' % (int(tid, 16) - 0x1000 & 0xFFFFFFFFFFFFF000)
    name = ''
    tkey = get_titlekey(basetid)
    ver = get_versions(basetid)[-1]
    ncaFile = get_control_nca(basetid,ver,tkey)
    if ncaFile == '':
        return ''
    extractDir = extract_control_nca(ncaFile)
    nacpFile = os.path.join(extractDir,'control.nacp')
    pos = 0
    with open(nacpFile, 'rb') as f:
        wf = TextIOWrapper(f, 'utf-8')
        wf._CHUNK_SIZE = 1  
        while wf.read(1) == '':
            pos = pos + 1
        wf.seek(pos)
        name  = wf.read(100).rstrip(' \t\r\n\0')

    shutil.rmtree(extractDir)
    os.remove(ncaFile)
    quiet = False
    return name.strip()
    
    

def get_titlekey(tid):
    for line in titlekey_list:
        if tid in line:
            return line.split('|')[1].strip()
    return ''


def download_game(tid, ver, tkey='', nspRepack=False, name='', verify=False):
    name = get_name(tid)
    gameType = ''

    if name == 'Uknown Title':
        temp = "[" + tid + "]"
    else:
        temp = name + " [" + tid + "]"

    basetid = ''
    if tid.endswith('000'):  # Base game
        gameDir = os.path.join(os.path.dirname(__file__), temp)
        gameType = 'BASE'
    elif tid.endswith('800'):  # Update
        basetid = '%s000' % tid[:-3]
        gameDir = os.path.join(os.path.dirname(__file__), temp)
        gameType = 'UPD'
    else:  # DLC
        basetid = '%s%s000' % (tid[:-4], str(int(tid[-4], 16) - 1))
        gameDir = os.path.join(os.path.dirname(__file__), temp)
        gameType = 'DLC'

    os.makedirs(gameDir, exist_ok=True)

    outputDir = os.path.join(os.path.dirname(__file__), nspout)

    if not os.path.exists(outputDir):
        os.makedirs(outputDir, exist_ok=True)

   
    if name != "":
        if gameType == 'BASE':
             outf = os.path.join(outputDir, '%s [%s][v%s]' % (name,tid,ver))
        else:
            outf = os.path.join(outputDir, '%s [%s][%s][v%s]' % (name,gameType,tid,ver))
    else:
        if gameType == 'BASE':
            outf = os.path.join(outputDir, '%s [v%s]' % (tid,ver))
        else:
            outf = os.path.join(outputDir, '%s [%s][v%s]' % (tid,gameType,ver))

    if truncateName:
        name = name.replace(' ','')[0:20]
        outf = os.path.join(outputDir, '%s%sv%s' % (name,tid,ver))

    if tinfoil:
        outf = outf + '[tf]'

    outf = outf + '.nsp'

    for item in os.listdir(outputDir):
        if item.find('%s' % tid) != -1:
            if item.find('v%s' % ver) != -1:
                if not tinfoil:
                    print_('%s already exists, skipping download' % outf)
                    shutil.rmtree(gameDir)
                    return

    if tinfoil:
        files = download_title_tinfoil(gameDir, tid, ver, tkey, nspRepack, verify=verify)
    else:
        files = download_title(gameDir, tid, ver, tkey, nspRepack, verify=verify)

    if gameType != 'UPD':
        verified = verify_NCA(get_biggest_file(gameDir), tkey)

        if not verified:
            shutil.rmtree(gameDir)
            print_('\ncleaned up downloaded content')
            return

    if nspRepack == True:
        if files == None:
            return
        NSP = nsp(outf, files)
        print_('\nstarting repack, This may take a while')
        NSP.repack()
        shutil.rmtree(gameDir)
        print_('\ncleaned up downloaded content')

        if enxhop:
            enxhopDir = os.path.join(outputDir,'switch')
            os.makedirs(enxhopDir, exist_ok=True)
            with open(os.path.join(enxhopDir,'eNXhop.txt'), 'a+') as f:
                f.write(tid + '\n')

        return outf

    return gameDir


def download_sysupdate(ver):
    if ver == '0':
        url = 'https://sun.hac.%s.d4c.nintendo.net/v1/system_update_meta?device_id=%s' % (env, did)
        r = make_request('GET', url)
        j = r.json()
        ver = str(j['system_update_metas'][0]['title_version'])

    sysupdateDir = os.path.join(os.path.dirname(__file__), '0100000000000816', ver)
    os.makedirs(sysupdateDir, exist_ok=True)

    url = 'https://atumn.hac.%s.d4c.nintendo.net/t/s/0100000000000816/%s?device_id=%s' % (env, ver, did)
    r = make_request('HEAD', url)

    cnmtID = r.headers.get('X-Nintendo-Content-ID')
    print_('\nDownloading CNMT (%s)...' % cnmtID)
    url = 'https://atumn.hac.%s.d4c.nintendo.net/c/s/%s?device_id=%s' % (env, cnmtID, did)
    fPath = os.path.join(sysupdateDir, '%s.cnmt.nca' % cnmtID)
    cnmtNCA = download_file(url, fPath)
    dir = decrypt_NCA(cnmtNCA)
    CNMT = cnmt(os.path.join(dir, 'section0', os.listdir(os.path.join(dir, 'section0'))[0]))

    titles = CNMT.parse()
    for title in titles:
        dir = os.path.join(sysupdateDir, title)
        os.makedirs(dir, exist_ok=True)
        download_title(dir, title, titles[title][0], n='n')

    return sysupdateDir


class cnmt:
    def __init__(self, fPath, hdPath):
        self.packTypes = {0x1: 'SystemProgram',
                          0x2: 'SystemData',
                          0x3: 'SystemUpdate',
                          0x4: 'BootImagePackage',
                          0x5: 'BootImagePackageSafe',
                          0x80: 'Application',
                          0x81: 'Patch',
                          0x82: 'AddOnContent',
                          0x83: 'Delta'}

        self.ncaTypes = {0: 'Meta', 1: 'Program', 2: 'Data', 3: 'Control',
                         4: 'HtmlDocument', 5: 'LegalInformation', 6: 'DeltaFragment'}

        f = open(fPath, 'rb')

        self.path = fPath
        self.type = self.packTypes[read_u8(f, 0xC)]
        self.id = '0%s' % format(read_u64(f, 0x0), 'x')
        self.ver = str(read_u32(f, 0x8))
        self.sysver = str(read_u64(f, 0x28))
        self.dlsysver = str(read_u64(f, 0x18))
        self.digest = hx(read_at(f, f.seek(0, 2) - 0x20, f.seek(0, 2))).decode()

        with open(hdPath, 'rb') as ncaHd:
            self.mkeyrev = str(read_u8(ncaHd, 0x220))

        f.close()

    def parse(self, ncaType=''):
        f = open(self.path, 'rb')

        data = {}
        if self.type == 'SystemUpdate':
            EntriesNB = read_u16(f, 0x12)
            for n in range(0x20, 0x10 * EntriesNB, 0x10):
                tid = hex(read_u64(f, n))[2:]
                if len(tid) != 16:
                    tid = '%s%s' % ((16 - len(tid)) * '0', tid)
                ver = str(read_u32(f, n + 0x8))
                packType = self.packTypes[read_u8(f, n + 0xC)]

                data[tid] = ver, packType
        else:
            tableOffset = read_u16(f, 0xE)
            contentEntriesNB = read_u16(f, 0x10)
            cmetadata = {}
            for n in range(contentEntriesNB):
                offset = 0x20 + tableOffset + 0x38 * n
                hash = hx(read_at(f, offset, 0x20)).decode()
                tid = hx(read_at(f, offset + 0x20, 0x10)).decode()
                size = str(read_u48(f, offset + 0x30))
                type = self.ncaTypes[read_u16(f, offset + 0x36)]

                if type == ncaType or ncaType == '':
                    data[tid] = type, size, hash

        f.close()
        return data

    def gen_xml(self, ncaPath, outf):
        data = self.parse()
        hdPath = os.path.join(os.path.dirname(ncaPath),
                              '%s.cnmt' % os.path.basename(ncaPath).split('.')[0], 'Header.bin')
        with open(hdPath, 'rb') as ncaHd:
            mKeyRev = str(read_u8(ncaHd, 0x220))

        ContentMeta = ET.Element('ContentMeta')

        ET.SubElement(ContentMeta, 'Type').text = self.type
        ET.SubElement(ContentMeta, 'Id').text = '0x%s' % self.id
        ET.SubElement(ContentMeta, 'Version').text = self.ver
        ET.SubElement(ContentMeta, 'RequiredDownloadSystemVersion').text = self.dlsysver

        n = 1
        for tid in data:
            locals()["Content" + str(n)] = ET.SubElement(ContentMeta, 'Content')
            ET.SubElement(locals()["Content" + str(n)], 'Type').text = data[tid][0]
            ET.SubElement(locals()["Content" + str(n)], 'Id').text = tid
            ET.SubElement(locals()["Content" + str(n)], 'Size').text = data[tid][1]
            ET.SubElement(locals()["Content" + str(n)], 'Hash').text = data[tid][2]
            ET.SubElement(locals()["Content" + str(n)], 'KeyGeneration').text = mKeyRev
            n += 1

        # cnmt.nca itself
        cnmt = ET.SubElement(ContentMeta, 'Content')
        ET.SubElement(cnmt, 'Type').text = 'Meta'
        ET.SubElement(cnmt, 'Id').text = os.path.basename(ncaPath).split('.')[0]
        ET.SubElement(cnmt, 'Size').text = str(os.path.getsize(ncaPath))
        hash = sha256()
        with open(ncaPath, 'rb') as nca:
            hash.update(nca.read())  # Buffer not needed
        ET.SubElement(cnmt, 'Hash').text = hash.hexdigest()
        ET.SubElement(cnmt, 'KeyGeneration').text = mKeyRev

        ET.SubElement(ContentMeta, 'Digest').text = self.digest
        ET.SubElement(ContentMeta, 'KeyGenerationMin').text = self.mkeyrev
        ET.SubElement(ContentMeta, 'RequiredSystemVersion').text = self.sysver
        if self.id.endswith('800'):
            ET.SubElement(ContentMeta, 'PatchId').text = '0x%s000' % self.id[:-3]
        else:
            ET.SubElement(ContentMeta, 'PatchId').text = '0x%s800' % self.id[:-3]

        string = ET.tostring(ContentMeta, encoding='utf-8')
        reparsed = minidom.parseString(string)
        with open(outf, 'w') as f:
            f.write(reparsed.toprettyxml(encoding='utf-8', indent='  ').decode()[:-1])

        print_('\nGenerated %s!' % os.path.basename(outf))
        return outf

    def gen_xml_tinfoil(self, ncaPath, outf):
        data = self.parse()
        hdPath = os.path.join(os.path.dirname(ncaPath),
                              '%s.cnmt' % os.path.basename(ncaPath).split('.')[0], 'Header.bin')
        with open(hdPath, 'rb') as ncaHd:
            mKeyRev = str(read_u8(ncaHd, 0x220))

        ContentMeta = ET.Element('ContentMeta')

        ET.SubElement(ContentMeta, 'Type').text = self.type
        ET.SubElement(ContentMeta, 'Id').text = '0x%s' % self.id
        ET.SubElement(ContentMeta, 'Version').text = self.ver
        ET.SubElement(ContentMeta, 'RequiredDownloadSystemVersion').text = self.dlsysver

        n = 1
        for tid in data:
            if data[tid][0] == 'Control':
                locals()["Content" + str(n)] = ET.SubElement(ContentMeta, 'Content')
                ET.SubElement(locals()["Content" + str(n)], 'Type').text = data[tid][0]
                ET.SubElement(locals()["Content" + str(n)], 'Id').text = tid
                ET.SubElement(locals()["Content" + str(n)], 'Size').text = data[tid][1]
                ET.SubElement(locals()["Content" + str(n)], 'Hash').text = data[tid][2]
                ET.SubElement(locals()["Content" + str(n)], 'KeyGeneration').text = mKeyRev
                n += 1

        # cnmt.nca itself
        hash = sha256()
        with open(ncaPath, 'rb') as nca:
            hash.update(nca.read())  # Buffer not needed
        ET.SubElement(ContentMeta, 'Digest').text = self.digest
        ET.SubElement(ContentMeta, 'KeyGenerationMin').text = self.mkeyrev
        ET.SubElement(ContentMeta, 'RequiredSystemVersion').text = self.sysver
        if self.id.endswith('800'):
            ET.SubElement(ContentMeta, 'PatchId').text = '0x%s000' % self.id[:-3]
        else:
            ET.SubElement(ContentMeta, 'PatchId').text = '0x%s800' % self.id[:-3]

        string = ET.tostring(ContentMeta, encoding='utf-8')
        reparsed = minidom.parseString(string)
        with open(outf, 'w') as f:
            f.write(reparsed.toprettyxml(encoding='utf-8', indent='  ').decode()[:-1])

        print_('\nGenerated %s!' % os.path.basename(outf))
        return outf


class nsp:
    def __init__(self, outf, files):
        self.path = outf
        self.files = files

    def repack(self):
        print_('\tRepacking to NSP...')
        
        hd = self.gen_header()
        
        totSize = len(hd) + sum(os.path.getsize(file) for file in self.files)
        if os.path.exists(self.path) and os.path.getsize(self.path) == totSize:
            print_('\t\tRepack %s is already complete!' % self.path)
            return
            
        t = tqdm(total=totSize, unit='B', unit_scale=True, desc=os.path.basename(self.path), leave=False)
        
        t.write('\t\tWriting header...')
        outf = open(self.path, 'wb')
        outf.write(hd)
        t.update(len(hd))
        
        done = 0
        for file in self.files:
            t.write('\t\tAppending %s...' % os.path.basename(file))
            with open(file, 'rb') as inf:
                while True:
                    buf = inf.read(4096)
                    if not buf:
                        break
                    outf.write(buf)
                    t.update(len(buf))
        t.close()
        
        print_('\t\tRepacked to %s!' % outf.name)
        outf.close()

    def gen_header(self):
        filesNb = len(self.files)
        stringTable = '\x00'.join(os.path.basename(file) for file in self.files)
        headerSize = 0x10 + (filesNb)*0x18 + len(stringTable)
        remainder = 0x10 - headerSize%0x10
        headerSize += remainder
        
        fileSizes = [os.path.getsize(file) for file in self.files]
        fileOffsets = [sum(fileSizes[:n]) for n in range(filesNb)]
        
        fileNamesLengths = [len(os.path.basename(file))+1 for file in self.files] # +1 for the \x00
        stringTableOffsets = [sum(fileNamesLengths[:n]) for n in range(filesNb)]
        
        header =  b''
        header += b'PFS0'
        header += pk('<I', filesNb)
        header += pk('<I', len(stringTable)+remainder)
        header += b'\x00\x00\x00\x00'
        for n in range(filesNb):
            header += pk('<Q', fileOffsets[n])
            header += pk('<Q', fileSizes[n])
            header += pk('<I', stringTableOffsets[n])
            header += b'\x00\x00\x00\x00'
        header += stringTable.encode()
        header += remainder * b'\x00'
        
        return header

def load_titlekeys():
    global titlekey_list
    try:
        print_('\nloading titlekeys...')
        with open('titlekeys.txt', encoding="utf8") as f:
            lines = f.readlines()
    except Exception as e:
        print_("Error:", e)
        print_('the -title command will NOT WORK to download games without it')
        return
    try:
        for line in lines:
            temp = line.split('|')
            tid = temp[0][0:16]
            tkey = temp[1]
            name = temp[2]
            line = '%s|%s|%s' % (tid,tkey,name)
            titlekey_list.append(line)
        print_('\ntitlekeys loaded')
    except Exception as e:
        print_('Error: ', e)
        return

def update_db():
    global titlekey_list
    print_("\nDownloading new titlekey database...\n")
    try:
        url = dbURL
        if url == '':
            print_('\nDatabase url is empty. Check the CDNSPconfig')
            return
        if "http://" not in url and "https://" not in url:
            try:
                url = base64.b64decode(url)
            except Exception as e:
                print_("\nError decoding url: ", e)
                return

        r = requests.get(url)
        r.encoding = 'utf-8'

        if r.status_code == 200:
            newdb = r.text.split('\r')

            currdb = [x.strip() for x in titlekey_list]
            print_('The following games have either been added or updated:\n')
            for line in newdb:
                line = line.strip()
                if line != '':
                    temp = line.split('|')
                    tid = temp[0][0:16]
                    tkey = temp[1]
                    name = temp[2]
                    line = '%s|%s|%s' % (tid,tkey,name)
                    if line not in currdb and line != None :
                        print_(line.split('|')[-1])

            try:
                print_('\nSaving new database...')
                f = open('titlekeys.txt', 'w', encoding="utf8")
                for line in newdb:
                    f.write(line)
                f.close()
                print_('\nDatabase update complete')
                titlekey_list = []
                load_titlekeys()
            except Exception as e:
                print_(e)
                return
        else:
            print_('Error updating database: ', repr(r))
            return
            
    except Exception as e:
        print_('\nError updating database:', e)
        return

def title_in_keylist(tid):
    global titlekey_list
    for title in titlekey_list:
        if title.find(tid) != -1:
            return True
    return False


def main():
    formatter = lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=40)
    parser = argparse.ArgumentParser(formatter_class=formatter)

    parser.add_argument('-i', dest='info', default=[], metavar='TID', nargs='+', help='''\
print_ info about a title:
   - name from titlekeys.txt
   - available updates from versionlist''')

    parser.add_argument('-infodump', dest='infodump', default=[], metavar='TID', nargs='+', help='''\
dumps info to infodump.txt info about a title:
   - name from titlekeys.txt
   - available updates from versionlist''')

    parser.add_argument('-title', dest='title', default=[], metavar='TID', nargs='+', help='''\
Downloads game only passing in titleid. Uses titlekeys.txt to lookup titlekey.
	You need to have titlekeys.txt in root of folder.
	usage:
	 -title titleid (...titleid titleid titleid): this will download latest version for this title or base version/"license" of a dlc (not updates)''')

    parser.add_argument('-alldlc', dest='alldlc', action='store_true', default=False, help='''\
Used with -title. lets you download all dlc for current game in the tid list.''')

    parser.add_argument('-justupdate', dest='justupdate', action='store_true', default=False, help='''\
Used with -title. lets you download just the update for a game. Will get latest version''')

    parser.add_argument('-update', dest='update', action='store_true', default=False, help='''\
Used with -title. lets you downloads update along with games.''')

    parser.add_argument('-n', dest='name', default=[], metavar='TID', nargs='+', help='''\
print_ name of title''')

    parser.add_argument('-g', dest='games', default=[], metavar='TID-VER-TKEY', nargs='+', help='''\
[LEGACY DONT USE] download games/updates/DLC's:
   - titlekey argument is optional
   - format TitleID-Version(-Titlekey)
   - update TitleID's are the same as the base game's,
	 with the three last digits replaced with '800'
   - version is 0 for base games, multiple of 65536 (0x10000) for updates''')

    parser.add_argument('-s', dest='sysupdates', default=[], metavar='VER', nargs='+', help='''\
download system updates:
   - version is computed as follows (credit goes to SocraticBliss):
   - X.Y.Z-B (all decimal integers)
	 => VER = X*67108864 + Y*1048576 + Z*65536 + B
		   (= X*0x4000000 + Y*0x100000 + Z*0x10000 + B)
   - 0 will download the lastest update''')

    parser.add_argument('-r', dest='repack', action='store_true', default=False, help='''\
[ONLY NEEDED WITH -g] repack the downloaded games to nsp format
   - for non-update titles, titlekey is required to generate tik
   - will generate/download cert, tik and cnmt.xml''')

    parser.add_argument('-verify', dest='verify', action='store_true', default=False, help='''\
verifies the downloaded files (this is NOT the same thing as titlekey verification)
   - computes hashes of downloaded files and compares them against the CNMT
   - processing can take a while for big files
   - if a file is corrupted, delete it and restart the download''')

    parser.add_argument('-trunc', dest='trunc', action='store_true', default=False, help='''\
repacked nsp name will be truncated''')

    parser.add_argument('-updatedb', dest='updatedb', action='store_true', default=False, help='''\
download the latest titlekeys.txt file''')

    parser.add_argument('-tinfoil', dest='tinfoil', action='store_true', default=False, help='''\
download the latest titlekeys.txt file''')

    parser.add_argument('-enxhop', dest='enxhop', action='store_true', default=False, help='''\
download the latest titlekeys.txt file''')

    parser.add_argument('-searchdb', dest='searchdb', default=[], metavar='Name', nargs='+', help='''\
search the titlekey db by game name
uses basic contains search
usage -searchdb zelda''')

    args = parser.parse_args()

    if args.games == [] and args.sysupdates == [] and args.info == [] and args.name == [] and args.title == [] and args.infodump == [] and not args.updatedb and args.searchdb == [] and not args.alldlc and not args.justupdate and not args.trunc and not args.tinfoil and not args.enxhop:
        parser.print_help()
        return 1
 
    load_titlekeys()

    global tinfoil

    if autoUpdatedb == 'True':
        update_db()

    if args.tinfoil:
        tinfoil = True

    if args.enxhop:
        global enxhop
        enxhop = True
        tinfoil = True

        enxhopDir = os.path.join(nspout,'switch')
        if os.path.exists(enxhopDir):
            shutil.rmtree(enxhopDir)
        
    if args.trunc:
        global truncateName
        truncateName = True

    def setup_download(tid, ver, tkey, nspRepack, name=''):
        tid = tid.lower()
        try:
            if len(tid) != 16:
                raise ValueError('TitleID %s is not a 16-digits hexadecimal number!' % tid)
            if len(tkey) != 32 and len(tkey) != 0:
                raise ValueError('Titlekey %s is not a 32-digits hexadecimal number!' % tkey)
        except ValueError as e:
            print_(e)
            return

        download_game(tid.lower(), ver, tkey.lower(), nspRepack, name, args.verify)

    if args.title:
        for title in args.title:
            tid = title.strip().lower()[0:16]
            updateVer = 'none'
            updateTid = ''

            if (args.update or args.justupdate) and tid.endswith("000"):
                updateTid = '%s%s' % (tid[0:13], '800')
                updateVersions = get_versions(updateTid)
                if 'none' not in updateVersions:
                    updateVer = updateVersions[-1]
                else:
                    print_("no updates available for the game")

            try:
                for line in titlekey_list:
                    if line.strip() == '':
                        continue
                    temp = line.split("|")
                    if len(temp) < 3:
                        continue
                    listTid = temp[0].strip()
                    listTkey = temp[1].strip()
                    if tid == listTid:
                        if not args.justupdate:
                            if tid.endswith("000"): #base 
                                setup_download(listTid, get_versions(listTid)[-1], listTkey, True)
                            else: #dlc
                                # set dlc ver to 0 becaus that seems the only way we can get it to work all the time
                                setup_download(listTid,'0', listTkey, True)
                        if tid.endswith("000") and updateVer != 'none':
                            # update
                            setup_download(updateTid, updateVer, '', True)
                        if args.alldlc:
                            searchdlctid = listTid[0:12]
                            for title in titlekey_list:
                                if searchdlctid in title:
                                    split = title.split('|')
                                    dlctkey = split[1]
                                    dlctid = split[0]
                                    if dlctkey != listTkey:
                                        # set dlc ver to 0 becaus that seems the only way we can get it to work all the time
                                        setup_download(dlctid,'0',dlctkey, True)
                            
            except Exception as e:
                print_('Error:', e)

    for tid in args.info:
        get_info(tid)

    if args.infodump:
        if os.path.isfile('infodump.txt'):
            os.remove("infodump.txt")
            print_('removed old infodump.txt')

        for tid in args.infodump:
            silent = True
            if os.path.isfile('infodump.txt'):
                with open('infodump.txt', 'a', encoding="utf8") as f:
                    f.write(get_info(tid, silent))
                    f.close()
            else:
                f = open('infodump.txt', 'w', encoding="utf8")
                f.write(get_info(tid, silent))
                f.close()
        print_('info written to infodump.txt')

    if args.updatedb:
        update_db()
        
    if args.searchdb != []:
        search = ' '.join(args.searchdb)
        print_('')
        print_('Search Results:\n')
        for line in titlekey_list:
            line = line.strip()
            if line != '' and line != None:
                name = line.split('|')[2]
                if search.lower() in name.lower():
                    temp = line.split('|')
                    tid = temp[0]
                    tkey = temp[1]
                    name = temp[2]
                    print_(tid,tkey,name)

    for tid in args.name:
        get_name(tid)

    for game in args.games:
        try:
            tid, ver, tkey = game.split('-')
        except ValueError:
            try:
                tid, ver = game.split('-')
                tkey = ''
            except ValueError:
                print_('Incorrect game argument (%s): should be formatted this way: TID-VER(-TKEY)!' % game)
                return 1
        setup_download(tid[0:16], ver, tkey, args.repack, get_name(tid))

    for ver in args.sysupdates:
        download_sysupdate(ver)

    # print_('Done!')
    return 0


if __name__ == '__main__':
    urllib3.disable_warnings()

    try:
        from tqdm import tqdm

        tqdmProgBar = True
    except ImportError:
        tqdmProgBar = False
        print_('Install the tqdm library for better-looking progress bars! (pip install tqdm)')

    configPath = os.path.join(os.path.dirname(__file__), 'CDNSPconfig.json')
    hactoolPath, keysPath, NXclientPath, ShopNPath, reg, fw, did, env, dbURL, nspout, autoUpdatedb = load_config(configPath)

    if keysPath != '':
        keysArg = ' -k "%s"' % keysPath
    else:
        keysArg = ''

    sys.exit(main())
