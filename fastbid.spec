# -*- mode: python ; coding: utf-8 -*-
"""Спека сборки FastBid.exe (PyInstaller).

Сборка::

    pyinstaller fastbid.spec --noconfirm

Результат: dist\\FastBid.exe — автономный GUI-исполняемый файл
(Windows 10/11 x64). Для отладки соберите консольный вариант
(переменная окружения читается спекой при сборке)::

    set FASTBID_CONSOLE=1
    pyinstaller fastbid.spec --noconfirm
"""

import os

from PyInstaller.utils.hooks import collect_all

console = os.environ.get("FASTBID_CONSOLE", "0") == "1"

datas = []
binaries = []
hiddenimports = []

# Пакеты с файлами данных: темы CustomTkinter, базы часовых поясов (Asia/Almaty),
# хуки websockets и HTTP/2-стек (h2/hpack/hyperframe — чистый Python, но их
# нужно объявить, т.к. httpx импортирует их динамически).
for package in (
    "customtkinter",
    "tzdata",
    "h2",
    "hpack",
    "hyperframe",
    "websockets",
):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

hiddenimports += [
    "websockets.asyncio.client",
    "websockets.asyncio.server",
    "websockets.legacy",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter.test", "unittest", "pydoc_data"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FastBid",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=console,          # GUI-режим: без консольного окна
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
