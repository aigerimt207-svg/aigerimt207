"""Виджеты интерфейса FastBid: светофоры, таймеры, карточки лотов, лог.

Все виджеты обновляются строго из UI-потока Tkinter. Фоновая asyncio-логика
общается с UI только через очереди: ``UILogSink.drain()`` и события
``EventBus`` → ``FastBidApp`` → ``widget.configure(...)`` через ``after()``.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Any, ClassVar

import customtkinter as ctk

__all__ = [
    "CountdownTimer",
    "LogConsole",
    "LotCard",
    "MetricPill",
    "PasswordDialog",
    "StageBar",
    "StatusLight",
    "UiEventQueue",
    "set_appearance",
]

# -- базовая палитра в стиле zakup.gov.kz (светлая, teal-акцент) ----------- #
PORTAL_ACCENT = "#0e7d63"  # teal-кнопки «Выбрать ЭЦП ключ» на портале
PORTAL_ACCENT_HOVER = "#0b6b55"
PORTAL_BG = "#eef3f6"
PORTAL_CARD = "#ffffff"
PORTAL_BORDER = "#d8e2e9"
PORTAL_TEXT = "#182c3a"
PORTAL_DIM = "#546877"

COLORS: dict[str, tuple[str, str]] = {
    "frame": (PORTAL_BG, "#12161b"),
    "card": (PORTAL_CARD, "#1d2129"),
    "ok": ("#16824a", "#43c76b"),
    "warn": ("#b07d0a", "#e8b93b"),
    "err": ("#cf3f36", "#e0574b"),
    "dim": (PORTAL_DIM, "#a5b4c5"),
    "badge_text": ("#ffffff", "#101b27"),
    "text": (PORTAL_TEXT, "#d8dee9"),
    "accent": (PORTAL_ACCENT, "#2fa572"),
    "accent_hover": (PORTAL_ACCENT_HOVER, "#287a5a"),
    "border": (PORTAL_BORDER, "#3a4150"),
}
FONT_MONO = ("Consolas", 11) if __import__("sys").platform == "win32" else ("Menlo", 11)


def set_appearance(
    appearance: str = "light", theme: str = "green", scaling: float = 1.0
) -> None:
    """Тема оформления приложения (вызывать до создания окна).

    По умолчанию — светлая тема в стиле zakup.gov.kz: зелёные акценты,
    белые карточки, тёмный текст.
    """
    ctk.set_appearance_mode(appearance)
    ctk.set_default_color_theme(theme)
    try:
        ctk.set_widget_scaling(max(0.5, min(2.0, scaling)))
    except Exception:
        pass


class UiEventQueue:
    """Очередь событий «ядро → UI» (потокобезопасная, FIFO)."""

    def __init__(self, maxsize: int = 5000) -> None:
        self.queue: queue.Queue[tuple[str, dict[str, Any]]] = queue.Queue(maxsize)
        self._lock = threading.Lock()
        self._seen: dict[str, int] = {}

    def put(self, event: str, **payload: Any) -> None:
        try:
            self.queue.put_nowait((event, payload))
        except queue.Full:
            pass

    def drain(self, max_items: int = 200) -> list[tuple[str, dict[str, Any]]]:
        out: list[tuple[str, dict[str, Any]]] = []
        for _ in range(max_items):
            try:
                out.append(self.queue.get_nowait())
            except queue.Empty:
                break
        return out


class StatusLight(ctk.CTkFrame):
    """Светофор соединения: цветной кружок + подпись + опциональный бейдж."""

    def __init__(self, master: Any, title: str = "", **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._color: tuple[str, str] | str = COLORS["dim"]
        self._dot = ctk.CTkFrame(
            self, width=10, height=10, corner_radius=5, fg_color=self._color
        )
        self._dot.grid(row=0, column=0, padx=(0, 8))
        texts = ctk.CTkFrame(self, fg_color="transparent")
        texts.grid(row=0, column=1, sticky="w")
        self._title = ctk.CTkLabel(
            texts, text=title, font=ctk.CTkFont(size=11), text_color=COLORS["dim"]
        )
        self._title.pack(anchor="w")
        self._value = ctk.CTkLabel(
            texts, text="—", font=ctk.CTkFont(size=12, weight="bold")
        )
        self._value.pack(anchor="w")
        self._blink_after: str | None = None

    def _resolve_bg(self) -> str:
        try:
            mode = ctk.get_appearance_mode()
        except Exception:
            mode = "Light"
        return "#242424" if mode == "Dark" else PORTAL_CARD

    def set(
        self,
        text: str,
        color: tuple[str, str] | str = "#7a8290",
        detail: str | None = None,
    ) -> None:
        """Установить состояние (вызывать из UI-потока)."""
        self._color = color
        self._dot.configure(fg_color=color)
        self._value.configure(text=text)
        if detail is not None:
            self._title.configure(text=detail)

    def activity(self) -> None:
        """Короткая вспышка — визуальный отклик на сетевую активность."""
        self._dot.configure(fg_color=COLORS["accent"])
        if self._blink_after:
            self.after_cancel(self._blink_after)
        self._blink_after = self.after(120, self._restore)

    def _restore(self) -> None:
        self._blink_after = None
        self._dot.configure(fg_color=self._color)


class MetricPill(ctk.CTkFrame):
    """Компактный показатель: «ПОДПИСЬ 431 мс»."""

    def __init__(self, master: Any, label: str, **kwargs: Any) -> None:
        super().__init__(
            master,
            fg_color=COLORS["card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )
        ctk.CTkLabel(
            self,
            text=label.upper(),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["dim"],
        ).pack(anchor="w", padx=16, pady=(12, 0))
        self._value = ctk.CTkLabel(
            self,
            text="—",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text"],
            wraplength=250,
            justify="left",
        )
        self._value.pack(anchor="w", padx=16, pady=(0, 12))

    def set(self, text: str) -> None:
        self._value.configure(text=text)


class CountdownTimer(ctk.CTkFrame):
    """Таймер обратного отсчёта с миллисекундной точностью."""

    def __init__(self, master: Any, caption: str = "до T0", **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(
            self,
            text=caption,
            font=ctk.CTkFont(size=10),
            text_color=COLORS["dim"],
        ).pack(anchor="w")
        self._label = ctk.CTkLabel(
            self,
            text="--:--:--.---",
            font=("Consolas", 26, "bold"),
        )
        self._label.pack(anchor="w")
        self._after: str | None = None

    @staticmethod
    def format_ms(seconds: float) -> str:
        """Форматирует секунды как HH:MM:SS.mmm (отрицательные — с минусом)."""
        sign = "-" if seconds < 0 else ""
        total = abs(seconds)
        hours, rest = divmod(int(total), 3600)
        minutes, secs = divmod(rest, 60)
        millis = int((total - int(total)) * 1000)
        return f"{sign}{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def set(self, seconds: float) -> None:
        self._label.configure(text=self.format_ms(seconds))

    def bind_live(
        self, source: Callable[[], float | None], interval_ms: int = 100
    ) -> None:
        """Живое обновление из функции-источника (вызывается из UI-потока)."""
        self.unbind_live()

        def tick() -> None:
            value = source()
            if value is None:
                self.set(0.0)
            else:
                self.set(value)
            self._after = self.after(interval_ms, tick)

        tick()

    def unbind_live(self) -> None:
        if self._after:
            with __import__("contextlib").suppress(Exception):
                self.after_cancel(self._after)
            self._after = None


class StageBar(ctk.CTkFrame):
    """Горизонтальная шкала этапов конвейера с миллисекундами."""

    _ORDER: ClassVar[tuple[str, ...]] = (
        "plan",
        "sign",
        "upload",
        "wait",
        "submit",
        "verify",
    )
    _TITLES: ClassVar[dict[str, str]] = {
        "plan": "План",
        "sign": "Подпись",
        "upload": "Загрузка",
        "wait": "Ожидание",
        "submit": "Submit",
        "verify": "Проверка",
    }

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._labels: dict[str, Any] = {}
        for index, stage in enumerate(self._ORDER):
            frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=6)
            frame.grid(row=0, column=index, padx=2, sticky="ew")
            self.grid_columnconfigure(index, weight=1)
            ctk.CTkLabel(
                frame,
                text=self._TITLES[stage],
                font=ctk.CTkFont(size=10),
                text_color=COLORS["dim"],
            ).pack(padx=8, pady=(4, 0))
            value = ctk.CTkLabel(
                frame, text="—", font=ctk.CTkFont(size=11, weight="bold")
            )
            value.pack(padx=8, pady=(0, 4))
            self._labels[stage] = value

    def set(self, timings: dict[str, float]) -> None:
        for stage, widget in self._labels.items():
            value = timings.get(stage)
            widget.configure(
                text="—" if value is None else f"{value:,.0f} мс".replace(",", " ")
            )

    def reset(self) -> None:
        for widget in self._labels.values():
            widget.configure(text="—")


class LotCard(ctk.CTkFrame):
    """Карточка наблюдаемого лота: данные, T0, статус взвода, действия."""

    def __init__(
        self,
        master: Any,
        lot_id: int,
        lot_number: str = "",
        on_arm: Callable[[int], None] | None = None,
        on_disarm: Callable[[int], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["card"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )
        self.lot_id = lot_id
        self._on_arm = on_arm
        self._on_disarm = on_disarm

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 0))
        self._title = ctk.CTkLabel(
            header,
            text=f"Лот {lot_number or lot_id}",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self._title.pack(side="left", expand=True, fill="x")
        self._pill = ctk.CTkLabel(
            header,
            text="готова к взводу",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["badge_text"],
            fg_color=COLORS["dim"],
            corner_radius=8,
            padx=8,
            pady=2,
        )
        self._pill.pack(side="right")

        self._meta = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["dim"],
            anchor="w",
            wraplength=420,
            justify="left",
        )
        self._meta.pack(fill="x", padx=10)

        self._countdown = CountdownTimer(self, caption="до открытия окна")
        self._countdown.pack(anchor="w", padx=10, pady=(2, 0))

        self._stages = StageBar(self)
        self._stages.pack(fill="x", padx=10, pady=(4, 0))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(4, 8))
        self._arm_button = ctk.CTkButton(
            row,
            text="Взвести заявку",
            width=160,
            command=self._emit_arm,
            fg_color=COLORS["ok"],
        )
        self._arm_button.pack(side="left")
        self._disarm_button = ctk.CTkButton(
            row,
            text="Снять",
            width=100,
            state="disabled",
            command=self._emit_disarm,
            fg_color=COLORS["err"],
        )
        self._disarm_button.pack(side="left", padx=(8, 0))
        self._status_line = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["dim"],
            anchor="w",
            justify="left",
            wraplength=800,
        )
        self._status_line.pack(fill="x", padx=12, pady=(0, 10))

    def _emit_arm(self) -> None:
        if self._on_arm is not None:
            self._on_arm(self.lot_id)

    def _emit_disarm(self) -> None:
        if self._on_disarm is not None:
            self._on_disarm(self.lot_id)

    # -- обновление (только из UI-потока) ----------------------------------- #
    def set_meta(
        self, name: str, amount: float, status: str, start_date: str = ""
    ) -> None:
        self._title.configure(text=f"Лот {self.lot_id} — {name[:48]}")
        text = f"{amount:,.2f} KZT · {status} · начало: {start_date or '—'}"
        self._meta.configure(text=text.replace(",", " "))

    def set_pill(self, text: str, color: tuple[str, str] | str) -> None:
        self._pill.configure(text=text, fg_color=color)

    def set_status(self, text: str) -> None:
        self._status_line.configure(text=text)

    def set_armed(self, armed: bool) -> None:
        self._arm_button.configure(state="disabled" if armed else "normal")
        self._disarm_button.configure(state="normal" if armed else "disabled")
        if armed:
            self._stages.reset()
        self.set_pill(
            "взведена" if armed else "готова к взводу",
            COLORS["ok"] if armed else COLORS["dim"],
        )

    def set_timings(self, timings: dict[str, float]) -> None:
        values = dict(timings)
        for name in ("plan", "wait"):
            if f"cycle_{name}" in values:
                values[name] = values[f"cycle_{name}"]
        self._stages.set(values)

    @property
    def countdown(self) -> CountdownTimer:
        return self._countdown


class LogConsole(ctk.CTkFrame):
    """Консоль логов с фильтром уровней и автопрокруткой."""

    _ORDER: ClassVar[dict[str, int]] = {
        "DEBUG": 10,
        "INFO": 20,
        "SUCCESS": 25,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    def __init__(self, master: Any, max_rows: int = 2000, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(toolbar, text="Фильтр:", font=ctk.CTkFont(size=11)).pack(
            side="left"
        )
        self._level = ctk.CTkOptionMenu(
            toolbar,
            width=130,
            values=["DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR"],
            command=self._on_filter,
        )
        self._level.set("INFO")
        self._level.pack(side="left", padx=(6, 0))
        self._autoscroll = ctk.CTkCheckBox(toolbar, text="Автопрокрутка")
        self._autoscroll.select()
        self._autoscroll.pack(side="left", padx=(10, 0))
        ctk.CTkButton(toolbar, text="Очистить", width=100, command=self.clear).pack(
            side="right"
        )
        self._box = ctk.CTkTextbox(
            self,
            font=FONT_MONO,
            wrap="none",
            activate_scrollbars=True,
        )
        self._box.pack(fill="both", expand=True)
        self._refresh_colors()
        self._box.configure(state="disabled")
        self._min_level = 20
        self._max_rows = max_rows
        self._rows = 0

    def _refresh_colors(self) -> None:
        index = 1 if ctk.get_appearance_mode() == "Dark" else 0
        for level, token in {
            "DEBUG": "dim",
            "INFO": "text",
            "SUCCESS": "ok",
            "WARNING": "warn",
            "ERROR": "err",
            "CRITICAL": "err",
        }.items():
            self._box.tag_config(level, foreground=COLORS[token][index])

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        if hasattr(self, "_box"):
            self._refresh_colors()

    def _on_filter(self, value: str) -> None:
        self._min_level = self._ORDER.get(value, 20)

    def append_record(self, text: str, level: str) -> None:
        if self._ORDER.get(level, 20) < self._min_level:
            return
        self._box.configure(state="normal")
        self._box.insert("end", text + "\n", level)
        self._rows += text.count("\n") + 1
        if self._rows > self._max_rows:
            self._box.delete("1.0", f"{self._rows - self._max_rows + 1}.0")
            self._rows = self._max_rows
        if self._autoscroll.get():
            self._box.see("end")
        self._box.configure(state="disabled")

    def clear(self) -> None:
        self._box.configure(state="normal")
        self._box.delete("1.0", "end")
        self._box.configure(state="disabled")
        self._rows = 0


class CredentialDialog(ctk.CTkToplevel):
    """Модальное окно входа: пароль ЭЦП или токен/cookie из браузера.

    Всё, что пользователь вводит, живёт только в RAM вызывающего кода.
    """

    def __init__(self, master: Any, mode: str = "ecp") -> None:
        super().__init__(master)
        self.mode = mode
        self.title("Разблокировка ЭЦП" if mode == "ecp" else "Вход по токену")
        self.resizable(False, False)
        self._value: str | None = None

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(padx=22, pady=16)

        if mode == "ecp":
            ctk.CTkLabel(
                body,
                text="Введите пароль от контейнера ЭЦП.\n"
                "Он хранится только в памяти до конца сессии.",
                font=ctk.CTkFont(size=12),
                justify="left",
            ).pack(anchor="w", pady=(0, 8))
            self._entry = ctk.CTkEntry(body, width=360, show="*")
            self._entry.pack(fill="x")
        else:
            ctk.CTkLabel(
                body,
                text="Вход по токену/cookie из браузера.\n\n"
                "1. Откройте кабинет закупок в браузере и войдите (ЭЦП/QR).\n"
                "2. F12 → Сеть (Network) → обновите страницу.\n"
                "3. Кликните любой запрос к v3bl.goszakup.gov.kz\n"
                "    или zakup.gov.kz → заголовки запроса.\n"
                "4. Скопируйте заголовок Authorization (целиком, с 'Bearer'),\n"
                "    либо Cookie (например, SESSION=...), либо только токен.\n"
                "5. Вставьте сюда. Данные хранятся только в памяти.",
                font=ctk.CTkFont(size=12),
                justify="left",
            ).pack(anchor="w", pady=(0, 8))
            self._entry = ctk.CTkEntry(body, width=520, show="*")
            self._entry.pack(fill="x")

        self._entry.bind("<Return>", lambda _event: self._confirm())
        self._entry.bind("<Escape>", lambda _event: self._cancel())
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", pady=(12, 0))
        ctk.CTkButton(
            row, text="Отмена", width=120, command=self._cancel, fg_color=COLORS["dim"]
        ).pack(side="right")
        ctk.CTkButton(
            row, text="ОК", width=120, command=self._confirm, fg_color=COLORS["ok"]
        ).pack(
            side="right",
            padx=(0, 8),
        )
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.transient(master)
        self.grab_set()
        self._entry.focus_set()

    def _confirm(self) -> None:
        self._value = self._entry.get()
        self._entry.delete(0, "end")
        self.grab_release()
        self.destroy()

    def _cancel(self) -> None:
        self._value = None
        self._entry.delete(0, "end")
        self.grab_release()
        self.destroy()

    @property
    def value(self) -> str | None:
        return self._value

    def wait_value(self) -> str | None:
        """Блокирует UI-поток до закрытия диалога."""
        self.wait_window()
        return self._value


# Историческое имя оставлено для совместимости
PasswordDialog = CredentialDialog
