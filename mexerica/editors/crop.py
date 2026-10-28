"""Recorte: a tela com retângulo e alças (usada também pelo Edit) e a
janela "Crop Image" (ferramenta CROP)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from .. import cropmath as CM  # noqa: E402
from .. import theme as TH  # noqa: E402
from ..engine import edits as E  # noqa: E402
from ..engine import tools as T  # noqa: E402
from ..engine.ops import Op  # noqa: E402
from .base import EditorWindow, Segmented, label, spin  # noqa: E402
from .common import bg, texture  # noqa: E402

GRAB = 12                 # px de tolerância para pegar canto/borda
PREVIEW_PX = 1400
CURSORS = {"nw": "nw-resize", "ne": "ne-resize", "sw": "sw-resize",
           "se": "se-resize", "n": "n-resize", "s": "s-resize",
           "e": "e-resize", "w": "w-resize", "move": "move",
           "new": "crosshair"}
ASPECTS: list[tuple[str, float | None]] = [
    ("Free", None), ("1:1", 1.0), ("16:9", 16 / 9), ("9:16", 9 / 16),
    ("4:3", 4 / 3), ("3:4", 3 / 4),
]


def load_preview(path: Path, out: Path) -> tuple[tuple[int, int],
                                                 tuple[int, int], bytes]:
    """(tamanho real, tamanho da prévia, PNG da prévia), orientação já
    corrigida. Roda numa thread."""
    size = E.image_size(path)
    subprocess.run(
        T.cmd("magick") + [
            "-define", f"jpeg:size={PREVIEW_PX * 2}x{PREVIEW_PX * 2}",
            f"{path}[0]", "-auto-orient", "-thumbnail",
            f"{PREVIEW_PX}x{PREVIEW_PX}>",
            "-define", "png:compression-level=1", str(out)],
        check=True, capture_output=True, stdin=subprocess.DEVNULL)
    return size, E.image_size(out), out.read_bytes()


class CropCanvas(Gtk.Overlay):
    """Prévia com retângulo de recorte. Coordenadas normalizadas sobre a
    imagem como ela aparece (`shown`, já girada)."""

    def __init__(self, on_change=None):
        self.picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN,
                                   can_shrink=True, hexpand=True,
                                   vexpand=True)
        super().__init__(child=self.picture)
        self.add_css_class("mx-canvas")
        self.set_overflow(Gtk.Overflow.HIDDEN)
        self.area = Gtk.DrawingArea(hexpand=True, vexpand=True)
        self.area.set_draw_func(self._draw)
        self.add_overlay(self.area)
        self.spinner = Gtk.Spinner(spinning=True, halign=Gtk.Align.CENTER,
                                   valign=Gtk.Align.CENTER,
                                   width_request=28, height_request=28)
        self.add_overlay(self.spinner)
        self.shown: tuple[int, int] | None = None
        self.crop: CM.Rect = [0.0, 0.0, 1.0, 1.0]
        self.ratio: float | None = None          # px (16:9 = 1.777)
        self._drag = None
        self._on_change = on_change
        self.pad = 10                              # respiro em volta

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end", self._drag_end)
        self.area.add_controller(drag)
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._motion)
        self.area.add_controller(motion)
        click = Gtk.GestureClick()
        click.connect("pressed", self._click)
        self.area.add_controller(click)
        self.picture.set_margin_start(self.pad)
        self.picture.set_margin_end(self.pad)
        self.picture.set_margin_top(self.pad)
        self.picture.set_margin_bottom(self.pad)

    # --- estado -----------------------------------------------------------
    def set_image(self, tex, shown: tuple[int, int]) -> None:
        self.spinner.set_visible(False)
        self.picture.set_paintable(tex)
        self.shown = shown
        self.area.queue_draw()

    def set_crop(self, rect: CM.Rect, notify: bool = True) -> None:
        self.crop = list(rect)
        self.area.queue_draw()
        if notify and self._on_change:
            self._on_change()

    def set_ratio(self, ratio: float | None) -> None:
        self.ratio = ratio
        if ratio and self.shown:
            self.set_crop(CM.largest_centered(ratio, *self.shown))
        else:
            self.area.queue_draw()

    def value(self) -> CM.Rect | None:
        return None if CM.is_full(self.crop) else list(self.crop)

    # --- geometria ---------------------------------------------------------
    def _img_rect(self) -> tuple[float, float, float, float]:
        W = self.area.get_width() - 2 * self.pad
        H = self.area.get_height() - 2 * self.pad
        dw, dh = self.shown or (1, 1)
        s = min(W / dw, H / dh)
        rw, rh = dw * s, dh * s
        return self.pad + (W - rw) / 2, self.pad + (H - rh) / 2, rw, rh

    def _k(self) -> float | None:
        if not self.shown:
            return None
        return CM.norm_ratio(self.ratio, *self.shown)

    def _hit(self, x: float, y: float) -> str:
        rx, ry, rw, rh = self._img_rect()
        x0, y0, w, h = self.crop
        cx, cy, cw, ch = rx + x0 * rw, ry + y0 * rh, w * rw, h * rh
        near_l, near_r = abs(x - cx) < GRAB, abs(x - cx - cw) < GRAB
        near_t, near_b = abs(y - cy) < GRAB, abs(y - cy - ch) < GRAB
        in_x = cx - GRAB < x < cx + cw + GRAB
        in_y = cy - GRAB < y < cy + ch + GRAB
        v = "n" if near_t and in_x else "s" if near_b and in_x else ""
        hh = "w" if near_l and in_y else "e" if near_r and in_y else ""
        if v or hh:
            return v + hh
        # sem recorte ainda: arrastar dentro da imagem desenha um novo
        if self.value() and cx < x < cx + cw and cy < y < cy + ch:
            return "move"
        return "new"

    # --- interação --------------------------------------------------------
    def _motion(self, _c, x, y) -> None:
        if self.shown and self._drag is None:
            self.area.set_cursor_from_name(CURSORS[self._hit(x, y)])

    def _click(self, _g, n_press, x, y) -> None:
        if n_press == 2 and self._hit(x, y) == "move":
            self.set_crop([0.0, 0.0, 1.0, 1.0])

    def _drag_begin(self, _g, x, y) -> None:
        if not self.shown:
            return
        mode = self._hit(x, y)
        start = list(self.crop)
        if mode == "new":
            rx, ry, rw, rh = self._img_rect()
            start = [min(max((x - rx) / rw, 0), 1),
                     min(max((y - ry) / rh, 0), 1), 0.0, 0.0]
        self._drag = (mode, start)

    def _drag_update(self, _g, dx, dy) -> None:
        if not self._drag:
            return
        mode, start = self._drag
        _rx, _ry, rw, rh = self._img_rect()
        ndx, ndy = dx / rw, dy / rh
        if mode == "move":
            self.set_crop(CM.moved(start, ndx, ndy))
            return
        if mode == "new":
            if abs(dx) < 3 and abs(dy) < 3:
                return
            mode = ("s" if ndy >= 0 else "n") + ("e" if ndx >= 0 else "w")
        self.set_crop(CM.resized(mode, start, ndx, ndy, self._k()))

    def _drag_end(self, *_a) -> None:
        self._drag = None
        self.area.queue_draw()

    # --- desenho ----------------------------------------------------------
    def _draw(self, _area, cr, _W, _H) -> None:
        if not self.shown:
            return
        rx, ry, rw, rh = self._img_rect()
        x, y, w, h = self.crop
        cx, cy, cw, ch = rx + x * rw, ry + y * rh, w * rw, h * rh
        if self.value():
            cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            cr.rectangle(rx, ry, rw, rh)
            cr.rectangle(cx, cy, cw, ch)
            cr.set_source_rgba(*TH.CROP_DIM)
            cr.fill()
            cr.set_fill_rule(cairo.FILL_RULE_WINDING)
        if self._drag:
            cr.set_source_rgba(1, 1, 1, 0.45)
            cr.set_line_width(1)
            for i in (1, 2):
                cr.move_to(cx + cw * i / 3, cy)
                cr.line_to(cx + cw * i / 3, cy + ch)
                cr.move_to(cx, cy + ch * i / 3)
                cr.line_to(cx + cw, cy + ch * i / 3)
            cr.stroke()
        cr.set_source_rgba(*TH.CROP_LINE)
        cr.set_line_width(1.5)
        cr.rectangle(cx, cy, cw, ch)
        cr.stroke()
        s = TH.HANDLE_PX
        for hx, hy in ((cx, cy), (cx + cw / 2, cy), (cx + cw, cy),
                       (cx, cy + ch / 2), (cx + cw, cy + ch / 2),
                       (cx, cy + ch), (cx + cw / 2, cy + ch),
                       (cx + cw, cy + ch)):
            cr.rectangle(hx - s / 2, hy - s / 2, s, s)
        cr.set_source_rgba(*TH.HANDLE)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.set_line_width(1)
        cr.stroke()


class CropWindow(EditorWindow):
    """Ferramenta CROP: recorte com proporção e medidas em pixels."""

    def __init__(self, app, op: Op, path: Path):
        super().__init__(app, op, "Crop Image", 680, 600, primary="Apply")
        self.path = path
        self.src_size: tuple[int, int] | None = None
        self._syncing = False

        self.canvas = CropCanvas(on_change=self._canvas_changed)
        self.canvas.set_size_request(560, 360)
        self.body.append(self.canvas)

        self.aspect = Segmented([a[0] for a in ASPECTS],
                                on_change=self._on_aspect)
        ar = Gtk.Box(spacing=10)
        ar.append(label("Aspect ratio", hexpand=True))
        ar.append(self.aspect)
        self.body.append(ar)

        self.w_spin = spin(1, 100000, 1, width=6)
        self.h_spin = spin(1, 100000, 1, width=6)
        self.w_spin.connect("value-changed", self._on_size, "w")
        self.h_spin.connect("value-changed", self._on_size, "h")
        sizes = Gtk.Box(spacing=6)
        sizes.append(label("Size", hexpand=True))
        for w in (label("W", "mx-dim"), self.w_spin, label("×", "mx-dim"),
                  label("H", "mx-dim"), self.h_spin, label("px", "mx-dim")):
            sizes.append(w)
        self.body.append(sizes)
        self.say("Loading…")

        out = self.tmp / "base.png"
        bg(lambda: load_preview(path, out), self.alive(self._loaded))

    def _loaded(self, res) -> None:
        if isinstance(res, Exception):
            self.say(f"Could not open the image: {res}", error=True)
            return
        self.src_size, shown, png = res
        self.canvas.set_image(texture(png), shown)
        self.save_btn.set_sensitive(True)
        self.say("")
        self._canvas_changed()

    # --- sincronia retângulo <-> campos ------------------------------------
    def _canvas_changed(self) -> None:
        if not self.src_size:
            return
        W, H = self.src_size
        _x, _y, w, h = self.canvas.crop
        self._syncing = True
        self.w_spin.set_range(1, W)
        self.h_spin.set_range(1, H)
        self.w_spin.set_value(round(w * W))
        self.h_spin.set_value(round(h * H))
        self._syncing = False

    def _on_size(self, sp, which) -> None:
        if self._syncing or not self.src_size:
            return
        W, H = self.src_size
        w_px, h_px = self.w_spin.get_value(), self.h_spin.get_value()
        ratio = self.canvas.ratio
        if ratio:
            if which == "w":
                h_px = w_px / ratio
                if h_px > H:
                    h_px, w_px = H, H * ratio
            else:
                w_px = h_px * ratio
                if w_px > W:
                    w_px, h_px = W, W / ratio
        self.canvas.set_crop(CM.with_size_px(self.canvas.crop, w_px, h_px,
                                             W, H))

    def _on_aspect(self, i: int) -> None:
        self.canvas.set_ratio(ASPECTS[i][1])
        if ASPECTS[i][1] is None:
            self._canvas_changed()

    def reset(self) -> None:
        self.aspect.set_active(0)
        self.canvas.ratio = None
        self.canvas.set_crop([0.0, 0.0, 1.0, 1.0])

    def build(self):
        rect = self.canvas.value()
        if rect is None:
            raise ValueError("Drag on the image to choose an area.")
        edit = E.ImageEdit(crop=tuple(rect))
        return E.image_edit_op(self.op, edit, " Cropped"), [self.path]
