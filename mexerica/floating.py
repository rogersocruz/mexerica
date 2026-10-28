"""Janela Flutuar: guarda arquivos numa bolha sempre visível, para arrastar
depois para qualquer lugar.

Uma bolha de vidro com o ícone do arquivo como o PC mostra (miniatura, ou o
ícone do tipo; de um atalho ou programa, o ícone do programa), o nome
embaixo, o "×" às 3 horas e o botão de arrastar (setas em cruz) às 9.
Arrastar a bolha leva os arquivos (e fecha a janela, como antes); arrastar
o botão ou o nome move a janela. Com vários arquivos, um contador no canto
do ícone.
"""
from __future__ import annotations

from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk, Pango  # noqa: E402

from . import theme as TH  # noqa: E402
from .wheel.render import draw_disc  # noqa: E402

# "Mexerica — " deixa a janela acima das outras (extensão do GNOME e backend
# do Windows); "Flutuar" avisa a extensão para não borrar atrás (é redonda).
TITLE_PREFIX = "Mexerica — Flutuar · "
WIDTH = 152                 # janela
CX, CY, R = 76, 72, 56      # bolha
AREA_H = CY + R + 16        # bolha + sombra
ICON_PX = 64
CLOSE_PX = 26


class FloatWindow(Gtk.Window):
    def __init__(self, app, paths: list[Path]):
        n = len(paths)
        name = app.desktop.display_name(paths[0]) if n == 1 else f"{n} arquivos"
        super().__init__(application=app, title=TITLE_PREFIX + name,
                         decorated=False, resizable=False)
        self.add_css_class("mx-float")
        self.paths = paths
        self._hover = 0.0

        self.disc = Gtk.DrawingArea(content_width=WIDTH, content_height=AREA_H)
        self.disc.set_draw_func(self._draw)
        self.disc.set_cursor_from_name("grab")
        self.disc.set_tooltip_text("Arraste para levar o arquivo"
                                   if n == 1 else "Arraste para levar os arquivos")
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_: self._set_hover(1.0))
        motion.connect("leave", lambda *_: self._set_hover(0.0))
        self.disc.add_controller(motion)

        icon = _icon_widget(app.desktop.file_icon(paths[0], ICON_PX))
        icon.set_can_target(False)          # o arraste é da bolha inteira
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_valign(Gtk.Align.START)
        icon.set_margin_top(CY - ICON_PX // 2)

        close = Gtk.Button(label="×", tooltip_text="Fechar")
        close.add_css_class("mx-float-close")
        close.set_size_request(CLOSE_PX, CLOSE_PX)
        close.set_halign(Gtk.Align.START)
        close.set_valign(Gtk.Align.START)
        close.set_margin_start(CX + R - CLOSE_PX // 2)      # às 3 horas
        close.set_margin_top(CY - CLOSE_PX // 2)
        close.connect("clicked", lambda *_: self.close())

        grip = Gtk.DrawingArea(content_width=CLOSE_PX, content_height=CLOSE_PX)
        grip.set_draw_func(_draw_move)
        grip.add_css_class("mx-float-move")
        grip.set_cursor_from_name("move")
        move = Gtk.WindowHandle(child=grip, tooltip_text="Arraste para mover",
                                halign=Gtk.Align.START, valign=Gtk.Align.START)
        move.set_margin_start(CX - R - CLOSE_PX // 2)        # às 9 horas
        move.set_margin_top(CY - CLOSE_PX // 2)

        top = Gtk.Overlay(child=self.disc)
        top.add_overlay(icon)
        if n > 1:                       # contador por cima do ícone
            badge = Gtk.Label(label=str(n), halign=Gtk.Align.START,
                              valign=Gtk.Align.START, can_target=False)
            badge.add_css_class("mx-float-badge")
            badge.set_margin_start(CX + ICON_PX // 2 - 14)
            badge.set_margin_top(CY + ICON_PX // 2 - 14)
            top.add_overlay(badge)
        top.add_overlay(close)
        top.add_overlay(move)

        label = Gtk.Label(label=name, ellipsize=Pango.EllipsizeMode.MIDDLE,
                          max_width_chars=16, justify=Gtk.Justification.CENTER)
        label.add_css_class("mx-float-label")
        handle = Gtk.WindowHandle(child=label, halign=Gtk.Align.CENTER,
                                  tooltip_text="Arraste para mover a janela")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0,
                      margin_bottom=6)
        box.append(top)
        box.append(handle)
        self.set_child(box)
        app.desktop.drag_source(self.disc, paths, self.close)

    def _set_hover(self, value: float) -> None:
        self._hover = value
        self.disc.queue_draw()

    def _draw(self, _area, cr, _w, _h) -> None:
        draw_disc(cr, CX, CY, R, self._hover)


def _draw_move(_area, cr, w, h) -> None:
    """Setas em cruz, na cor do texto do estilo."""
    x, y, arm, head = w / 2, h / 2, 7.0, 2.6
    cr.set_source_rgba(*TH.LABEL_COLOR)
    cr.set_line_width(1.6)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.move_to(x - arm, y)
    cr.line_to(x + arm, y)
    cr.move_to(x, y - arm)
    cr.line_to(x, y + arm)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        tx, ty = x + dx * arm, y + dy * arm
        cr.move_to(tx - dx * head + dy * head, ty - dy * head + dx * head)
        cr.line_to(tx, ty)
        cr.line_to(tx - dx * head - dy * head, ty - dy * head - dx * head)
    cr.stroke()


def _icon_widget(icon) -> Gtk.Image:
    """Gtk.Image do que o backend achou: textura (miniatura, ícone do
    Windows) ou Gio.Icon (tema de ícones do GNOME)."""
    if icon is None:
        image = Gtk.Image.new_from_icon_name("text-x-generic")
    elif isinstance(icon, Gio.Icon):
        image = Gtk.Image.new_from_gicon(icon)
    else:
        image = Gtk.Image.new_from_paintable(icon)
    image.set_pixel_size(ICON_PX)
    return image


__all__ = ["FloatWindow", "TITLE_PREFIX"]
