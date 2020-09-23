#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from nut.google.drive.v3.files import Files
from nut.google.drive.v3.drives import Drives
from google.auth.credentials import Credentials
from nut.google.auth.helpers import gen_auth_session
from nut.google.drive.v3.permissions import Permissions

DRIVE_V3_BASE_URL = 'https://www.googleapis.com/drive/v3'


class DriveV3:
    def __init__(self, credentials: Credentials):
        session = gen_auth_session(credentials)
        self.__files = Files(session)
        self.__drives = Drives(session)
        self.__permissions = Permissions(session)

    @property
    def files(self):
        return self.__files

    @property
    def drives(self):
        return self.__drives

    @property
    def permissions(self):
        return self.__permissions
