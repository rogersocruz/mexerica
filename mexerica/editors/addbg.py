"""Ferramenta ADD BG: a imagem com cantos arredondados e sombra sobre um
fundo (gradiente, cor ou imagem), com prévia ao vivo. A prévia e o arquivo
final saem do mesmo engine/background.paint()."""
from __future__ import annotations

import dataclasses
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from .. import theme as TH  # noqa: E402
from ..engine import background as B  # noqa: E402
from ..engine import edits as E  # noqa: E402
from ..engine.ops import Op  # noqa: E402
from ..i18n import N_, _  # noqa: E402
from .base import (ColorButton, EditorWindow, Segmented, SliderRow,  # noqa: E402
                   label)
from .common import bg  # noqa: E402

PREVIEW_SIDE = 900


def _rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


class Swatch(Gtk.Button):
    """Quadradinho de 22 px com cantos de 6 px (cor ou gradiente)."""

    def __init__(self, colors: tuple[str, ...], tooltip: str, on_pick):
        super().__init__(tooltip_text=tooltip, valign=Gtk.Align.CENTER)
        self.add_css_class("mx-swatch")
        self.colors = colors
        area = Gtk.DrawingArea(content_width=TH.SWATCH_PX,
                               content_height=TH.SWATCH_PX)
        area.set_draw_func(self._draw)
        self.set_child(area)
        self.connect("clicked", lambda *_: on_pick(self))

    def _draw(self, _a, cr, w, h) -> None:
        r = TH.SWATCH_RADIUS
        cr.new_sub_path()
        cr.arc(w - r, r, r, -1.5708, 0)
        cr.arc(w - r, h - r, r, 0, 1.5708)
        cr.arc(r, h - r, r, 1.5708, 3.1416)
        cr.arc(r, r, r, 3.1416, 4.7124)
        cr.close_path()
        if len(self.colors) == 1:
            cr.set_source_rgb(*_rgb(self.colors[0]))
        else:
            g = cairo.LinearGradient(0, 0, w, h)
            g.add_color_stop_rgb(0, *_rgb(self.colors[0]))
            g.add_color_stop_rgb(1, *_rgb(self.colors[1]))
            cr.set_source(g)
        cr.fill()


class AddBgWindow(EditorWindow):
    def __init__(self, app, op: Op, path: Path):
        super().__init__(app, op, "Adicionar fundo", 720, 700,
                         primary="Salvar com fundo")
        self.path = path
        self.style = B.BgStyle(colors=TH.BG_GRADIENTS[0])
        self.img: cairo.ImageSurface | None = None
        self.k = 1.0
        self.bg_img: cairo.ImageSurface | None = None
        self.swatches: list[Swatch] = []

        self.preview = Gtk.DrawingArea(hexpand=True, vexpand=True)
        self.preview.set_size_request(560, 330)
        self.preview.add_css_class("mx-canvas")
        self.preview.set_draw_func(self._draw)
        self.body.append(self.preview)

        self.body.append(label("Fundo"))
        row1 = Gtk.Box(spacing=6)
        for c1, c2 in TH.BG_GRADIENTS:
            row1.append(self._swatch((c1, c2), f"{c1} → {c2}"))
        pick_img = Gtk.Button(label=_("Imagem…"), valign=Gtk.Align.CENTER)
        pick_img.add_css_class("mx-pill")
        pick_img.connect("clicked", lambda *_: self._choose_image())
        row1.append(pick_img)
        self.body.append(row1)
        row2 = Gtk.Box(spacing=6)
        for c in TH.BG_SOLIDS:
            row2.append(self._swatch((c,), c))
        self.custom = ColorButton(self.style.color, self._custom_color,
                                  text=N_("Outra cor"))
        self.custom.add_css_class("mx-pill")
        row2.append(self.custom)
        self.body.append(row2)

        lo, hi, dflt = TH.BG_PADDING
        self.padding = SliderRow("Margem", lo, hi, dflt,
                                 on_change=lambda v: self._set(padding=v))
        lo, hi, dflt = TH.BG_CORNERS
        self.corners = SliderRow("Cantos", lo, hi, dflt,
                                 on_change=lambda v: self._set(corners=v))
        lo, hi, dflt = TH.BG_SHADOW
        self.shadow = SliderRow("Sombra", lo, hi, dflt,
                                on_change=lambda v: self._set(shadow=v))
        for s in (self.padding, self.corners, self.shadow):
            self.body.append(s)
        ratio = Gtk.Box(spacing=10)
        ratio.append(label("Proporção", hexpand=True))
        self.ratio = Segmented([r[0] for r in TH.BG_RATIOS],
                               on_change=lambda i: self._set(
                                   ratio=TH.BG_RATIOS[i][1]))
        ratio.append(self.ratio)
        self.body.append(ratio)

        self._select(self.swatches[0])
        self.say("Carregando…")

        def load():
            size = E.image_size(path)
            img = B.load_png(path, self.tmp, "prev", PREVIEW_SIDE)
            return size, img
        bg(load, self.alive(self._loaded))

    # --- estado ------------------------------------------------------------
    def _swatch(self, colors, tip) -> Swatch:
        sw = Swatch(colors, tip, self._pick)
        self.swatches.append(sw)
        return sw

    def _select(self, chosen: Gtk.Widget | None) -> None:
        for w in [*self.swatches, self.custom]:
            if w is chosen:
                w.add_css_class("selected")
            else:
                w.remove_css_class("selected")

    def _pick(self, sw: Swatch) -> None:
        if len(sw.colors) == 1:
            self._set(kind="solid", color=sw.colors[0])
        else:
            self._set(kind="gradient", colors=tuple(sw.colors))
        self._select(sw)

    def _set(self, **changes) -> None:
        self.style = dataclasses.replace(self.style, **changes)
        self.preview.queue_draw()

    def _loaded(self, res) -> None:
        if isinstance(res, Exception):
            self.say(_("Não deu para abrir a imagem: {err}").format(err=res),
                     error=True)
            return
        (w, _h), self.img = res
        self.k = self.img.get_width() / w if w else 1.0
        self.save_btn.set_sensitive(True)
        self.say("PNG, salvo ao lado do original")
        self.preview.queue_draw()

    # --- escolhas externas -------------------------------------------------
    def _custom_color(self, color: str) -> None:
        """Outra cor (popover da própria janela, ColorButton)."""
        self._set(kind="solid", color=color)
        self._select(self.custom)

    def _choose_image(self) -> None:
        dialog = Gtk.FileDialog(title=_("Imagem de fundo"))
        filt = Gtk.FileFilter()
        filt.add_mime_type("image/*")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filt)
        dialog.set_filters(filters)

        def done(dlg, result):
            try:
                f = dlg.open_finish(result)
            except GLib.Error:
                return
            path = Path(f.get_path())
            self.say("Carregando o fundo…")
            bg(lambda: B.load_png(path, self.tmp, "bg", 1600),
               self.alive(lambda r: self._bg_loaded(path, r)))
        dialog.open(self, None, done)

    def _bg_loaded(self, path: Path, res) -> None:
        if isinstance(res, Exception):
            self.say(_("Não deu para abrir o fundo: {err}").format(err=res),
                     error=True)
            return
        self.bg_img = res
        self._select(None)
        self.say("")
        self._set(kind="image", image=str(path))

    # --- prévia -----------------------------------------------------------
    def _draw(self, _area, cr, W, H) -> None:
        if self.img is None:
            return
        cw, ch = B.canvas_size(self.img.get_width(), self.img.get_height(),
                               self.style, self.k)
        pad = 14
        s = min((W - 2 * pad) / cw, (H - 2 * pad) / ch)
        cr.translate((W - cw * s) / 2, (H - ch * s) / 2)
        cr.scale(s, s)
        cr.rectangle(0, 0, cw, ch)
        cr.clip()
        B.paint(cr, self.img, self.style, self.k, self.bg_img)

    def reset(self) -> None:
        self.style = B.BgStyle(colors=TH.BG_GRADIENTS[0])
        self.bg_img = None
        self.padding.set(TH.BG_PADDING[2])
        self.corners.set(TH.BG_CORNERS[2])
        self.shadow.set(TH.BG_SHADOW[2])
        self.ratio.set_active(0)
        self._select(self.swatches[0])
        self.preview.queue_draw()

    def build(self):
        return E.add_background_op(self.op, self.style), [self.path]
