#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
from nut import Print

users = {}


class User:
    def __init__(self):
        self.id = None
        self.password = None
        self.isAdmin = False
        self.remoteAddr = None
        self.requireAuth = True
        self.switchHost = None
        self.switchPort = None
        pass

    def setId(self, id):
        self.id = id

    def getId(self):
        return str(self.id)

    def setPassword(self, password):
        self.password = password

    def getPassword(self):
        return self.password

    def setIsAdmin(self, isAdmin):
        try:
            self.isAdmin = False if int(isAdmin) == 0 else True
        except:
            pass

    def getIsAdmin(self):
        return str(self.isAdmin)

    def setRequireAuth(self, requireAuth):
        try:
            self.requireAuth = False if int(requireAuth) == 0 else True
        except:
            pass

    def getRequireAuth(self):
        return str(self.requireAuth)

    def setSwitchHost(self, host):
        self.switchHost = host

    def getSwitchHost(self):
        return self.switchHost

    def setSwitchPort(self, port):
        try:
            self.switchPort = int(port)
        except:
            pass

    def getSwitchPort(self):
        return self.switchPort


def first():
    global users
    for id, user in users.items():
        return user
    return None


def auth(id, password, address):
    if id not in users:
        return None

    user = users[id]

    if user.requireAuth == 0 and address == user.remoteAddr:
        return user

    if user.remoteAddr and user.remoteAddr != address:
        return None

    if user.password != password:
        return None

    return user


def load(path='conf/users.conf'):
    global users

    if not os.path.isfile(path):
        id = 'guest'
        users[id] = User()
        users[id].setPassword('guest')
        users[id].setId('guest')
        return

    firstLine = True
    map = ['id', 'password']
    with open(path, encoding="utf-8-sig") as f:
        for line in f.readlines():
            if firstLine:
                firstLine = False
                continue

            line = line.strip()

            if len(line) == 0 or line[0] == '#':
                continue

            if re.match(r'[A-Za-z\|\s]+', line, re.I):
                map = line.split('|')

            t = User()
            t.setPassword(map[1])
            t.setId(map[0])

            users[t.id] = t

            Print.info('loaded user ' + str(t.id))


load()
