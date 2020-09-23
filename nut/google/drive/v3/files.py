#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from tqdm import tqdm
from time import time
from enum import Enum
from typing import List
from pathlib import Path
from typing import Optional
from requests import Response
from urllib.parse import urlparse
from nut.google.utils import path_to_hash
from nut.google.drive.v3 import DRIVE_V3_BASE_URL
from google.auth.transport.requests import AuthorizedSession

FILES_BASE_URL = f'{DRIVE_V3_BASE_URL}/files'


class FilesCorpora(Enum):
    user = 'user'
    drive = 'drive'
    domain = 'domain'
    all_drives = 'allDrives'


class FilesOrderBy(Enum):
    name = 'name'
    folder = 'folder'
    recency = 'recency'
    starred = 'starred'
    created_time = 'createdTime'
    name_natural = 'name_natural'
    modified_time = 'modifiedTime'
    quota_bytes_used = 'quotaBytesUsed'
    viewed_by_me_time = 'viewedByMeTime'
    modified_by_me_time = 'modifiedByMeTime'
    shared_with_me_time = 'sharedWithMeTime'


class Files:
    '''Class providing access to Drive V3 Files resources.'''
    def __init__(self, session: AuthorizedSession):
        self.__session = session

    def copy(
        self,
        file_id: str,
        fields: Optional[List[str]] = None,
        ocr_language: Optional[str] = None,
        supports_all_drives: Optional[str] = None,
        keep_revision_forever: Optional[bool] = None,
        enforce_single_parent: Optional[bool] = None,
        ignore_default_visibility: Optional[bool] = None,
        include_permissions_for_view: Optional[str] = None,
        **file_info,
    ) -> Response:
        '''Make a server side copy using file ID.

        For more information,
        https://developers.google.com/drive/api/v3/reference/files/copy
        '''
        params = {}

        if enforce_single_parent is not None:
            params.update({
                'enforceSingleParent': enforce_single_parent,
            })

        if fields is not None:
            _fields = ','.join(fields)
            params.update({
                'fields': _fields,
            })

        if ignore_default_visibility is not None:
            params.update({
                'ignoreDefaultVisibility': ignore_default_visibility,
            })

        if include_permissions_for_view is not None:
            params.update({
                'includePermissionsForView': include_permissions_for_view,
            })

        if keep_revision_forever is not None:
            params.update({
                'keepRevisionForever': keep_revision_forever,
            })

        if ocr_language is not None:
            params.update({
                'ocrLanguage': ocr_language,
            })

        if supports_all_drives is not None:
            params.update({
                'supportsAllDrives': supports_all_drives,
            })

        data = json.dumps(file_info)

        headers = {
            'Content-Type': 'application/json',
            'Content-Length': len(data),
        }

        return self.__session.request(
            'POST',
            f'{FILES_BASE_URL}/{file_id}/copy',
            params=params,
            headers=headers,
            data=data,
        )

    def delete(
        self,
        file_id: str,
        supports_all_drives: Optional[str] = None,
    ) -> Response:
        '''Delete a file using file ID.

        For more information,
        https://developers.google.com/drive/api/v3/reference/files/delete
        '''
        params = {}

        if supports_all_drives is not None:
            params.update({
                'supportsAllDrives': supports_all_drives,
            })

        return self.__session.request(
            'DELETE',
            f'{FILES_BASE_URL}/{file_id}',
            params=params,
        )

    def empty_trash(
        self,
    ) -> Response:
        '''Empty a user's trash.

        For more information,
        https://developers.google.com/drive/api/v3/reference/files/emptyTrash
        '''

        return self.__session.request(
            'DELETE',
            f'{FILES_BASE_URL}/trash',
        )

    def export(
        self,
        file_id: str,
        mime_type: str,
        fields: Optional[List[str]] = None,
    ) -> Response:
        '''Export a Google Doc to the requested MIME type.

        For more information,
        https://developers.google.com/drive/api/v3/reference/files/export
        '''
        params = {}

        params.update({
            'mimeType': mime_type,
        })

        if fields is not None:
            _fields = ','.join(fields)
            params.update({
                'fields': _fields,
            })

        return self.__session.request(
            'GET',
            f'{FILES_BASE_URL}/{file_id}/export',
            params=params,
        )

    def generate_ids(
        self,
        count: Optional[int],
        fields: Optional[List[str]] = None,
        space: Optional[str] = None,
    ) -> Response:
        '''Generates a set of file IDs which can be provided in create or copy
        requests.

        For more information,
        https://developers.google.com/drive/api/v3/reference/files/generateIds
        '''
        params = {}

        if fields is not None:
            _fields = ','.join(fields)
            params.update({
                'fields': _fields,
            })

        if count is not None:
            params.update({
                'count': count,
            })

        if space is not None:
            params.update({
                'space': space,
            })

        return self.__session.request(
            'GET',
            f'{FILES_BASE_URL}/generateIds',
            params=params,
        )

    def get(
        self,
    ):
        # TODO - Implementation of download file & get file metadata
        raise NotImplementedError('')

    def list_(
        self,
        q: Optional[str] = None,
        spaces: Optional[str] = None,
        drive_id: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        fields: Optional[List[str]] = None,
        corpora: Optional[FilesCorpora] = None,
        order_by: Optional[FilesOrderBy] = None,
        supports_all_drives: Optional[str] = None,
        include_permissions_for_view: Optional[str] = None,
        include_items_from_all_drives: Optional[bool] = None,
    ) -> Response:
        '''Get a list of files.

        For more information,
        https://developers.google.com/drive/api/v3/reference/files/list
        '''
        params = {}

        if fields is not None:
            files_field = ','.join(fields)
            _fields = 'kind,nextPageToken,incompleteSearch,' + \
                      f'files({files_field})'
            params.update({
                'fields': _fields,
            })

        if corpora is not None:
            params.update({
                'corpora': corpora,
            })

        if drive_id is not None:
            params.update({
                'driveId': drive_id,
            })

        if include_items_from_all_drives is not None:
            params.update({
                'includeItemsFromAllDrives': include_items_from_all_drives,
            })

        if include_permissions_for_view is not None:
            params.update({
                'includePermissionsForView': include_permissions_for_view,
            })

        if order_by is not None:
            params.update({
                'orderBy': order_by,
            })

        if page_size is not None:
            params.update({
                'pageSize': page_size,
            })

        if page_token is not None:
            params.update({
                'pageToken': page_token,
            })

        if q is not None:
            params.update({
                'q': q,
            })

        if spaces is not None:
            params.update({
                'spaces': spaces,
            })

        if supports_all_drives is not None:
            params.update({
                'supportsAllDrives': supports_all_drives,
            })

        return self.__session.request(
            'GET',
            f'{FILES_BASE_URL}/generateIds',
            params=params,
        )

    def __create_new_resumable_upload(
        self,
        file_path: Path,
        file_id: Optional[str] = None,
        parents: Optional[List[str]] = None,
    ) -> Response:
        params = {
            'uploadType': 'resumable',
        }

        file_size = f'{file_path.stat().st_size}'

        method = 'POST'
        url = 'https://www.googleapis.com/upload/drive/v3/files'

        body = {
            'name': file_path.name,
            'size': file_size,
        }

        if file_id is not None:
            body.update({'id': file_id})
            url += f'/{file_id}'
            method = 'PATCH'

        if parents is not None:
            body.update({'parents': parents})

        data = json.dumps(body)

        headers = {
            'X-Upload-Content-Length': file_size,
            'Content-Length': f'{len(data)}',
            'Content-Type': 'application/json; charset=UTF-8',
        }

        return self.__session.request(
            method,
            url,
            data=data,
            headers=headers,
            params=params,
        )

    def __resume_upload(
        self,
        upload_id: str,
        file_path: Path,
        chunk_size: Optional[int] = None,
        show_progress: bool = True,
    ) -> Response:
        file_size = file_path.stat().st_size
        res = self.__session.request(
            'PUT',
            'https://www.googleapis.com/upload/drive/v3/files',
            params={
                'uploadType': 'resumable',
                'upload_id': upload_id,
            },
            headers={
                'Content-Range': f'*/{file_size}',
            },
        )

        if res.status_code == 308:
            # Need to start uploading again
            to_upload_start = 0
            to_upload_end = file_size - 1
            to_upload_size = to_upload_end - to_upload_start + 1

            # Server has already received partial file, mark to send from next
            # byte of already received by server
            if 'Range' in res.headers:
                [_, _range] = res.headers['Range'].split('=')
                [_, uploaded_end] = _range.split('-')
                to_upload_start = uploaded_end + 1

            to_upload_size = to_upload_end - to_upload_start + 1

            with file_path.open(mode='rb') as file_stream:
                file_stream.seek(to_upload_start, 0)
                if chunk_size is None:
                    return self.__session.request(
                        'PUT',
                        'https://www.googleapis.com/upload/drive/v3/files',
                        data=file_stream,
                        params={
                            'uploadType': 'resumable',
                            'upload_id': upload_id,
                        },
                        headers={
                            'Content-Length': f'{to_upload_size}',
                            'Content-Range': f'bytes {to_upload_start}-' +
                            f'{to_upload_end}/{file_size}'
                        },
                        stream=True,
                    )
                else:
                    pbar = None

                    if show_progress:
                        pbar = tqdm(n=to_upload_start, total=file_size)

                    while to_upload_start < to_upload_end:
                        file_chunk = file_stream.read(chunk_size)

                        res = self.__session.request(
                            'PUT',
                            'https://www.googleapis.com/upload/drive/v3/files',
                            params={
                                'uploadType': 'resumable',
                                'upload_id': upload_id,
                            },
                            data=file_chunk,
                            headers={
                                'Content-Length': f'{len(file_chunk)}',
                                'Content-Range': f'bytes {to_upload_start}-' +
                                f'{to_upload_end}/{file_size}'
                            },
                        )

                        if pbar is not None:
                            pbar.update(len(file_chunk))

                        if res.status_code != 308:
                            break

                        else:
                            to_upload_start = to_upload_end
                            remaining_size = file_size - file_stream.tell()
                            to_upload_end += chunk_size if remaining_size > \
                                chunk_size else remaining_size

                        if pbar is not None:
                            pbar.close()

        return res

    def upload_resumable(
        self,
        file_path: Path,
        file_id: Optional[str] = None,
        parents: Optional[List[str]] = None,
        chunk_size: Optional[int] = None,
        show_progress: bool = True,
        cache_expire: int = 7 * 24 * 3600,
    ) -> Response:
        resume_cache_path = Path(f'cache/{path_to_hash(file_path)}')
        resume_session_start_time = resume_cache_path.stat().st_mtime
        now = time()

        # Cache file found which contains a resumable upload ID
        if resume_cache_path.is_file() and resume_session_start_time + \
                cache_expire < now:
            with resume_cache_path.open(mode='r') as cache_stream:
                upload_id = cache_stream.read()

                return self.__resume_upload(
                    upload_id,
                    file_path,
                    chunk_size=chunk_size,
                    show_progress=show_progress,
                )

        else:
            res = self.__create_new_resumable_upload(
                file_path,
                file_id=file_id,
                parents=parents,
            )

            if res.status_code == 200:
                url = urlparse(res.headers['Location'])
                for query in url.query.split('&'):
                    [query_key, query_value] = query.split('=')

                    if query_key == 'upload_id':
                        with resume_cache_path.open(mode='w') as cache_stream:
                            cache_stream.write(query_value)

                        return self.__resume_upload(
                            query_value,
                            file_path,
                            chunk_size=chunk_size,
                            show_progress=show_progress,
                        )

                raise ValueError('No resumable upload ID found with ' +
                                 'status code 200!')
            else:
                return res

    def download_file(
        self,
        file_id: str,
        file_path: Path,
        chunk_size: int = 4 * 1024 * 1024,
        show_progress: bool = True,
    ) -> Response:
        params = {
            'alt': 'media',
            'supportAllDrives': True,
            'acknowledgeAbuse': True,
        }

        with self.__session.request(
            'GET',
            f'https://www.googleapis.com/drive/v3/files/{file_id}',
            params=params,
            stream=True,
        ) as res:
            pbar = None

            if show_progress:
                pbar = tqdm(total=int(res.headers['Content-Size']))

            with file_path.open(mode='wb') as file_stream:
                for chunk in res.iter_content(chunk_size=chunk_size):
                    file_stream.write(chunk)

                    if pbar is not None:
                        pbar.update(len(chunk))

            if pbar is not None:
                pbar.close()

# TODO - Documentation for upload_resumable and download_file
