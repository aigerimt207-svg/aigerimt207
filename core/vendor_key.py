"""Публичный ключ вендора, вшитый в сборку.

ЕДИНСТВЕННЫЙ доверенный источник ключа проверки лицензий. Env-подмены
(``FASTBID_LICENSE_PUBKEY``) и файл ``license_public_key.pem`` рядом с
данными убраны намеренно: репозиторий публичный, и без вшитого ключа
любой мог выпустить себе лицензию своим ключом.

Приватный ключ пары хранится у вендора (ВНЕ репозитория и поставки).
Смена ключа вендора = правка этого файла + новая сборка.
"""

from __future__ import annotations

VENDOR_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAzvBRuCuops5vu8V8EIvAVG1ZtofISvC8S7saTwO6ZRw=
-----END PUBLIC KEY-----
"""
