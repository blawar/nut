#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from nut_impl import printer, config

def makeRequest(method, url, hdArgs={}, start=None, end=None, accept='*/*'):
    reqHd = {
        'Accept': accept,
        'Connection': None,
        'Accept-Encoding': None,
    }
    if start is not None:
        reqHd['Range'] = 'bytes=%d-%d' % (start, end-1)

    reqHd.update(hdArgs)

    r = requests.request(
        method,
        url,
        headers=reqHd,
        verify=False,
        stream=True,
        timeout=15
    )

    printer.debug(f'{method} {str(r.status_code)} {url}')
    printer.debug(r.request.headers)

    if r.status_code == 403:
        raise IOError('Forbidden ' + r.text)

    return r


def downloadProxyFile(url, response, start=None, end=None, headers={}):
    bytes = 0

    r = makeRequest('GET', url, start=start, end=end, hdArgs=headers)
    size = int(r.headers.get('Content-Length'))

    chunkSize = 0x100000

    if size >= 10000:

        for chunk in r.iter_content(chunkSize):
            response.write(chunk)
            bytes += len(chunk)

            if not config.isRunning:
                break
    else:
        response.write(r.content)
        bytes += len(r.content)

    if size != 0 and bytes != size:
        raise ValueError(
            f'Downloaded data is not as big as expected ({bytes}/{size})!'
        )

    return bytes
