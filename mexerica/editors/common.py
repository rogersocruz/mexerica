"""Utilidades das janelas: threads de prévia, texturas e formatação."""
from __future__ import annotations

import logging
import subprocess
import threading

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib  # noqa: E402

from ..engine import tools as T  # noqa: E402

log = logging.getLogger("mexerica")


def bg(fn, done) -> None:
    """Roda `fn()` numa thread e entrega o resultado (ou a exceção) a
    `done` no laço principal."""
    def worker():
        try:
            res = fn()
        except Exception as exc:  # noqa: BLE001 - mostrado na janela
            log.warning("tarefa de prévia falhou: %s", exc)
            res = exc
        GLib.idle_add(lambda: (done(res), False)[1])
    threading.Thread(target=worker, daemon=True).start()


class Latest:
    """Prévia sob demanda: no máximo um trabalho por vez e, enquanto ele
    roda, só o pedido mais recente fica na fila. Arrastar um controle
    deslizante não empilha dezenas de processos."""

    def __init__(self, delay_ms: int = 40):
        self._delay = delay_ms
        self._src = 0
        self._busy = False
        self._pending = None

    def request(self, fn, done) -> None:
        self._pending = (fn, done)
        if not self._busy and not self._src:
            self._src = GLib.timeout_add(self._delay, self._fire)

    def cancel(self) -> None:
        self._pending = None
        if self._src:
            GLib.source_remove(self._src)
            self._src = 0

    def _fire(self):
        self._src = 0
        if self._busy or not self._pending:
            return GLib.SOURCE_REMOVE
        fn, done = self._pending
        self._pending = None
        self._busy = True

        def finished(res):
            self._busy = False
            done(res)
            if self._pending and not self._src:
                self._src = GLib.timeout_add(self._delay, self._fire)
        bg(fn, finished)
        return GLib.SOURCE_REMOVE


def texture(png: bytes) -> Gdk.Texture:
    return Gdk.Texture.new_from_bytes(GLib.Bytes.new(png))


def run_out(argv: list[str]) -> bytes:
    proc = subprocess.run(argv, capture_output=True, stdin=subprocess.DEVNULL)
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode(errors="replace").strip().splitlines()
        raise RuntimeError(err[-1] if err else f"{argv[0]} falhou")
    return proc.stdout


def fmt_time(t: float) -> str:
    t = max(t, 0.0)
    m, s = divmod(t, 60)
    h, m = divmod(int(m), 60)
    return f"{h}:{m:02d}:{s:05.2f}" if h else f"{m}:{s:05.2f}"


def fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") \
                else f"{n:.1f} {unit}".replace(".", ",")
        n /= 1024
    return ""


def lossy(ext: str) -> bool:
    return ext in ("jpg", "jpeg", "webp", "avif", "heic", "heif", "jxl")


def image_formats() -> list[tuple[str, str | None]]:
    can = T.magick_writable()
    out: list[tuple[str, str | None]] = [("Original", None)]
    for label, ext, probe in (("JPG", "jpg", "jpeg"), ("PNG", "png", "png"),
                              ("WEBP", "webp", "webp"),
                              ("AVIF", "avif", "avif")):
        if probe in can:
            out.append((label, ext))
    return out
