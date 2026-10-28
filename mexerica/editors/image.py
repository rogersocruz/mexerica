"""Imagem: "Edit Image" (EDIT) e "Resize" (RESIZE, em lote)."""
from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from .. import cropmath as CM  # noqa: E402
from ..engine import edits as E  # noqa: E402
from ..engine import formats as F  # noqa: E402
from ..engine import tools as T  # noqa: E402
from ..engine.ops import Op  # noqa: E402
from .base import (EditorWindow, Segmented, SliderRow, dropdown, label,  # noqa: E402
                   row, spin)
from .common import (Latest, bg, fmt_size, image_formats, lossy,  # noqa: E402
                     run_out, texture)
from .crop import ASPECTS, CropCanvas, load_preview  # noqa: E402


def _section(text: str) -> Gtk.Label:
    lbl = label(text.upper(), "mx-dim")
    lbl.set_margin_top(6)
    return lbl


class ImageEditor(EditorWindow):
    """Recorte, girar/espelhar, brilho/contraste/saturação, escala e
    formato, com prévia ao vivo."""

    def __init__(self, app, op: Op, path: Path):
        super().__init__(app, op, "Edit Image", 1040, 680, primary="Save")
        self.path = path
        self.edit = E.ImageEdit()
        self.src_size: tuple[int, int] | None = None
        self.base_size: tuple[int, int] | None = None
        self.base: Path | None = None
        self.base_tex = None
        self.render = Latest(30)
        self.formats = image_formats()

        self.canvas = CropCanvas(on_change=self._update_info)
        self.canvas.set_size_request(560, 420)

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                        width_request=300, margin_start=6)
        panel.append(_section("Crop"))
        self.aspect = Segmented([a[0] for a in ASPECTS],
                                on_change=self._on_aspect)
        panel.append(self.aspect)
        self.crop_info = label("", "mx-dim")
        panel.append(self.crop_info)

        panel.append(_section("Rotate & flip"))
        tools = Gtk.Box(spacing=6, homogeneous=True)
        for icon, tip, cb in (
                ("object-rotate-left-symbolic", "Rotate left (L)",
                 lambda *_: self._rotate(-90)),
                ("object-rotate-right-symbolic", "Rotate right (R)",
                 lambda *_: self._rotate(90)),
                ("object-flip-horizontal-symbolic", "Flip horizontal (H)",
                 lambda *_: self._flip(True)),
                ("object-flip-vertical-symbolic", "Flip vertical (V)",
                 lambda *_: self._flip(False))):
            b = Gtk.Button(icon_name=icon, tooltip_text=tip)
            b.connect("clicked", cb)
            tools.append(b)
        panel.append(tools)

        panel.append(_section("Adjust"))
        self.sliders = {}
        for key, title in (("brightness", "Brightness"),
                           ("contrast", "Contrast"),
                           ("saturation", "Saturation")):
            sr = SliderRow(title, -100, 100, 0, unit="",
                           on_change=lambda v, k=key: self._on_adjust(k, v))
            self.sliders[key] = sr
            panel.append(sr)
        self.gray = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.gray.connect("notify::active", lambda *_: self._on_gray())
        panel.append(row("Black & white", self.gray))

        panel.append(_section("Output"))
        self.scale = spin(5, 100, 100, step=5, width=4)
        self.scale.connect("value-changed", lambda *_: self._update_info())
        panel.append(row("Scale (%)", self.scale))
        self.fmt_dd = dropdown([f[0] for f in self.formats])
        self.fmt_dd.connect("notify::selected",
                            lambda *_: self._update_info())
        panel.append(row("Format", self.fmt_dd))
        self.quality = SliderRow("Quality", 30, 100, 90, unit="")
        panel.append(self.quality)
        self.out_info = label("", "mx-dim", wrap=True)
        panel.append(self.out_info)

        scroll = Gtk.ScrolledWindow(child=panel, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                    propagate_natural_width=True)
        body = Gtk.Box(spacing=12, vexpand=True)
        body.append(self.canvas)
        body.append(scroll)
        self.body.append(body)
        self.say("Loading…")
        out = self.tmp / "base.png"
        bg(lambda: load_preview(path, out), self.alive(self._loaded))

    # --- carregamento e prévia ---------------------------------------------
    def _loaded(self, res) -> None:
        if isinstance(res, Exception):
            self.say(f"Could not open the image: {res}", error=True)
            return
        self.src_size, self.base_size, png = res
        self.base = self.tmp / "base.png"
        self.base_tex = texture(png)
        self.canvas.set_image(self.base_tex, self.base_size)
        self.save_btn.set_sensitive(True)
        self.say("")
        self._update_info()

    def _shown(self) -> tuple[int, int]:
        w, h = self.base_size or (1, 1)
        return (h, w) if self.edit.rotate % 180 else (w, h)

    def _rerender(self) -> None:
        if not self.base:
            return
        e = dataclasses.replace(self.edit, crop=None, scale=100, max_side=0,
                                target_kb=0, ext=None)
        args = e.args(0, 0, "png")
        if not args:
            self.render.cancel()
            self.canvas.set_image(self.base_tex, self._shown())
            return
        argv = T.cmd("magick") + [str(self.base), *args, "-define",
                                  "png:compression-level=1", "png:-"]
        shown = self._shown()
        self.render.request(
            lambda: run_out(argv),
            self.alive(lambda r: self.say(f"Preview failed: {r}", True)
                       if isinstance(r, Exception)
                       else self.canvas.set_image(texture(r), shown)))

    # --- girar / espelhar ----------------------------------------------------
    # Estado canônico: girar R primeiro e depois (talvez) espelhar na
    # horizontal. Virar de cabeça = espelhar + 180°.
    def _rotate(self, deg: int) -> None:
        mirrored = self.edit.flip_h
        self.edit.rotate = (self.edit.rotate + (-deg if mirrored else deg)) \
            % 360
        self.canvas.shown = self._shown()
        if self.canvas.ratio:
            self.aspect.set_active(0)
            self.canvas.ratio = None
        self.canvas.set_crop(CM.rotated(self.canvas.crop, deg))
        self._rerender()

    def _flip(self, horizontal: bool) -> None:
        self.edit.flip_h = not self.edit.flip_h
        if not horizontal:
            self.edit.rotate = (self.edit.rotate + 180) % 360
        self.canvas.set_crop(CM.flipped(self.canvas.crop, horizontal))
        self._rerender()

    def _on_aspect(self, i: int) -> None:
        self.canvas.set_ratio(ASPECTS[i][1])
        self._update_info()

    # --- ajustes -------------------------------------------------------------
    def _on_adjust(self, key: str, value: int) -> None:
        setattr(self.edit, key, value)
        if key == "saturation" and self.gray.get_active():
            self.edit.saturation = -100
        self._rerender()

    def _on_gray(self) -> None:
        on = self.gray.get_active()
        self.sliders["saturation"].set_sensitive(not on)
        self.edit.saturation = -100 if on else \
            self.sliders["saturation"].get()
        self._rerender()

    def reset(self) -> None:
        for sr in self.sliders.values():
            sr.set(0)
        self.gray.set_active(False)
        self.edit = E.ImageEdit()
        self.aspect.set_active(0)
        self.canvas.ratio = None
        self.canvas.shown = self._shown()
        self.canvas.set_crop([0.0, 0.0, 1.0, 1.0])
        self.scale.set_value(100)
        self.fmt_dd.set_selected(0)
        self._rerender()

    # --- informações ---------------------------------------------------------
    def _out_ext(self) -> str:
        return self.formats[self.fmt_dd.get_selected()][1] or \
            F.full_ext(self.path)

    def _update_info(self) -> None:
        if not self.src_size:
            return
        w, h = self.src_size
        if self.edit.rotate % 180:
            w, h = h, w
        cw = round(self.canvas.crop[2] * w)
        ch = round(self.canvas.crop[3] * h)
        self.crop_info.set_text(f"{cw} × {ch} px" +
                                ("" if self.canvas.value() else " (full)"))
        s = self.scale.get_value() / 100
        ext = self._out_ext()
        self.quality.set_visible(lossy(ext))
        self.out_info.set_text(
            f"{max(1, round(cw * s))} × {max(1, round(ch * s))} px · "
            f"{ext.upper()} · saved next to the original")

    def on_key(self, keyval, state) -> bool:
        if isinstance(self.get_focus(), (Gtk.Text, Gtk.SpinButton)):
            return False
        actions = {Gdk.KEY_r: lambda: self._rotate(90),
                   Gdk.KEY_l: lambda: self._rotate(-90),
                   Gdk.KEY_h: lambda: self._flip(True),
                   Gdk.KEY_v: lambda: self._flip(False)}
        fn = actions.get(Gdk.keyval_to_lower(keyval))
        if fn and self.base_size:
            fn()
            return True
        return False

    def build(self):
        crop = self.canvas.value()
        self.edit.crop = tuple(crop) if crop else None
        self.edit.scale = int(self.scale.get_value())
        self.edit.quality = self.quality.get()
        self.edit.ext = self.formats[self.fmt_dd.get_selected()][1]
        if self.edit == E.ImageEdit(quality=self.edit.quality):
            raise ValueError("Nothing changed yet.")
        only_crop = self.edit == E.ImageEdit(crop=self.edit.crop,
                                             quality=self.edit.quality)
        suffix = " Cropped" if only_crop else " Edited"
        return E.image_edit_op(self.op, self.edit, suffix), [self.path]

    def cleanup(self) -> None:
        self.render.cancel()


# --------------------------------------------------------------------------
# Resize (em lote)
# --------------------------------------------------------------------------

SIZES: list[tuple[str, int, int]] = [       # rótulo, escala %, lado máximo
    ("Original", 100, 0), ("75%", 75, 0), ("50%", 50, 0), ("25%", 25, 0),
    ("Max 3840 px", 100, 3840), ("Max 2560 px", 100, 2560),
    ("Max 1920 px", 100, 1920), ("Max 1280 px", 100, 1280),
    ("Max 1080 px", 100, 1080), ("Max 800 px", 100, 800),
    ("Max 512 px", 100, 512),
]
WEIGHTS: list[tuple[str, int]] = [
    ("No limit", 0), ("100 KB", 100), ("200 KB", 200), ("500 KB", 500),
    ("1 MB", 1000), ("2 MB", 2000), ("5 MB", 5000),
]


class ImageSizeWindow(EditorWindow):
    def __init__(self, app, op: Op, paths: list[Path]):
        n = len(paths)
        super().__init__(app, op, "Resize" + ("" if n == 1 else f" · {n} images"),
                         460, 360, primary="Save")
        self.paths = paths
        self.formats = image_formats()
        self.estimate = Latest(250)

        self.size_dd = dropdown([s[0] for s in SIZES])
        self.body.append(row("Size", self.size_dd))
        self.fmt_dd = dropdown([f[0] for f in self.formats])
        self.body.append(row("Format", self.fmt_dd))
        self.quality = SliderRow("Quality", 30, 100, 82, unit="",
                                 on_change=lambda _v: self._changed())
        self.body.append(self.quality)
        self.weight_dd = dropdown([w[0] for w in WEIGHTS])
        self.body.append(row("Max file size (JPG)", self.weight_dd))
        self.result = label("", "mx-label", wrap=True)
        self.body.append(self.result)

        for w in (self.size_dd, self.fmt_dd, self.weight_dd):
            w.connect("notify::selected", lambda *_: self._changed())
        self.save_btn.set_sensitive(True)
        self._changed()

    def _edit(self) -> E.ImageEdit:
        _l, scale, side = SIZES[self.size_dd.get_selected()]
        kb = WEIGHTS[self.weight_dd.get_selected()][1]
        ext = self.formats[self.fmt_dd.get_selected()][1]
        if kb:
            ext = "jpg"
        return E.ImageEdit(scale=scale, max_side=side, target_kb=kb,
                           quality=self.quality.get(), ext=ext)

    def _changed(self) -> None:
        edit = self._edit()
        ext = edit.ext or F.full_ext(self.paths[0])
        self.quality.set_visible(lossy(ext))
        self.fmt_dd.set_sensitive(not edit.target_kb)
        self.result.set_text("Calculating…")
        src = self.paths[0]
        out = self.tmp / f"preview.{'jpg' if ext == 'jpeg' else ext}"

        def work():
            w, h = E.image_size(src)
            argv = T.cmd("magick") + [f"{src}[0]", "-auto-orient",
                                      *edit.args(w, h, F.full_ext(out)),
                                      str(out)]
            subprocess.run(argv, check=True, capture_output=True,
                           stdin=subprocess.DEVNULL)
            ow, oh = E.image_size(out)
            return src.stat().st_size, out.stat().st_size, (w, h), (ow, oh)
        self.estimate.request(work, self.alive(self._estimated))

    def _estimated(self, res) -> None:
        if isinstance(res, Exception):
            self.result.set_text(f"No preview: {res}")
            return
        before, after, (w, h), (ow, oh) = res
        pct = after * 100 / before if before else 0
        first = "" if len(self.paths) == 1 else "First image: "
        self.result.set_text(
            f"{first}{w} × {h}, {fmt_size(before)}  →  "
            f"{ow} × {oh}, {fmt_size(after)} ({pct:.0f}%)")

    def reset(self) -> None:
        self.size_dd.set_selected(0)
        self.fmt_dd.set_selected(0)
        self.weight_dd.set_selected(0)
        self.quality.set(82)

    def build(self):
        edit = self._edit()
        if edit == E.ImageEdit(quality=edit.quality) and \
                not lossy(F.full_ext(self.paths[0])):
            raise ValueError("Nothing changed: pick a size, format or limit.")
        return E.image_edit_op(self.op, edit, " Resized"), self.paths

    def cleanup(self) -> None:
        self.estimate.cancel()
