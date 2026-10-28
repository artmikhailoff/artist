#!/usr/bin/env python3
"""Generate bcrypt hash for ADMIN_PASSWORD_HASH (never commit the plain password)."""
from __future__ import annotations

import getpass
import sys

import bcrypt


def main() -> None:
    password = sys.argv[1] if len(sys.argv) > 1 else getpass.getpass("Password: ")
    if not password:
        raise SystemExit("Empty password")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    print(hashed.decode("utf-8"))


if __name__ == "__main__":
    main()
