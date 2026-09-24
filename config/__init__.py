"""Пакет конфигурации FastBid GosZakup."""

from __future__ import annotations

from .niche_blueprints import (
    BLUEPRINTS,
    NicheBlueprint,
    get_blueprint,
    resolve_blueprint,
)
from .settings import APP_NAME, APP_VERSION, AppSettings, load_settings

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "BLUEPRINTS",
    "AppSettings",
    "NicheBlueprint",
    "get_blueprint",
    "load_settings",
    "resolve_blueprint",
]
