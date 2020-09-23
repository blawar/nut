#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from hashlib import sha256


def path_to_hash(file_path: Path) -> str:
    hash_ctx = sha256()
    hash_ctx.update(str(file_path.resolve()).encode('utf8'))
    return hash_ctx.digest().hex()
