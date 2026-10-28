"""Backend do Windows: o próprio serviço faz o papel da extensão do GNOME.

  1. A cada 30 ms (como a extensão) lê o botão do mouse e procura a
     imagem de arraste do shell: as duas juntas = arraste do Explorer em
     andamento. Shift, Shift+Alt e Shift+Ctrl escolhem a roda (drag.py).
  2. A janela da roda cobre o monitor do ponteiro, acima de tudo. O
     arraste do OLE passa a apontar para ela e o GtkDropTarget recebe o
     hover, os arquivos e o drop, como no GNOME. Se o arraste não trouxer
     arquivos (texto, link), a roda some.
  3. As janelas do serviço vêm para a frente, a Flutuar e os editores
     ficam acima das outras, e o DWM borra o fundo delas (o vidro).
  4. Clipboard, "mostrar na pasta", abrir e terminal pela API do Windows;
     notificações viram toasts (toast.py).
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from .. import APP_ID  # noqa: E402
from ..editors.base import TITLE_PREFIX  # noqa: E402
from . import drag as D  # noqa: E402
from . import win32 as W  # noqa: E402
from .toast import Toast  # noqa: E402

log = logging.getLogger("mexerica")

OVERLAY_DIM = 0.28         # a tela atrás da roda (brilho 0,72 no GNOME)
TOAST_MARGIN = 16          # px físicos, da borda da área útil
TOAST_GAP = 10


class WindowsDesktop:
    name = "Windows"
    overlay_dim = OVERLAY_DIM   # sem a extensão, a própria roda escurece

    def __init__(self, app):
        self.app = app
        self.watch = D.DragWatch()
        self._polling = False
        self._anchor: tuple[int, int] | None = None
        self._monitor: W.Rect | None = None
        self._toasts: dict[str, Toast] = {}
        W.load_gdk_win32()

    def start(self) -> None:
        if not W.claim_instance(APP_ID):
            # o GApplication não achou a outra instância (sem o barramento
            # D-Bus do GLib); duas abririam duas rodas a cada arraste
            log.warning("outro serviço da Mexerica já está rodando; saindo")
            os._exit(0)
        self.app.connect("window-added", self._on_window_added)
        self._polling = True
        GLib.timeout_add(D.IDLE_POLL_MS, self._tick)
        log.info("detecção de arraste do Windows ativa")

    # -- arraste -------------------------------------------------------------
    def _tick(self):
        busy = False
        try:
            busy = self._poll()
        except Exception:  # noqa: BLE001 - o laço não pode parar
            log.exception("falha ao ler mouse e teclado")
        GLib.timeout_add(D.POLL_MS if busy else D.IDLE_POLL_MS, self._tick)
        return GLib.SOURCE_REMOVE

    def _poll(self) -> bool:
        down = W.primary_button_down()
        dragging = down and bool(W.drag_image())
        mode = D.mode_for(*W.modifiers()) if dragging else None
        now = time.monotonic() * 1000
        act = self.watch.step(dragging, mode, W.pointer(), now)
        if act is None and self.watch.shown:
            ov = self.app.overlay
            act = self.watch.probe(bool(ov and ov.paths), now)
        if act and act[0] == D.SHOW:
            self._anchor = act[2]
            self.app.show_wheel(act[1], [])
        elif act:
            self._anchor = None
            self.app.hide_wheel()
        return down or bool(self.watch.shown)

    # -- roda ----------------------------------------------------------------
    def show_overlay(self, win) -> None:
        self._monitor = W.monitor_at(self._anchor or W.pointer())[0]
        hwnd = W.hwnd_of(win)
        W.add_ex_style(hwnd, W.WS_EX_TOOLWINDOW, W.WS_EX_APPWINDOW)
        win.present()
        # o GTK ajusta o "acima de tudo" ao mostrar; o nosso vem depois
        W.place(hwnd, self._monitor)
        drag = W.drag_image()
        if drag:
            W.place_below(hwnd, drag)    # a miniatura do arraste fica visível
        W.set_glass(hwnd, rounded=False)

    def wheel_center(self, win, w: float, h: float):
        """Ponteiro em coordenadas da janela: a janela cobre o monitor, então
        a proporção converte pixels físicos para os do GTK (qualquer escala)."""
        if not self._monitor:
            return None
        left, top, right, bottom = self._monitor
        x, y = self._anchor or W.pointer()
        return ((x - left) * w / max(right - left, 1),
                (y - top) * h / max(bottom - top, 1))

    def dialog_parent(self):
        """Dono dos diálogos nativos (Copiar para…). Sem uma janela nossa na
        frente, o Windows abre o diálogo atrás do Explorer."""
        win = Gtk.Window(application=self.app, title="Mexerica",
                         decorated=False, default_width=1, default_height=1)
        win.add_css_class("mexerica-overlay")        # transparente
        win.present()
        hwnd = W.hwnd_of(win)
        W.add_ex_style(hwnd, W.WS_EX_TOOLWINDOW, W.WS_EX_APPWINDOW)
        W.bring_to_front(hwnd)
        return win

    # -- janelas do serviço --------------------------------------------------
    def _on_window_added(self, _app, win) -> None:
        win.connect("map", self._pin)

    def _pin(self, win) -> None:
        """O que a extensão faz no GNOME: todas as janelas do serviço vêm
        para a frente, Flutuar e editores ficam acima das outras e as de
        vidro ganham o fundo borrado."""
        if win.has_css_class("mexerica-overlay") or isinstance(win, Toast):
            return
        hwnd = W.hwnd_of(win)
        if not hwnd:
            return
        if (win.get_title() or "").startswith(TITLE_PREFIX):
            W.set_topmost(hwnd)
        if win.has_css_class("mx-window"):
            W.set_glass(hwnd, rounded=True)
        W.bring_to_front(hwnd)

    # -- sistema -------------------------------------------------------------
    def set_clipboard(self, text: str) -> None:
        if not W.set_clipboard(text):
            log.warning("clipboard ocupado por outro app")

    def reveal(self, uris) -> None:
        paths = [Path(p) for p in
                 (Gio.File.new_for_uri(u).get_path() for u in uris) if p]
        if not paths:
            return
        W.allow_foreground()
        if not W.reveal(paths):
            subprocess.Popen(f'explorer /select,"{paths[0]}"')

    def open_uri(self, uri: str) -> None:
        W.allow_foreground()
        os.startfile(Gio.File.new_for_uri(uri).get_path() or uri)

    def open_terminal(self, folder: Path) -> None:
        W.allow_foreground()
        d = str(folder)
        term = os.environ.get("TERMINAL")
        if term and shutil.which(term):
            subprocess.Popen([term], cwd=d)
        elif shutil.which("wt"):                     # Windows Terminal
            subprocess.Popen(["wt", "-d", "."], cwd=d)
        else:
            shell = shutil.which("pwsh") or shutil.which("powershell") \
                or "cmd.exe"
            subprocess.Popen([shell], cwd=d,
                             creationflags=subprocess.CREATE_NEW_CONSOLE)

    # -- notificações --------------------------------------------------------
    def notify(self, nid, title, body="", buttons=None, default=None,
               progress=False) -> None:
        toast = self._toasts.get(nid)
        fresh = toast is None
        if fresh:
            toast = Toast(self.app)
            toast.connect("close-request", self._forget, nid)
            self._toasts[nid] = toast
        toast.update(title, body, buttons or [], default, sticky=progress)
        if fresh:
            hwnd = W.hwnd_of(toast)
            W.add_ex_style(hwnd, W.WS_EX_TOOLWINDOW | W.WS_EX_NOACTIVATE,
                           W.WS_EX_APPWINDOW)
            toast.set_visible(True)       # sem present(): não rouba o foco
            W.set_topmost(hwnd)
            W.set_glass(hwnd, rounded=True)
        GLib.idle_add(self._stack)
        GLib.timeout_add(80, self._stack)  # o GTK pode mudar a altura depois

    def withdraw(self, nid) -> None:
        toast = self._toasts.get(nid)
        if toast is not None:
            toast.close()

    def _forget(self, toast, nid):
        if self._toasts.get(nid) is toast:
            del self._toasts[nid]
            GLib.idle_add(self._stack)
        return False

    def _stack(self):
        """Empilha os toasts no canto do monitor principal, o mais novo
        embaixo, como as notificações do Windows."""
        _left, _top, right, bottom = W.monitor_at((0, 0))[1]
        y = bottom - TOAST_MARGIN
        for toast in reversed(list(self._toasts.values())):
            hwnd = W.hwnd_of(toast)
            x0, y0, x1, y1 = W.window_rect(hwnd)
            y -= y1 - y0
            W.move(hwnd, right - TOAST_MARGIN - (x1 - x0), y)
            y -= TOAST_GAP
        return GLib.SOURCE_REMOVE

    def status(self) -> str:
        state = "ativa" if self._polling else "parada"
        return f"Detecção de arraste do Windows: <b>{state}</b>"
