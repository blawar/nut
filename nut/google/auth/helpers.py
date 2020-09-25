#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
from pathlib import Path
from typing import NoReturn
from typing import Sequence
from typing import Optional
from requests import request
from google.auth.credentials import Credentials
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as SACredentials


def load_app_creds(
    creds_path: Path,
) -> dict:
    with creds_path.open(mode='r', encoding='utf8') as credentials_stream:
        return json.load(credentials_stream)


def load_user_token(
    ut_path: Path,
) -> Optional[UserCredentials]:
    with ut_path.open(mode='r', encoding='utf8') as token_stream:
        user_token = json.load(token_stream)
        user_creds = UserCredentials.from_authorized_user_info(user_token)

        try:
            user_creds.refresh(Request())
        except RefreshError:
            logging.exception(
                'RefreshError occurred while refreshing user token. Most ' +
                'likely the user\'s refresh token is no longer valid!'
            )
            return None

        return user_creds


def load_service_account(
    sa_path: Path,
) -> Optional[SACredentials]:
    with sa_path.open(mode='r', encoding='utf8') as sa_stream:
        sa_info = json.load(sa_stream)
        return SACredentials.from_service_account_info(sa_info)


def save_user_token(
    user_creds: UserCredentials,
    user_token_path: Path
) -> NoReturn:
    with user_token_path.open(mode='w', encoding='utf8') as \
            token_stream:
        json.dump(json.loads(user_creds.to_json()), token_stream)


def revoke_token(
    token: str
) -> bool:
    response = request(
        'POST',
        'https://oauth2.googleapis.com/revoke',
        params={
            'token': token,
        },
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    )
    return response.status_code == 200


def auth_new_user(
    app_creds: dict,
    scopes: Sequence[str],
    headless: bool = False
) -> Optional[UserCredentials]:
    flow = InstalledAppFlow.from_client_config(app_creds, scopes)

    try:
        return flow.run_console() if headless else flow.run_local_server(
            port=0,
        )
    except InvalidGrantError:
        logging.exception('InvalidGrantError occurred while generating ' +
                          'user token. Most likely due to bad auth user code!')
        return None


def gen_auth_session(creds: Credentials) -> AuthorizedSession:
    return AuthorizedSession(creds)
