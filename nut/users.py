#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from nut import printer
from pathlib import Path
from typing import NoReturn

users_path = Path('conf/users.conf')
users = {}


class User:
    __username = None
    __password = None

    def __init__(self, username: str, password: str):
        self.__username = username
        self.__password = password

    @property
    def username(self) -> str:
        return self.__username

    @property
    def password(self):
        return self.__password


def first() -> User:
    for user in users.values():
        return user


def auth(username: str, password: str) -> bool:
    if username not in users:
        return False

    return users[username].password == password


def save() -> NoReturn:
    users_to_save = {}

    for username, user in users.items():
        users_to_save.update({
            username: {
                "password": user.password,
            }
        })

    users_path.parent.mkdir(exist_ok=True, parents=True)

    with users_path.open(mode='w', encoding='utf8') as users_stream:
        json.dump(users_to_save, users_stream)


def load() -> NoReturn:
    global users

    if users_path.is_file():
        with users_path.open(mode='r', encoding='utf8') as users_stream:
            try:
                for username, user in json.load(users_stream).items():
                    user = User(username, user['password'])
                    users[username] = user
                    printer.info(f'loaded user {username}')

            except json.JSONDecodeError:
                # Try loading old version
                users_stream.seek(0)
                first_line = True
                for line in users_stream.readlines():
                    if first_line:
                        first_line = False
                        continue

                    line = line.strip()

                    if len(line) == 0 or line[0] == '#':
                        continue

                    try:
                        username, password = line.split('|')
                    except ValueError:
                        continue

                    user = User(username, password)
                    users[username] = user
                    printer.info(f'loaded user {username}')
                save()

    if len(users) == 0:
        username = 'guest'
        users[username] = User(username, username)
        save()


load()
