"""Интерфейс FastBid GosZakup (CustomTkinter)."""

from __future__ import annotations

from .app import AsyncBridge, Backend, FastBidApp
from .components import (
    COLORS,
    CountdownTimer,
    LogConsole,
    LotCard,
    MetricPill,
    PasswordDialog,
    StageBar,
    StatusLight,
    UiEventQueue,
    set_appearance,
)

__all__ = [
    "COLORS",
    "AsyncBridge",
    "Backend",
    "CountdownTimer",
    "FastBidApp",
    "LogConsole",
    "LotCard",
    "MetricPill",
    "PasswordDialog",
    "StageBar",
    "StatusLight",
    "UiEventQueue",
    "set_appearance",
]
