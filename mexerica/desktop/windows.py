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
  5. Ícone na área de notificação (perto do relógio) enquanto o serviço
     roda: clique abre as Configurações, o botão direito abre o menu.
"""
from __future__ import annotations

import logging
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

from .. import APP_ID, settings  # noqa: E402
from ..editors.base import TITLE_PREFIX  # noqa: E402
from . import drag as D  # noqa: E402
from . import win32 as W  # noqa: E402
from .toast import Toast  # noqa: E402

log = logging.getLogger("mexerica")

DRAG_THRESHOLD = 8         # px que o ponteiro anda até virar arraste (o do GTK)
TOAST_MARGIN = 16          # px físicos, da borda da área útil
TOAST_GAP = 10
ICON = Path(__file__).resolve().parents[1] / "data" / "icon.ico"
STARTUP_LINK = "Mexerica (serviço).lnk"     # criado pelo install.ps1


def _startup() -> tuple[Path, Path]:
    """Atalho do serviço na pasta Inicializar e onde ele fica desligado (o
    install.ps1 respeita: se estiver desligado, continua desligado)."""
    roaming = os.environ.get("APPDATA") or str(Path.home() / "AppData/Roaming")
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData/Local")
    folder = W.startup_folder() or Path(roaming, "Microsoft", "Windows",
                                        "Start Menu", "Programs", "Startup")
    return folder / STARTUP_LINK, Path(local, "Mexerica", "autostart-off.lnk")


def _app_alias(name: str) -> str | None:
    """Apps da Microsoft Store (wt, winget) são aliases em WindowsApps,
    pasta que nem sempre está no PATH."""
    alias = Path(os.environ.get("LOCALAPPDATA", ""), "Microsoft",
                 "WindowsApps", f"{name}.exe")
    return shutil.which(name) or (str(alias) if alias.exists() else None)


class WindowsDesktop:
    name = "Windows"

    def __init__(self, app):
        self.app = app
        self.watch = D.DragWatch()
        self._polling = False
        self._anchor: tuple[int, int] | None = None
        self._monitor: W.Rect | None = None
        self._toasts: dict[str, Toast] = {}
        self.tray: W.Tray | None = None
        W.load_gdk_win32()

    @property
    def overlay_dim(self) -> float:
        """Sem a extensão, a própria roda escurece a tela atrás dela."""
        return settings.get()["dim"] / 100

    def start(self) -> None:
        if not W.claim_instance(APP_ID):
            # o GApplication não achou a outra instância (sem o barramento
            # D-Bus do GLib); duas abririam duas rodas a cada arraste. Pede
            # à outra que abra o que este abriria (Início, com os arquivos
            # do menu de contexto) e sai.
            tray = W.FindWindowExW(None, None, W.TRAY_CLASS, None)
            files = [str(Path(f).resolve()) for f in self.app.argv_files
                     if Path(f).exists()]
            if tray and not (files and W.send_files(tray, files)):
                W.PostMessageW(tray, W.Tray.OPEN, 0, 0)
            log.warning("outro serviço da Mexerica já está rodando; saindo")
            os._exit(0)
        self.app.connect("window-added", self._on_window_added)
        self._polling = True
        GLib.timeout_add(D.IDLE_POLL_MS, self._tick)
        self._start_tray()
        log.info("detecção de arraste do Windows ativa")

    def stop(self) -> None:
        if self.tray is not None:
            self.tray.remove()
            self.tray = None

    def _start_tray(self) -> None:
        # chamadas a partir da janela da bandeja: o GTK roda depois, no laço
        def later(action):
            return lambda: GLib.idle_add(lambda: (action(), False)[1])
        try:
            self.tray = W.Tray(
                ICON, "Mexerica: arraste um arquivo e segure Shift",
                on_open=later(self.app.show_home),
                on_files=lambda paths: GLib.idle_add(
                    lambda: (self.app.show_home(paths, merge=True), False)[1]),
                menu=[("Abrir a Mexerica", later(self.app.show_home)),
                      ("Configurações…",
                       later(lambda: self.app.show_settings("look"))),
                      ("Abrir o log", later(lambda: self.app.activate_action(
                          "open-log", None))),
                      None,
                      ("Sair da Mexerica", later(self.app.quit))],
                on_close=later(self.app.quit))
        except Exception:  # noqa: BLE001 - sem bandeja o resto funciona
            log.exception("ícone da bandeja indisponível")

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
        image = down and not self.watch.dragging and bool(W.drag_image())
        mode = D.mode_for(*W.modifiers()) if down else None
        now = time.monotonic() * 1000
        act = self.watch.step(down, image, mode, W.pointer(), now)
        if act is None and self.watch.shown:
            ov = self.app.overlay
            act = self.watch.probe(bool(ov and ov.paths), now)
            if act:
                log.info("arraste sem arquivos para a roda; desistindo")
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

    def drag_source(self, widget, paths: list[Path], done) -> None:
        """Arrastar `widget` leva os arquivos (janela Flutuar), pelo arraste
        nativo do shell. O do GTK no Windows deixava o ícone dele na tela e
        não trazia janelas pela barra de tarefas. O Windows conduz o arraste
        até o drop; nesse meio tempo o serviço fica parado (a roda não abre
        num arraste que começa na Flutuar)."""
        gesture = Gtk.GestureDrag()
        busy = []

        def update(g, dx, dy):
            if busy or math.hypot(dx, dy) < DRAG_THRESHOLD:
                return
            busy.append(True)
            g.set_state(Gtk.EventSequenceState.CLAIMED)
            try:
                W.drag_files(W.hwnd_of(widget.get_root()), paths)
            except OSError:
                log.exception("arraste da Flutuar falhou")
            g.reset()
            GLib.idle_add(lambda: (done(), False)[1])
        gesture.connect("drag-update", update)
        widget.add_controller(gesture)

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
        if win.has_css_class("mx-float"):
            # a bolha nasce sob o ponteiro (onde o arquivo foi solto)
            W.plain_frame(hwnd)
            left, top, right, bottom = W.window_rect(hwnd)
            x, y = W.pointer()
            area = W.monitor_at((x, y))[1]
            w, h = right - left, bottom - top
            W.move(hwnd, min(max(x - w // 2, area[0]), area[2] - w),
                   min(max(y - h // 3, area[1]), area[3] - h))
        W.bring_to_front(hwnd)

    # -- arquivos como o Explorer mostra --------------------------------------
    def file_icon(self, path: Path, size: int):
        """Miniatura ou ícone do Explorer (de atalho e .exe, o do programa)."""
        img = W.shell_image(path, size * 2)          # nítido em tela HiDPI
        if img is None:
            return None
        w, h, data = img
        # o shell entrega alfa direto (não pré-multiplicado)
        return Gdk.MemoryTexture.new(w, h, Gdk.MemoryFormat.B8G8R8A8,
                                     GLib.Bytes.new(data), w * 4)

    def display_name(self, path: Path) -> str:
        return W.display_name(path)

    # -- iniciar com o sistema -------------------------------------------------
    def autostart(self) -> bool | None:
        """None: sem o atalho do instalador (não dá para ligar daqui)."""
        on, off = _startup()
        return True if on.exists() else False if off.exists() else None

    def set_autostart(self, enabled: bool) -> None:
        on, off = _startup()
        src, dst = (off, on) if enabled else (on, off)
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

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
        wt = _app_alias("wt")                        # Windows Terminal
        if term and shutil.which(term):
            subprocess.Popen([term], cwd=d)
        elif wt:
            subprocess.Popen([wt, "-d", "."], cwd=d)
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
