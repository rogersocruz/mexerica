"""Backend do COSMIC (Pop!_OS 24.04+) — EXPERIMENTAL.

O COSMIC não aceita extensões, então o papel da extensão do GNOME fica com
o próprio serviço, como no Windows:

  1. Mouse e teclado vêm direto do kernel (evinput.py, precisa do grupo
     `input`): botão esquerdo pressionado + ponteiro andando = talvez um
     arraste; Shift, Shift+Alt e Shift+Ctrl escolhem a roda. A regra de
     abrir e fechar é a mesma da extensão e do Windows (drag.py).
  2. A roda é uma superfície de sobreposição do protocolo wlr-layer-shell
     (camada OVERLAY, a mesma usada pelo painel do COSMIC), cobrindo a
     tela, pela biblioteca gtk4-layer-shell.
  3. O kernel não sabe onde o ponteiro está na tela. A janela nasce
     invisível; quando o arraste passa a apontar para ela, o primeiro
     evento do GtkDropTarget dá a posição e a roda aparece ali.
  4. Se o arraste não trouxer arquivos (seleção de texto com Shift, por
     exemplo), a roda nunca aparece e some sozinha (DragWatch.probe).

Sem o grupo `input` ou sem o gtk4-layer-shell, o gesto não funciona, mas
`mexerica wheel ARQ...` (o "Abrir com > Mexerica (roda)") abre a roda no
centro da tela em qualquer caso.

O que ainda precisa ser validado numa sessão COSMIC real está no README
(seção COSMIC): se o cosmic-comp entrega o arraste para a superfície de
sobreposição e se o drop chega ao GTK.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib  # noqa: E402

from .. import settings  # noqa: E402
from ..engine import tools as T  # noqa: E402
from . import drag as D  # noqa: E402
from .evinput import InputReader, readable_devices  # noqa: E402
from .gnome import GnomeDesktop, _USER_AUTOSTART, _autostart_source  # noqa: E402

log = logging.getLogger("mexerica")


def layer_shell():
    """O módulo Gtk4LayerShell, ou None se a biblioteca não estiver
    instalada ou o compositor não suportar o protocolo."""
    try:
        gi.require_version("Gtk4LayerShell", "1.0")
        from gi.repository import Gtk4LayerShell as LS
    except (ImportError, ValueError):
        return None
    try:
        if hasattr(LS, "is_supported") and not LS.is_supported():
            return None
    except Exception:  # noqa: BLE001
        return None
    return LS


class CosmicDesktop(GnomeDesktop):
    name = "COSMIC"

    def __init__(self, app):
        super().__init__(app)
        self.watch = D.DragWatch()
        self.reader = InputReader()
        self.LS = layer_shell()
        self._layered: set[int] = set()
        self._center: tuple[float, float] | None = None
        self._await_enter = False
        self._input_ok = False

    @property
    def overlay_dim(self) -> float:
        """Sem a extensão, a própria roda escurece a tela atrás dela."""
        return settings.get()["dim"] / 100

    # -- ciclo de vida ---------------------------------------------------------
    def start(self) -> None:
        if self.LS is None:
            log.warning("gtk4-layer-shell indisponível: a roda não fica "
                        "acima das outras janelas nem recebe o arraste")
        self._input_ok = self.reader.start()
        if not self._input_ok:
            log.warning("sem acesso a /dev/input (grupo `input`): o gesto "
                        "Shift + arrastar fica desligado; use `mexerica "
                        "wheel` (Abrir com > Mexerica)")
            return
        GLib.timeout_add(D.IDLE_POLL_MS, self._tick)
        log.info("detecção de arraste do COSMIC ativa (%d dispositivos)",
                 len(readable_devices()))

    def stop(self) -> None:
        self.reader.stop()

    # -- arraste ---------------------------------------------------------------
    def _tick(self):
        busy = False
        try:
            busy = self._poll()
        except Exception:  # noqa: BLE001 - o laço não pode parar
            log.exception("falha ao ler mouse e teclado")
        GLib.timeout_add(D.POLL_MS if busy else D.IDLE_POLL_MS, self._tick)
        return GLib.SOURCE_REMOVE

    def _poll(self) -> bool:
        button, moved, mods = self.reader.snapshot()
        mode = D.mode_for(*mods) if button else None
        now = time.monotonic() * 1000
        was_open = bool(self.watch.shown)
        act = self.watch.step(button, moved, mode, (0, 0), now)
        if act is None and self.watch.shown:
            ov = self.app.overlay
            act = self.watch.probe(bool(ov and ov.paths), now)
            if act:
                log.info("arraste sem arquivos para a roda; desistindo")
        if act and act[0] == D.SHOW:
            if not was_open:
                self._center = None
                self._await_enter = True    # invisível até o arraste entrar
            self.app.show_wheel(act[1], [])
        elif act:
            self._await_enter = False
            self._center = None
            self.app.hide_wheel()
        return button or bool(self.watch.shown)

    # -- ganchos da roda (app.Overlay) ----------------------------------------
    def ready_to_draw(self, win) -> bool:
        return not self._await_enter

    def pointer_seen(self, win, x: float, y: float) -> None:
        """Primeiro evento do arraste sobre a roda: é onde o ponteiro está."""
        if self._await_enter:
            self._await_enter = False
            self._center = (x, y)
            win.wheel = None
            win.area.queue_draw()

    def wheel_center(self, win, w: float, h: float):
        return self._center          # None = centro da tela (mexerica wheel)

    def show_overlay(self, win) -> None:
        if self.LS is not None and id(win) not in self._layered:
            LS = self.LS
            LS.init_for_window(win)
            LS.set_namespace(win, "mexerica")
            LS.set_layer(win, LS.Layer.OVERLAY)
            for edge in (LS.Edge.TOP, LS.Edge.BOTTOM, LS.Edge.LEFT,
                         LS.Edge.RIGHT):
                LS.set_anchor(win, edge, True)
            LS.set_exclusive_zone(win, -1)      # cobre também o painel
            LS.set_keyboard_mode(win, LS.KeyboardMode.ON_DEMAND)
            self._layered.add(id(win))
        elif self.LS is None:
            # sem a sobreposição: janela maximizada, como no GNOME
            super().show_overlay(win)
            return
        win.present()

    # -- iniciar com o sistema (autostart do XDG, chave Hidden) ----------------
    def autostart(self) -> bool | None:
        src = _autostart_source()
        if src is None:
            return None
        text = src.read_text()
        return "Hidden=true" not in text and \
            "X-GNOME-Autostart-enabled=false" not in text

    def set_autostart(self, enabled: bool) -> None:
        src = _autostart_source()
        if src is None:
            return
        lines = [ln for ln in src.read_text().splitlines()
                 if not ln.startswith(("X-GNOME-Autostart-enabled=",
                                       "Hidden="))]
        lines.append(f"Hidden={str(not enabled).lower()}")
        _USER_AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
        _USER_AUTOSTART.write_text("\n".join(lines) + "\n")

    # -- sistema -------------------------------------------------------------
    def set_clipboard(self, text: str) -> None:
        if T.which("wl-copy"):
            subprocess.run(["wl-copy"], input=text, text=True, check=False)
            return
        display = Gdk.Display.get_default()
        if display:
            display.get_clipboard().set(text)

    def status(self) -> str:
        parts = []
        if self._input_ok:
            parts.append("Shift + arrastar: <b>ativo</b> (experimental)")
        elif os.path.exists("/dev/input"):
            parts.append("Shift + arrastar: <b>desligado</b>, sem acesso ao "
                         "teclado e mouse (entre no grupo <tt>input</tt>)")
        parts.append("Sobreposição (gtk4-layer-shell): <b>"
                     + ("ok" if self.LS else "ausente") + "</b>")
        if not T.which("wl-copy"):
            parts.append("Clipboard: instale <tt>wl-clipboard</tt>")
        return "\n".join(parts)

