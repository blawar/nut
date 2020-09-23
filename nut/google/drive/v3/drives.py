#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import List
from typing import Optional
from requests import Response
from uuid import uuid4 as uuid_generator
from nut.google.drive.v3 import DRIVE_V3_BASE_URL
from google.auth.transport.requests import AuthorizedSession

DRIVES_BASE_URL = f'{DRIVE_V3_BASE_URL}/drives'


class Drives:
    '''Class providing access to Drive V3 Shared Drives resources.'''
    def __init__(self, session: AuthorizedSession):
        self.__session = session

    def create(
        self,
        drive_name: str,
        **drive_info,
    ) -> Response:
        '''Creates a new shared drive.

        For more information,
        https://developers.google.com/drive/api/v3/reference/drives/create
        '''
        req_id = uuid_generator()

        params = {
            'requestId': str(req_id),
        }

        drive_info.update({
            'name': drive_name,
        })

        data = json.dumps(drive_info)

        headers = {
            'Content-Type': 'application/json',
            'Content-Length': len(data),
        }

        return self.__session.request(
            'POST',
            DRIVES_BASE_URL,
            params=params,
            headers=headers,
            data=data,
        )

    def delete(
        self,
        drive_id: str,
    ) -> Response:
        '''Deletes a new shared drive with shared drive ID.

        For more information,
        https://developers.google.com/drive/api/v3/reference/drives/delete
        '''
        return self.__session.request(
            'DELETE',
            f'{DRIVES_BASE_URL}/{drive_id}',
        )

    def get(
        self,
        drive_id: str,
        fields: Optional[List[str]] = None,
        use_domain_admin_access: Optional[bool] = None,
    ) -> Response:
        '''Retrieve a shared drive information via Shared Drive ID.

        For more information,
        https://developers.google.com/drive/api/v3/reference/drives/get
        '''
        params = {}

        if fields is not None:
            _fields = ','.join(fields)
            params.update({'fields': _fields})

        if use_domain_admin_access is not None:
            params.update({
                'useDomainAdminAccess': use_domain_admin_access,
            })

        return self.__session.request(
            'GET',
            f'{DRIVES_BASE_URL}/{drive_id}',
            params=params
        )

    def hide(
        self,
        drive_id: str,
    ) -> Response:
        '''Hides a shared drive with shared drive ID.

        For more information,
        https://developers.google.com/drive/api/v3/reference/drives/hide
        '''
        return self.__session.request(
            'POST',
            f'{DRIVES_BASE_URL}/{drive_id}/hide',
        )

    def list_(
        self,
        q: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        fields: Optional[List[str]] = None,
        use_domain_admin_access: Optional[bool] = None,
    ) -> Response:
        '''List all shared drives.

        For more information,
        https://developers.google.com/drive/api/v3/reference/drives/list
        '''
        params = {}

        if fields is not None:
            _drive_fields = ','.join(fields)
            _fields = f'kind,nextPageToken,drives({_drive_fields})'
            params.update({
                'fields': _fields,
            })

        if q is not None:
            params.update({
                'q': q,
            })

        if page_size is not None:
            params.update({
                'pageSize': page_size,
            })

        if page_token is not None:
            params.update({
                'pageToken': page_token,
            })

        if use_domain_admin_access is not None:
            params.update({
                'useDomainAdminAccess': use_domain_admin_access,
            })

        return self.__session.request(
            'GET',
            DRIVES_BASE_URL,
            params=params,
        )

    def unhide(
        self,
        drive_id: str
    ) -> Response:
        '''Unhides a shared drive with shared drive ID.

        For more information,
        https://developers.google.com/drive/api/v3/reference/drives/unhide
        '''
        return self.__session.request(
            'POST',
            f'{DRIVES_BASE_URL}/{drive_id}/unhide'
        )

    def update(
        self,
        drive_id: str,
        use_domain_admin_access: Optional[bool] = None,
        **drive_info,
    ) -> Response:
        '''Update Shared Drive information.

        For more information,
        https://developers.google.com/drive/api/v3/reference/drives/update
        '''
        params = {}

        if use_domain_admin_access is not None:
            params.update({
                'useDomainAdminAccess': use_domain_admin_access,
            })

        data = json.dumps(drive_info)

        headers = {
            'Content-Type': 'application/json',
            'Content-Length': len(data),
        }

        return self.__session.request(
            'PATCH',
            f'{DRIVES_BASE_URL}/{drive_id}',
            headers=headers,
            params=params,
            data=data,
        )
