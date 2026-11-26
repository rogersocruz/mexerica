"""COSMIC (Pop!_OS 24.04+) e outros desktops Linux sem a extensão do
GNOME Shell (KDE, Sway, Hyprland...).

Sem extensão, nenhum programa vê o Shift durante um arraste: o Wayland só
entrega o arraste a quem está embaixo do ponteiro, e o COSMIC não tem API
de extensões. O gatilho vira um atalho de teclado (Configurações do COSMIC >
Teclado > Atalhos personalizados) que roda `mexerica wheel`: a roda abre e
espera o arquivo ser arrastado até ela (o mesmo drop do GNOME). Com
arquivos na linha de comando (`mexerica wheel --group tools ARQ`), clicar
num item escolhe.

A roda vai numa camada "overlay" do wlr-layer-shell (o cosmic-comp, o
KWin, o Sway e o Hyprland suportam) quando o gtk4-layer-shell está
instalado: acima de tudo, sem foco, cobrindo a tela. Sem ele, a janela é
maximizada como no GNOME. O resto (clipboard, mostrar na pasta, terminal,
notificações) é freedesktop e vem do backend do GNOME.
"""
from __future__ import annotations

import ctypes.util
import logging
import os

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402,F401

from .. import settings  # noqa: E402
from .gnome import GnomeDesktop  # noqa: E402

log = logging.getLogger("mexerica")

LAYER_LIB = "gtk4-layer-shell"


def current_desktop() -> str:
    return os.environ.get("XDG_CURRENT_DESKTOP", "")


def is_gnome() -> bool:
    """GNOME, Ubuntu ("ubuntu:GNOME") e o Pop!_OS antigo ("pop:GNOME")."""
    return "GNOME" in current_desktop().upper().split(":")


def is_cosmic() -> bool:
    return "COSMIC" in current_desktop().upper().split(":")


def layer_shell_preload() -> str | None:
    """A biblioteca do gtk4-layer-shell, se instalada. Ela precisa ser
    carregada antes do libwayland-client (LD_PRELOAD); __main__ reinicia o
    serviço com ela."""
    if os.environ.get("MEXERICA_NO_LAYER_SHELL"):
        return None
    name = ctypes.util.find_library(LAYER_LIB)
    return name


def _layer_shell():
    try:
        gi.require_version("Gtk4LayerShell", "1.0")
        from gi.repository import Gtk4LayerShell as LS
    except (ValueError, ImportError):
        return None
    return LS if LS.is_supported() else None


class WaylandDesktop(GnomeDesktop):
    name = "COSMIC" if is_cosmic() else "Linux"

    @property
    def overlay_dim(self) -> float:
        """Sem a extensão, a própria roda escurece a tela atrás dela."""
        return settings.get()["dim"] / 100

    def start(self) -> None:
        log.info("%s: sem detecção de arraste; a roda abre pelo atalho "
                 "(mexerica wheel)", self.name)

    def show_overlay(self, win) -> None:
        LS = _layer_shell()
        if LS is None:
            super().show_overlay(win)
            return
        if not LS.is_layer_window(win):
            LS.init_for_window(win)
            LS.set_namespace(win, "mexerica")
            LS.set_layer(win, LS.Layer.OVERLAY)
            for edge in (LS.Edge.TOP, LS.Edge.BOTTOM, LS.Edge.LEFT,
                         LS.Edge.RIGHT):
                LS.set_anchor(win, edge, True)
            LS.set_exclusive_zone(win, -1)      # por cima dos painéis
            LS.set_keyboard_mode(win, LS.KeyboardMode.ON_DEMAND)
        win.present()

    def wheel_center(self, win, w: float, h: float):
        # o Wayland não diz onde está o ponteiro antes dele se mexer sobre a
        # janela: a roda abre no centro da tela
        return None

    def drag_ok(self) -> bool | None:
        """Sem detecção de arraste aqui: a roda abre pelo atalho."""
        return None


__all__ = ["WaylandDesktop", "is_gnome", "is_cosmic", "layer_shell_preload"]
