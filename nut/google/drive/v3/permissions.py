#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import List
from typing import Optional
from requests import Response
from datetime import datetime
from nut.google.drive.v3.files import FILES_BASE_URL
from google.auth.transport.requests import AuthorizedSession


class PermissionRole:
    __owner = 'owner'
    __organizer = 'organizer'
    __file_organizer = 'fileOrganizer'
    __writer = 'writer'
    __commenter = 'commenter'
    __reader = 'reader'

    @property
    def owner(self):
        return self.__owner

    @property
    def organizer(self):
        return self.__organizer

    @property
    def file_organizer(self):
        return self.__file_organizer

    @property
    def writer(self):
        return self.__writer

    @property
    def commenter(self):
        return self.__commenter

    @property
    def reader(self):
        return self.__reader


class PermissionType:
    __user = 'user'
    __group = 'group'
    __domain = 'domain'
    __anyone = 'anyone'

    @property
    def user(self):
        return self.__user

    @property
    def group(self):
        return self.__group

    @property
    def domain(self):
        return self.__domain

    @property
    def anyone(self):
        return self.__anyone


class Permissions:
    '''Class providing access to Drive V3 Permissions resources.'''
    def __init__(self, session: AuthorizedSession):
        self.__session = session

    def create(
        self,
        file_id: str,
        perm_type: PermissionType,
        perm_role: PermissionRole,
        view: Optional[bool] = None,
        domain: Optional[str] = None,
        fields: Optional[List[str]] = None,
        email_address: Optional[str] = None,
        email_message: Optional[str] = None,
        transfer_ownership: Optional[bool] = None,
        supports_all_drives: Optional[bool] = None,
        allow_file_discovery: Optional[bool] = None,
        enforce_single_parent: Optional[bool] = None,
        use_domain_admin_access: Optional[bool] = None,
        move_to_new_owners_root: Optional[bool] = None,
        **perm_info,
    ) -> Response:
        '''Creates a new permission for a file.

        For more info,
        https://developers.google.com/drive/api/v3/reference/permissions/create
        '''
        perm_info.update({
            'role': perm_role,
            'type': perm_type,
        })

        query_params = {}

        if perm_type == PermissionType.user or \
                perm_type == PermissionType.group:
            if email_address is None:
                raise ValueError(
                    '\'email_address\' was not provided with permission type' +
                    f' {perm_type}!'
                )

            perm_info.update({
                'emailAddress': email_address,
            })

            if email_message is not None:
                query_params.update({
                    'emailMessage': email_message,
                })

            query_params.update({
                'sendNotificationEmail': True,
            })

        elif perm_type == PermissionType.domain or perm_type == \
                PermissionType.anyone:
            if perm_type == PermissionType.domain:
                if domain is None:
                    raise TypeError('\'domain\' was not provided!')

                perm_info.update({
                    'domain': domain,
                })

            elif perm_type == PermissionType.anyone:
                pass

            perm_info.update({
                'allowFileDiscovery': allow_file_discovery,
            })

        else:
            raise NotImplementedError(
                f'{perm_type} logic not included! Unable to continue!'
            )

        if fields is not None:
            _fields = ','.join(fields)
            query_params.update({
                'fields': _fields,
            })

        if view is not None:
            perm_info.update({
                'view': view,
            })

        if use_domain_admin_access is not None:
            perm_info.update({
                'useDomainAdminAccess': use_domain_admin_access,
            })

        if transfer_ownership is not None:
            perm_info.update({
                'transferOwnership': transfer_ownership,
            })

        if supports_all_drives is not None:
            perm_info.update({
                'supportsAllDrives': supports_all_drives,
            })

        if move_to_new_owners_root is not None:
            perm_info.update({
                'moveToNewOwnersRoot': move_to_new_owners_root,
            })

        if enforce_single_parent is not None:
            perm_info.update({
                'enforceSingleParent': enforce_single_parent,
            })

        data = json.dumps(perm_info)

        headers = {
            'Content-Type': 'application/json',
            'Content-Length': len(data)
        }

        return self.__session.request(
            'POST',
            f'{FILES_BASE_URL}/{file_id}/permissions',
            params=query_params,
            headers=headers,
            data=data
        )

    def delete(
        self,
        file_id: str,
        perm_id: str,
        supports_all_drives: Optional[bool] = None,
        use_domain_admin_access: Optional[bool] = None,
    ) -> Response:
        '''Deletes a file permission with file ID and permission ID.

        For more information,
        https://developers.google.com/drive/api/v3/reference/permissions/delete
        '''
        query_params = {}

        if supports_all_drives is not None:
            query_params.update({
                'supportsAllDrives': supports_all_drives,
            })

        if use_domain_admin_access is not None:
            query_params.update({
                'useDomainAdminAccess': use_domain_admin_access,
            })

        return self.__session.request(
            'DELETE',
            f'{FILES_BASE_URL}/{file_id}/permissions/{perm_id}',
            params=query_params,
        )

    def get(
        self,
        file_id: str,
        perm_id: str,
        fields: Optional[List[str]] = None,
        supports_all_drives: Optional[bool] = None,
        use_domain_admin_access: Optional[bool] = None,
    ) -> Response:
        '''Retrieve a file permission information by file ID and
        permission ID.

        For more information,
        https://developers.google.com/drive/api/v3/reference/permissions/get
        '''
        params = {}

        if fields is not None:
            _fields = ','.join(fields)
            params.update({
                'fields': _fields,
            })

        if supports_all_drives is not None:
            params.update({
                'supportsAllDrives': supports_all_drives,
            })

        if use_domain_admin_access is not None:
            params.update({
                'useDomainAdminAccess': use_domain_admin_access,
            })

        return self.__session.request(
            'GET',
            f'{FILES_BASE_URL}/{file_id}/permissions/{perm_id}',
            params=params
        )

    def list_(
        self,
        file_id: str,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        fields: Optional[List[str]] = None,
        supports_all_drives: Optional[bool] = None,
        use_domain_admin_access: Optional[bool] = None,
        include_permissions_for_view: Optional[str] = None,
    ) -> Response:
        '''List all file permissions by file ID.

        For more information,
        https://developers.google.com/drive/api/v3/reference/permissions/list
        '''
        params = {}

        if page_size is not None:
            params.update({
                'pageSize': page_size,
            })

        if page_token is not None:
            params.update({
                'pageToken': page_token,
            })

        if fields is not None:
            _perm_fields = ','.join(fields)
            _fields = f'kind,nextPageToken,permissions({_perm_fields})'
            params.update({
                'fields': _fields,
            })

        if supports_all_drives is not None:
            params.update({
                'supportsAllDrives': supports_all_drives,
            })

        if use_domain_admin_access is not None:
            params.update({
                'useDomainAdminAccess': use_domain_admin_access,
            })

        if include_permissions_for_view is not None:
            params.update({
                'includePermissionsForView': include_permissions_for_view,
            })

        return self.__session.request(
            'GET',
            f'{FILES_BASE_URL}/{file_id}/permissions',
            params=params
        )

    def update(
        self,
        file_id: str,
        perm_id: str,
        view: Optional[str] = None,
        fields: Optional[List[str]] = None,
        role: Optional[PermissionRole] = None,
        remove_expiration: Optional[bool] = None,
        transfer_ownership: Optional[bool] = None,
        expiration_time: Optional[datetime] = None,
        supports_all_drives: Optional[bool] = None,
        use_domain_admin_access: Optional[bool] = None,
        **perm_info,
    ) -> Response:
        '''Update file permission information.

        For more information,
        https://developers.google.com/drive/api/v3/reference/permissions/update
        '''
        params = {}

        if fields is not None:
            _perm_fields = ','.join(fields)
            params.update({
                'fields': _perm_fields,
            })

        if remove_expiration is not None:
            params.update({
                'removeExpiration': remove_expiration,
            })

        if supports_all_drives is not None:
            params.update({
                'supportsAllDrives': supports_all_drives,
            })

        if transfer_ownership is not None:
            params.update({
                'transferOwnership': transfer_ownership,
            })

        if use_domain_admin_access is not None:
            params.update({
                'useDomainAdminAccess': use_domain_admin_access,
            })

        if expiration_time is not None:
            perm_info.update({
                'expirationTime': expiration_time.isoformat('T'),
            })

        if role is not None:
            perm_info.update({
                'role': role,
            })

        if view is not None:
            perm_info.update({
                'view': view,
            })

        data = json.dumps(perm_info)

        headers = {
            'Content-Type': 'application/json',
            'Content-Length': len(data),
        }

        return self.__session.request(
            'PATCH',
            f'{FILES_BASE_URL}/{file_id}/permissions/{perm_id}',
            headers=headers,
            params=params,
            data=data,
        )
