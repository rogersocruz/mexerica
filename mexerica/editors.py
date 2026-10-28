"""Janelas abertas pela roda de ferramentas (Shift+Alt): Editar…, Recortar…,
Tamanho…, Cortar… e Páginas….

Todas abrem na hora: a janela aparece primeiro e o que é lento (prévia,
duração, miniaturas, forma de onda) carrega numa thread. Salvar fecha a
janela e entrega o trabalho ao mesmo runner das rodas (nunca sobrescreve,
notificação de progresso). Esc cancela; Enter ou Ctrl+S salva.
"""
from __future__ import annotations

import dataclasses
import logging
import shutil
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .engine import edits as E  # noqa: E402
from .engine import formats as F  # noqa: E402
from .engine import tools as T  # noqa: E402
from .engine.ops import Op  # noqa: E402

log = logging.getLogger("mexerica")


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def _bg(fn, done) -> None:
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


class _Latest:
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
        _bg(fn, finished)
        return GLib.SOURCE_REMOVE


def _texture(png: bytes) -> Gdk.Texture:
    return Gdk.Texture.new_from_bytes(GLib.Bytes.new(png))


def _out(argv: list[str]) -> bytes:
    proc = subprocess.run(argv, capture_output=True, stdin=subprocess.DEVNULL)
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode(errors="replace").strip().splitlines()
        raise RuntimeError(err[-1] if err else f"{argv[0]} falhou")
    return proc.stdout


def _fmt_time(t: float) -> str:
    t = max(t, 0.0)
    m, s = divmod(t, 60)
    h, m = divmod(int(m), 60)
    return f"{h}:{m:02d}:{s:05.2f}" if h else f"{m}:{s:05.2f}"


def _fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") \
                else f"{n:.1f} {unit}".replace(".", ",")
        n /= 1024
    return ""


def _section(title: str) -> Gtk.Label:
    lbl = Gtk.Label(label=title.upper(), xalign=0)
    lbl.add_css_class("mexerica-section")
    return lbl


def _row(label: str, widget: Gtk.Widget) -> Gtk.Box:
    box = Gtk.Box(spacing=10)
    lbl = Gtk.Label(label=label, xalign=0, hexpand=True)
    box.append(lbl)
    box.append(widget)
    return box


def _dropdown(items: list[str], selected: int = 0) -> Gtk.DropDown:
    dd = Gtk.DropDown.new_from_strings(items)
    dd.set_selected(selected)
    return dd


def _slider(lo: float, hi: float, value: float, step: float = 1,
            mark: float | None = None) -> Gtk.Scale:
    sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, step)
    sc.set_value(value)
    sc.set_hexpand(True)
    sc.set_draw_value(True)
    sc.set_value_pos(Gtk.PositionType.RIGHT)
    sc.set_digits(0)
    if mark is not None:
        sc.add_mark(mark, Gtk.PositionType.BOTTOM, None)
    return sc


def _lossy(ext: str) -> bool:
    return ext in ("jpg", "jpeg", "webp", "avif", "heic", "heif", "jxl")


def _image_formats() -> list[tuple[str, str | None]]:
    can = T.magick_writable()
    out: list[tuple[str, str | None]] = [("Mesmo formato", None)]
    for label, ext, probe in (("JPG", "jpg", "jpeg"), ("PNG", "png", "png"),
                              ("WEBP", "webp", "webp"),
                              ("AVIF", "avif", "avif")):
        if probe in can:
            out.append((label, ext))
    return out


# --------------------------------------------------------------------------
# Base: janela de vidro com Cancelar / Salvar
# --------------------------------------------------------------------------

class _EditorWindow(Gtk.Window):
    def __init__(self, app, op: Op, title: str, width: int, height: int,
                 save_label: str = "Salvar"):
        super().__init__(application=app, title=title, default_width=width,
                         default_height=height)
        self.app = app
        self.op = op
        self.closed = False
        self.tmp = Path(tempfile.mkdtemp(prefix="mexerica-ed-"))
        self.add_css_class("mexerica-glass")

        header = Gtk.HeaderBar()
        cancel = Gtk.Button(label="Cancelar")
        cancel.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel)
        self.save_btn = Gtk.Button(label=save_label, sensitive=False)
        self.save_btn.add_css_class("suggested-action")
        self.save_btn.connect("clicked", lambda *_: self.save())
        header.pack_end(self.save_btn)
        self.set_titlebar(header)

        self.status = Gtk.Label(xalign=0, wrap=True)
        self.status.add_css_class("mexerica-status")

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)
        self.connect("close-request", self._on_close)

    # subclasses
    def build(self) -> tuple[Op, list[Path]]:
        raise NotImplementedError

    def on_key(self, keyval: int, state) -> bool:
        return False

    def cleanup(self) -> None:
        pass

    # comum
    def alive(self, fn):
        """Embrulha um callback de thread: ignora se a janela já fechou."""
        return lambda res: None if self.closed else fn(res)

    def say(self, text: str, error: bool = False) -> None:
        self.status.set_text(text)
        if error:
            self.status.add_css_class("error")
        else:
            self.status.remove_css_class("error")

    def save(self) -> None:
        if not self.save_btn.get_sensitive():
            return
        try:
            op, paths = self.build()
        except ValueError as exc:
            self.say(str(exc), error=True)
            return
        self.close()
        self.app.execute(op, paths)

    def _on_key(self, _c, keyval, _code, state) -> bool:
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) or \
                (ctrl and keyval in (Gdk.KEY_s, Gdk.KEY_S)):
            self.save()
            return True
        return self.on_key(keyval, state)

    def _on_close(self, *_):
        self.closed = True
        self.cleanup()
        shutil.rmtree(self.tmp, ignore_errors=True)
        return False


# --------------------------------------------------------------------------
# Editar… / Recortar… (imagem)
# --------------------------------------------------------------------------

ASPECTS: list[tuple[str, float | str | None]] = [
    ("Livre", None), ("Original", "orig"), ("1:1", 1.0), ("4:3", 4 / 3),
    ("3:4", 3 / 4), ("3:2", 3 / 2), ("2:3", 2 / 3), ("16:9", 16 / 9),
    ("9:16", 9 / 16), ("4:5", 4 / 5),
]
MIN_CROP = 0.02          # menor recorte (fração da imagem)
GRAB = 14                # px de tolerância para pegar canto/borda
CURSORS = {"nw": "nw-resize", "ne": "ne-resize", "sw": "sw-resize",
           "se": "se-resize", "n": "n-resize", "s": "s-resize",
           "e": "e-resize", "w": "w-resize", "move": "move",
           "new": "crosshair"}
PREVIEW_PX = 1400


class ImageEditor(_EditorWindow):
    def __init__(self, app, op: Op, path: Path, crop_only: bool = False):
        verb = "Recortar" if crop_only else "Editar"
        super().__init__(app, op, f"{verb} — {path.name}", 1120, 740)
        self.path = path
        self.crop_only = crop_only
        self.edit = E.ImageEdit()
        self.crop = [0.0, 0.0, 1.0, 1.0]      # x, y, w, h (normalizado)
        self.aspect: float | str | None = None
        self.src_size: tuple[int, int] | None = None
        self.base_size: tuple[int, int] | None = None
        self.base: Path | None = None
        self.base_tex: Gdk.Texture | None = None
        self.render = _Latest(30)
        self._drag = None
        self.formats = _image_formats()

        # --- tela ---
        self.picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN,
                                   can_shrink=True, hexpand=True,
                                   vexpand=True)
        self.canvas = Gtk.DrawingArea(hexpand=True, vexpand=True)
        self.canvas.set_draw_func(self._draw)
        self.spinner = Gtk.Spinner(spinning=True, halign=Gtk.Align.CENTER,
                                   valign=Gtk.Align.CENTER,
                                   width_request=32, height_request=32)
        stage = Gtk.Overlay(child=self.picture, margin_top=18,
                            margin_bottom=18, margin_start=18,
                            margin_end=10)
        stage.add_overlay(self.canvas)
        stage.add_overlay(self.spinner)

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end", self._drag_end)
        self.canvas.add_controller(drag)
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._motion)
        self.canvas.add_controller(motion)
        dbl = Gtk.GestureClick()
        dbl.connect("pressed", self._click)
        self.canvas.add_controller(dbl)

        # --- painel ---
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                        margin_top=14, margin_bottom=14, margin_start=8,
                        margin_end=16, width_request=290)

        panel.append(_section("Recorte"))
        self.aspect_dd = _dropdown([a[0] for a in ASPECTS])
        self.aspect_dd.connect("notify::selected", self._on_aspect)
        panel.append(_row("Proporção", self.aspect_dd))
        self.crop_info = Gtk.Label(xalign=0)
        self.crop_info.add_css_class("dim-label")
        panel.append(self.crop_info)
        reset_crop = Gtk.Button(label="Sem recorte")
        reset_crop.connect("clicked", lambda *_: self._reset_crop())
        panel.append(reset_crop)

        panel.append(_section("Girar e espelhar"))
        tools = Gtk.Box(spacing=6, homogeneous=True)
        tools.add_css_class("linked")
        for icon, tip, cb in (
                ("object-rotate-left-symbolic", "Girar à esquerda (L)",
                 lambda *_: self._rotate(-90)),
                ("object-rotate-right-symbolic", "Girar à direita (R)",
                 lambda *_: self._rotate(90)),
                ("object-flip-horizontal-symbolic", "Espelhar (H)",
                 lambda *_: self._flip(horizontal=True)),
                ("object-flip-vertical-symbolic", "Virar de cabeça (V)",
                 lambda *_: self._flip(horizontal=False))):
            b = Gtk.Button(icon_name=icon, tooltip_text=tip)
            b.connect("clicked", cb)
            tools.append(b)
        panel.append(tools)

        self.adjust_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                  spacing=8)
        self.adjust_box.append(_section("Ajustes"))
        self.sliders = {}
        for key, label in (("brightness", "Brilho"),
                           ("contrast", "Contraste"),
                           ("saturation", "Saturação")):
            sc = _slider(-100, 100, 0, mark=0)
            sc.connect("value-changed", self._on_adjust, key)
            self.sliders[key] = sc
            self.adjust_box.append(Gtk.Label(label=label, xalign=0))
            self.adjust_box.append(sc)
        self.gray = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.gray.connect("notify::active", self._on_gray)
        self.adjust_box.append(_row("Preto e branco", self.gray))
        reset_adj = Gtk.Button(label="Zerar ajustes")
        reset_adj.connect("clicked", lambda *_: self._reset_adjust())
        self.adjust_box.append(reset_adj)
        panel.append(self.adjust_box)

        self.output_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                  spacing=8)
        self.output_box.append(_section("Saída"))
        self.scale = Gtk.SpinButton.new_with_range(5, 100, 5)
        self.scale.set_value(100)
        self.scale.connect("value-changed", lambda *_: self._update_info())
        self.output_box.append(_row("Escala (%)", self.scale))
        self.fmt_dd = _dropdown([f[0] for f in self.formats])
        self.fmt_dd.connect("notify::selected", lambda *_:
                            self._update_info())
        self.output_box.append(_row("Formato", self.fmt_dd))
        self.quality_lbl = Gtk.Label(label="Qualidade", xalign=0)
        self.quality = _slider(30, 100, 90)
        self.output_box.append(self.quality_lbl)
        self.output_box.append(self.quality)
        panel.append(self.output_box)
        self.out_info = Gtk.Label(xalign=0, wrap=True)
        self.out_info.add_css_class("dim-label")
        panel.append(self.out_info)
        panel.append(self.status)

        if crop_only:
            self.adjust_box.set_visible(False)
            self.output_box.set_visible(False)

        scroll = Gtk.ScrolledWindow(child=panel,
                                    hscrollbar_policy=Gtk.PolicyType.NEVER)
        body = Gtk.Box()
        body.append(stage)
        body.append(scroll)
        self.set_child(body)
        self._load()

    # --- carregamento ---------------------------------------------------
    def _load(self) -> None:
        path, base = self.path, self.tmp / "base.png"

        def work():
            size = E.image_size(path)
            subprocess.run(
                T.cmd("magick") + [
                    "-define", f"jpeg:size={PREVIEW_PX * 2}x{PREVIEW_PX * 2}",
                    f"{path}[0]", "-auto-orient", "-thumbnail",
                    f"{PREVIEW_PX}x{PREVIEW_PX}>",
                    "-define", "png:compression-level=1", str(base)],
                check=True, capture_output=True, stdin=subprocess.DEVNULL)
            return size, E.image_size(base), base.read_bytes()
        _bg(work, self.alive(self._loaded))

    def _loaded(self, res) -> None:
        self.spinner.set_visible(False)
        if isinstance(res, Exception):
            self.say(f"Não consegui abrir a imagem: {res}", error=True)
            return
        self.src_size, self.base_size, png = res
        self.base = self.tmp / "base.png"
        self.base_tex = _texture(png)
        self.picture.set_paintable(self.base_tex)
        self.save_btn.set_sensitive(True)
        self._update_info()
        self.canvas.queue_draw()

    def _rerender(self) -> None:
        if not self.base:
            return
        e = dataclasses.replace(self.edit, crop=None, scale=100, max_side=0,
                                target_kb=0, ext=None)
        args = e.args(0, 0, "png")
        if not args:
            self.render.cancel()
            self.picture.set_paintable(self.base_tex)
            return
        argv = T.cmd("magick") + [str(self.base), *args, "-define",
                                  "png:compression-level=1", "png:-"]
        self.render.request(lambda: _out(argv), self.alive(self._rendered))

    def _rendered(self, res) -> None:
        if isinstance(res, Exception):
            self.say(f"Prévia falhou: {res}", error=True)
            return
        self.picture.set_paintable(_texture(res))

    # --- geometria ------------------------------------------------------
    def _shown_size(self) -> tuple[int, int]:
        """Tamanho da imagem como aparece (já girada)."""
        w, h = self.base_size or (1, 1)
        return (h, w) if self.edit.rotate % 180 else (w, h)

    def _img_rect(self) -> tuple[float, float, float, float]:
        W, H = self.canvas.get_width(), self.canvas.get_height()
        dw, dh = self._shown_size()
        s = min(W / dw, H / dh)
        rw, rh = dw * s, dh * s
        return (W - rw) / 2, (H - rh) / 2, rw, rh

    def _ratio(self) -> float | None:
        """Proporção do recorte em unidades normalizadas (w/h)."""
        a = self.aspect
        if a is None:
            return None
        dw, dh = self._shown_size()
        if a == "orig":
            return 1.0
        return float(a) * dh / dw

    def _hit(self, x: float, y: float) -> str:
        rx, ry, rw, rh = self._img_rect()
        cx, cy, cw, ch = (rx + self.crop[0] * rw, ry + self.crop[1] * rh,
                          self.crop[2] * rw, self.crop[3] * rh)
        near_l, near_r = abs(x - cx) < GRAB, abs(x - cx - cw) < GRAB
        near_t, near_b = abs(y - cy) < GRAB, abs(y - cy - ch) < GRAB
        in_x = cx - GRAB < x < cx + cw + GRAB
        in_y = cy - GRAB < y < cy + ch + GRAB
        v = "n" if near_t and in_x else "s" if near_b and in_x else ""
        h = "w" if near_l and in_y else "e" if near_r and in_y else ""
        if v or h:
            return v + h
        # sem recorte ainda: arrastar dentro da imagem desenha um novo
        if self._crop_value() and cx < x < cx + cw and cy < y < cy + ch:
            return "move"
        return "new"

    # --- interação com o recorte ---------------------------------------
    def _motion(self, _c, x, y) -> None:
        if self.base_size and self._drag is None:
            self.canvas.set_cursor_from_name(CURSORS[self._hit(x, y)])

    def _click(self, gesture, n_press, x, y) -> None:
        if n_press == 2 and self._hit(x, y) == "move":
            self._reset_crop()

    def _drag_begin(self, _g, x, y) -> None:
        if not self.base_size:
            return
        mode = self._hit(x, y)
        start = list(self.crop)
        if mode == "new":
            rx, ry, rw, rh = self._img_rect()
            px = min(max((x - rx) / rw, 0), 1)
            py = min(max((y - ry) / rh, 0), 1)
            start = [px, py, 0.0, 0.0]
        self._drag = (mode, start)

    def _drag_update(self, _g, dx, dy) -> None:
        if not self._drag:
            return
        mode, start = self._drag
        _rx, _ry, rw, rh = self._img_rect()
        ndx, ndy = dx / rw, dy / rh
        if mode == "move":
            x = min(max(start[0] + ndx, 0), 1 - start[2])
            y = min(max(start[1] + ndy, 0), 1 - start[3])
            self.crop = [x, y, start[2], start[3]]
        else:
            if mode == "new":
                if abs(dx) < 3 and abs(dy) < 3:
                    return
                mode = ("s" if ndy >= 0 else "n") + ("e" if ndx >= 0 else "w")
            self.crop = self._resized(mode, start, ndx, ndy)
        self._update_info()
        self.canvas.queue_draw()

    def _drag_end(self, *_a) -> None:
        self._drag = None
        self.canvas.queue_draw()

    def _resized(self, mode, start, ndx, ndy) -> list[float]:
        x0, y0, w0, h0 = start
        l, t, r, b = x0, y0, x0 + w0, y0 + h0
        if "w" in mode:
            l = min(l + ndx, r - MIN_CROP)
        if "e" in mode:
            r = max(r + ndx, l + MIN_CROP)
        if "n" in mode:
            t = min(t + ndy, b - MIN_CROP)
        if "s" in mode:
            b = max(b + ndy, t + MIN_CROP)
        l, t, r, b = max(l, 0.0), max(t, 0.0), min(r, 1.0), min(b, 1.0)
        k = self._ratio()
        if not k:
            return [l, t, r - l, b - t]
        w, h = r - l, b - t
        if mode in ("n", "s"):
            w = h * k
        elif mode in ("e", "w"):
            h = w / k
        elif w / h > k:
            w = h * k
        else:
            h = w / k
        # ponto fixo: o lado/canto oposto ao que está sendo puxado
        ax = r if "w" in mode else l if "e" in mode else (l + r) / 2
        ay = b if "n" in mode else t if "s" in mode else (t + b) / 2
        avail_w = ax if "w" in mode else 1 - ax if "e" in mode \
            else 2 * min(ax, 1 - ax)
        avail_h = ay if "n" in mode else 1 - ay if "s" in mode \
            else 2 * min(ay, 1 - ay)
        f = min(1.0, avail_w / w if w else 1, avail_h / h if h else 1)
        w, h = w * f, h * f
        x = ax - w if "w" in mode else ax if "e" in mode else ax - w / 2
        y = ay - h if "n" in mode else ay if "s" in mode else ay - h / 2
        return [x, y, w, h]

    def _on_aspect(self, *_a) -> None:
        self.aspect = ASPECTS[self.aspect_dd.get_selected()][1]
        k = self._ratio()
        if k:
            # maior recorte centrado com a proporção pedida
            w, h = (1.0, 1.0 / k) if k >= 1 else (k, 1.0)
            if h > 1:
                w, h = w / h, 1.0
            if w > 1:
                w, h = 1.0, h / w
            self.crop = [(1 - w) / 2, (1 - h) / 2, w, h]
        self._update_info()
        self.canvas.queue_draw()

    def _reset_crop(self) -> None:
        self.aspect_dd.set_selected(0)
        self.crop = [0.0, 0.0, 1.0, 1.0]
        self._update_info()
        self.canvas.queue_draw()

    # --- girar / espelhar -----------------------------------------------
    # Estado canônico: girar R primeiro e depois (talvez) espelhar na
    # horizontal. Virar de cabeça = espelhar + 180°.
    def _rotate(self, deg: int) -> None:
        mirrored = self.edit.flip_h
        self.edit.rotate = (self.edit.rotate + (-deg if mirrored else deg)) \
            % 360
        x, y, w, h = self.crop
        self.crop = [1 - y - h, x, h, w] if deg > 0 else [y, 1 - x - w, h, w]
        if self.aspect not in (None, "orig"):
            self.aspect_dd.set_selected(0)
        self._changed_geometry()

    def _flip(self, horizontal: bool) -> None:
        x, y, w, h = self.crop
        self.edit.flip_h = not self.edit.flip_h
        if horizontal:
            self.crop = [1 - x - w, y, w, h]
        else:
            self.edit.rotate = (self.edit.rotate + 180) % 360
            self.crop = [x, 1 - y - h, w, h]
        self._changed_geometry()

    def _changed_geometry(self) -> None:
        self._update_info()
        self.canvas.queue_draw()
        self._rerender()

    # --- ajustes -------------------------------------------------------
    def _on_adjust(self, scale, key) -> None:
        setattr(self.edit, key, int(scale.get_value()))
        if key == "saturation" and self.gray.get_active():
            self.edit.saturation = -100
        self._rerender()

    def _on_gray(self, *_a) -> None:
        on = self.gray.get_active()
        self.sliders["saturation"].set_sensitive(not on)
        self.edit.saturation = -100 if on else \
            int(self.sliders["saturation"].get_value())
        self._rerender()

    def _reset_adjust(self) -> None:
        for sc in self.sliders.values():
            sc.set_value(0)
        self.gray.set_active(False)

    # --- informações ----------------------------------------------------
    def _crop_value(self) -> tuple[float, float, float, float] | None:
        x, y, w, h = self.crop
        if x < 1e-4 and y < 1e-4 and w > 1 - 1e-4 and h > 1 - 1e-4:
            return None
        return (x, y, w, h)

    def _out_ext(self) -> str:
        chosen = self.formats[self.fmt_dd.get_selected()][1]
        return chosen or F.full_ext(self.path)

    def _update_info(self) -> None:
        if not self.src_size:
            return
        w, h = self.src_size
        if self.edit.rotate % 180:
            w, h = h, w
        cw, ch = round(self.crop[2] * w), round(self.crop[3] * h)
        self.crop_info.set_text(
            f"{cw} × {ch} px" + ("" if self._crop_value() else " (inteira)"))
        s = self.scale.get_value() / 100
        ext = self._out_ext()
        lossy = _lossy(ext)
        self.quality.set_visible(lossy and not self.crop_only)
        self.quality_lbl.set_visible(lossy and not self.crop_only)
        self.out_info.set_text(
            f"Resultado: {max(1, round(cw * s))} × {max(1, round(ch * s))} px,"
            f" {ext.upper()}. Salvo ao lado do original, sem sobrescrever.")

    def _draw(self, _area, cr, W, H) -> None:
        if not self.base_size:
            return
        rx, ry, rw, rh = self._img_rect()
        x, y, w, h = self.crop
        cx, cy, cw, ch = rx + x * rw, ry + y * rh, w * rw, h * rh
        if self._crop_value():
            cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            cr.rectangle(rx, ry, rw, rh)
            cr.rectangle(cx, cy, cw, ch)
            cr.set_source_rgba(0, 0, 0, 0.55)
            cr.fill()
        if self._drag:
            cr.set_source_rgba(1, 1, 1, 0.35)
            cr.set_line_width(1)
            for i in (1, 2):
                cr.move_to(cx + cw * i / 3, cy)
                cr.line_to(cx + cw * i / 3, cy + ch)
                cr.move_to(cx, cy + ch * i / 3)
                cr.line_to(cx + cw, cy + ch * i / 3)
            cr.stroke()
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.set_line_width(1.5)
        cr.rectangle(cx, cy, cw, ch)
        cr.stroke()
        # cantos em L
        L = min(22, cw / 3, ch / 3)
        cr.set_line_width(4)
        for px, py, sx, sy in ((cx, cy, 1, 1), (cx + cw, cy, -1, 1),
                               (cx, cy + ch, 1, -1),
                               (cx + cw, cy + ch, -1, -1)):
            cr.move_to(px + sx * L, py)
            cr.line_to(px, py)
            cr.line_to(px, py + sy * L)
        cr.stroke()

    # --- teclado e salvar -----------------------------------------------
    def on_key(self, keyval, state) -> bool:
        if isinstance(self.get_focus(), (Gtk.Text, Gtk.SpinButton)):
            return False
        actions = {Gdk.KEY_r: lambda: self._rotate(90),
                   Gdk.KEY_l: lambda: self._rotate(-90),
                   Gdk.KEY_h: lambda: self._flip(True),
                   Gdk.KEY_v: lambda: self._flip(False),
                   Gdk.KEY_c: self._reset_crop}
        fn = actions.get(Gdk.keyval_to_lower(keyval))
        if fn and self.base_size:
            fn()
            return True
        return False

    def build(self):
        self.edit.crop = self._crop_value()
        self.edit.scale = int(self.scale.get_value())
        self.edit.quality = int(self.quality.get_value())
        self.edit.ext = self.formats[self.fmt_dd.get_selected()][1]
        if self.edit == E.ImageEdit(quality=self.edit.quality):
            raise ValueError("Nada mudou: recorte, gire ou ajuste algo.")
        only_crop = self.edit == E.ImageEdit(crop=self.edit.crop,
                                             quality=self.edit.quality)
        suffix = "-recortada" if only_crop else "-editada"
        return E.image_edit_op(self.op, self.edit, suffix), [self.path]

    def cleanup(self) -> None:
        self.render.cancel()


# --------------------------------------------------------------------------
# Tamanho… (imagens, em lote)
# --------------------------------------------------------------------------

SIZES: list[tuple[str, int, int]] = [       # rótulo, escala %, lado máximo
    ("Original", 100, 0), ("75%", 75, 0), ("50%", 50, 0), ("25%", 25, 0),
    ("Lado maior 3840", 100, 3840), ("Lado maior 2560", 100, 2560),
    ("Lado maior 1920", 100, 1920), ("Lado maior 1280", 100, 1280),
    ("Lado maior 1080", 100, 1080), ("Lado maior 800", 100, 800),
    ("Lado maior 512", 100, 512),
]
WEIGHTS: list[tuple[str, int]] = [
    ("Sem limite", 0), ("100 KB", 100), ("200 KB", 200), ("500 KB", 500),
    ("1 MB", 1000), ("2 MB", 2000), ("5 MB", 5000),
]


class ImageSizeWindow(_EditorWindow):
    def __init__(self, app, op: Op, paths: list[Path]):
        n = len(paths)
        name = paths[0].name if n == 1 else f"{n} imagens"
        super().__init__(app, op, f"Tamanho — {name}", 540, 470)
        self.paths = paths
        self.formats = _image_formats()
        self.estimate = _Latest(250)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                      margin_top=16, margin_bottom=16, margin_start=18,
                      margin_end=18)
        box.append(_section("Dimensões"))
        self.size_dd = _dropdown([s[0] for s in SIZES])
        box.append(_row("Tamanho", self.size_dd))
        box.append(_section("Arquivo"))
        self.fmt_dd = _dropdown([f[0] for f in self.formats])
        box.append(_row("Formato", self.fmt_dd))
        self.quality_lbl = Gtk.Label(label="Qualidade", xalign=0)
        self.quality = _slider(30, 100, 82)
        box.append(self.quality_lbl)
        box.append(self.quality)
        self.weight_dd = _dropdown([w[0] for w in WEIGHTS])
        box.append(_row("Peso máximo (vira JPG)", self.weight_dd))
        box.append(_section("Prévia"))
        self.result = Gtk.Label(xalign=0, wrap=True)
        self.result.add_css_class("mexerica-result")
        box.append(self.result)
        box.append(self.status)
        self.set_child(box)

        for w in (self.size_dd, self.fmt_dd, self.weight_dd):
            w.connect("notify::selected", lambda *_: self._changed())
        self.quality.connect("value-changed", lambda *_: self._changed())
        self.save_btn.set_sensitive(True)
        self._changed()

    def _edit(self) -> E.ImageEdit:
        _label, scale, side = SIZES[self.size_dd.get_selected()]
        kb = WEIGHTS[self.weight_dd.get_selected()][1]
        ext = self.formats[self.fmt_dd.get_selected()][1]
        if kb:
            ext = "jpg"
        return E.ImageEdit(scale=scale, max_side=side, target_kb=kb,
                           quality=int(self.quality.get_value()), ext=ext)

    def _changed(self) -> None:
        edit = self._edit()
        ext = edit.ext or F.full_ext(self.paths[0])
        lossy = _lossy(ext)
        self.quality.set_visible(lossy)
        self.quality_lbl.set_visible(lossy)
        self.fmt_dd.set_sensitive(not edit.target_kb)
        self.result.set_text("Calculando…")
        src = self.paths[0]
        out = self.tmp / f"prévia.{'jpg' if ext == 'jpeg' else ext}"

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
            self.result.set_text(f"Sem prévia: {res}")
            return
        before, after, (w, h), (ow, oh) = res
        pct = after * 100 / before if before else 0
        first = "" if len(self.paths) == 1 else \
            f"Primeira de {len(self.paths)}: "
        self.result.set_text(
            f"{first}{w} × {h}, {_fmt_size(before)}  →  "
            f"{ow} × {oh}, {_fmt_size(after)} ({pct:.0f}%)")

    def build(self):
        edit = self._edit()
        if edit == E.ImageEdit(quality=edit.quality) and \
                not _lossy(F.full_ext(self.paths[0])):
            raise ValueError("Nada mudou: escolha tamanho, formato ou peso.")
        return E.image_edit_op(self.op, edit, "-reduzida"), self.paths

    def cleanup(self) -> None:
        self.estimate.cancel()


# --------------------------------------------------------------------------
# Cortar… (vídeo e áudio)
# --------------------------------------------------------------------------

MIN_CLIP = 0.1


class TrimWindow(_EditorWindow):
    def __init__(self, app, op: Op, path: Path):
        self.video = F.kind_of(path) == F.VIDEO
        super().__init__(app, op, f"Cortar — {path.name}",
                         920 if self.video else 760,
                         620 if self.video else 380)
        self.path = path
        self.dur = 0.0
        self.start = 0.0
        self.end = 0.0
        self._drag = None
        self._syncing = False
        self.player: subprocess.Popen | None = None
        self._play_t0 = 0.0          # relógio monotônico no início do play
        self._play_src = 0
        self.frames = {"start": _Latest(60), "end": _Latest(60)}
        self.keyframe = _Latest(150)
        self._fast_auto = True       # o usuário ainda não mexeu no "Rápido"

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=16, margin_bottom=16, margin_start=18,
                      margin_end=18)

        if self.video:
            frames = Gtk.Box(spacing=14, homogeneous=True, vexpand=True)
            self.pics = {}
            for key, title in (("start", "Início"), ("end", "Fim")):
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                col.append(_section(title))
                pic = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN,
                                  can_shrink=True, vexpand=True)
                pic.add_css_class("mexerica-frame")
                self.pics[key] = pic
                col.append(pic)
                frames.append(col)
            box.append(frames)

        # linha do tempo: forma de onda (áudio) + seleção desenhada por cima
        self.wave = Gtk.Picture(content_fit=Gtk.ContentFit.FILL,
                                can_shrink=True)
        self.timeline = Gtk.DrawingArea(content_height=92 if not self.video
                                        else 72, hexpand=True)
        self.timeline.set_draw_func(self._draw)
        self._play_from = 0.0
        tl = Gtk.Overlay(child=self.wave)
        tl.add_overlay(self.timeline)
        tl.add_css_class("mexerica-timeline")
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end", lambda *_: setattr(self, "_drag", None))
        self.timeline.add_controller(drag)
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._motion)
        self.timeline.add_controller(motion)
        box.append(tl)

        # campos numéricos
        fields = Gtk.Box(spacing=10)
        self.spin = {}
        for key, title in (("start", "Início (s)"), ("end", "Fim (s)")):
            sp = Gtk.SpinButton.new_with_range(0, 1, 0.1)
            sp.set_digits(2)
            sp.connect("value-changed", self._on_spin, key)
            self.spin[key] = sp
            fields.append(Gtk.Label(label=title))
            fields.append(sp)
        self.len_lbl = Gtk.Label(hexpand=True, xalign=1)
        self.len_lbl.add_css_class("mexerica-result")
        fields.append(self.len_lbl)
        box.append(fields)

        opts = Gtk.Box(spacing=18)
        self.play_btn = Gtk.Button(icon_name="media-playback-start-symbolic",
                                   tooltip_text="Ouvir o trecho (espaço)",
                                   visible=T.has("ffplay"))
        self.play_btn.connect("clicked", lambda *_: self._toggle_play())
        opts.append(self.play_btn)
        self.fast = Gtk.CheckButton(label="Rápido, sem recodificar",
                                    active=True)
        self.fast.set_tooltip_text(
            "Instantâneo e sem perda. Em vídeo, o início pode recuar até o "
            "quadro-chave anterior; desmarque para corte exato.")
        self.fast.connect("toggled", self._on_fast_toggled)
        opts.append(self.fast)
        self.cut_out = Gtk.CheckButton(label="Remover o trecho (manter o resto)")
        self.cut_out.connect("toggled", lambda *_: self._check_keyframe())
        opts.append(self.cut_out)
        box.append(opts)
        box.append(self.status)
        self.set_child(box)
        self.say("Carregando…")
        self._load()

    # --- carregamento ---------------------------------------------------
    def _load(self) -> None:
        path = self.path
        _bg(lambda: E.duration(path), self.alive(self._got_duration))
        if not self.video:
            argv = T.cmd("ffmpeg") + [
                "-hide_banner", "-nostdin", "-v", "error", "-i", str(path),
                "-filter_complex",
                "aformat=channel_layouts=mono,"
                "showwavespic=s=1600x180:scale=sqrt:colors=#ffffff",
                "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-"]
            _bg(lambda: _out(argv), self.alive(self._got_wave))
        else:
            _bg(self._filmstrip, self.alive(self._got_wave))

    def _filmstrip(self) -> bytes:
        """Tira de quadros para o fundo da linha do tempo (só vídeo):
        buscas rápidas (-ss antes do -i) em paralelo, coladas lado a lado."""
        n, dur = 12, E.duration(self.path)

        def grab(i: int) -> Path | None:
            f = self.tmp / f"tira{i:02d}.jpg"
            subprocess.run(T.cmd("ffmpeg") + [
                "-hide_banner", "-nostdin", "-v", "error", "-y",
                "-ss", f"{dur * (i + 0.5) / n:.3f}", "-i", str(self.path),
                "-frames:v", "1", "-vf", "scale=-2:72", "-q:v", "5", str(f)],
                capture_output=True, stdin=subprocess.DEVNULL)
            return f if f.exists() else None
        with ThreadPoolExecutor(4) as pool:
            frames = [f for f in pool.map(grab, range(n)) if f]
        if not frames:
            raise RuntimeError("sem quadros")
        return _out(T.cmd("magick") + [*map(str, frames), "+append",
                                       "png:-"])

    def _got_duration(self, res) -> None:
        if isinstance(res, Exception):
            self.say(f"Não consegui ler a duração: {res}", error=True)
            return
        self.dur = res
        self.start, self.end = 0.0, res
        self._syncing = True
        for key in ("start", "end"):
            self.spin[key].set_range(0, res)
            self.spin[key].set_value(getattr(self, key))
        self._syncing = False
        self.save_btn.set_sensitive(True)
        self.say("Arraste as alças da linha do tempo ou digite os tempos.")
        self._changed("start")
        self._changed("end")

    def _got_wave(self, res) -> None:
        if not isinstance(res, Exception):
            self.wave.set_paintable(_texture(res))

    def _frame(self, key: str) -> None:
        if not self.video:
            return
        t = self.start if key == "start" else max(self.end - 0.05, 0)
        argv = T.cmd("ffmpeg") + [
            "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{t:.3f}",
            "-i", str(self.path), "-frames:v", "1", "-vf", "scale=640:-2",
            "-f", "image2pipe", "-c:v", "png", "-"]
        pic = self.pics[key]
        self.frames[key].request(
            lambda: _out(argv),
            self.alive(lambda r: None if isinstance(r, Exception)
                       else pic.set_paintable(_texture(r))))

    # --- tocar ----------------------------------------------------------
    # ffplay num processo à parte: o GtkMediaFile/GStreamer pode abortar o
    # processo inteiro com certos arquivos, e aqui isso derrubaria a roda.
    def _toggle_play(self) -> None:
        if self.player:
            self._stop()
            return
        if not self.dur:
            return
        self.player = subprocess.Popen(
            T.cmd("ffplay") + ["-nodisp", "-autoexit", "-loglevel", "quiet",
                               "-ss", f"{self.start:.3f}",
                               "-t", f"{self.end - self.start:.3f}",
                               str(self.path)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        self._play_t0 = GLib.get_monotonic_time() / 1e6
        self._play_from = self.start
        self.play_btn.set_icon_name("media-playback-stop-symbolic")
        self._play_src = GLib.timeout_add(40, self._play_tick)

    def _playhead(self) -> float | None:
        if not self.player:
            return None
        return self._play_from + GLib.get_monotonic_time() / 1e6 \
            - self._play_t0

    def _play_tick(self):
        if self.closed or not self.player or \
                self.player.poll() is not None:
            self._play_src = 0
            self._stop()
            return GLib.SOURCE_REMOVE
        self.timeline.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _stop(self) -> None:
        if self.player:
            if self.player.poll() is None:
                self.player.terminate()
            self.player = None
        if self._play_src:
            GLib.source_remove(self._play_src)
            self._play_src = 0
        self.play_btn.set_icon_name("media-playback-start-symbolic")
        self.timeline.queue_draw()

    # --- linha do tempo -------------------------------------------------
    def _x(self, t: float) -> float:
        w = self.timeline.get_width()
        return t / self.dur * w if self.dur else 0

    def _t(self, x: float) -> float:
        w = self.timeline.get_width() or 1
        return min(max(x / w, 0), 1) * self.dur

    def _hit(self, x: float) -> str:
        xs, xe = self._x(self.start), self._x(self.end)
        if abs(x - xs) <= 10 and abs(x - xs) <= abs(x - xe):
            return "start"
        if abs(x - xe) <= 10:
            return "end"
        if xs < x < xe:
            return "move"
        return "start" if abs(x - xs) < abs(x - xe) else "end"

    def _motion(self, _c, x, _y) -> None:
        if self.dur and self._drag is None:
            mode = self._hit(x)
            self.timeline.set_cursor_from_name(
                "grab" if mode == "move" else "col-resize")

    def _drag_begin(self, _g, x, _y) -> None:
        if not self.dur:
            return
        mode = self._hit(x)
        if mode != "move" and abs(x - self._x(getattr(self, mode))) > 10:
            self._set(mode, self._t(x))       # clique fora: pula a alça
        self._drag = (mode, x, self.start, self.end)

    def _drag_update(self, _g, dx, _dy) -> None:
        if not self._drag:
            return
        mode, x0, s0, e0 = self._drag
        if mode == "move":
            span = e0 - s0
            s = min(max(s0 + self._t(x0 + dx) - self._t(x0), 0),
                    self.dur - span)
            self._set("start", s, also_end=s + span)
        else:
            self._set(mode, self._t(x0 + dx))

    def _set(self, key: str, t: float, also_end: float | None = None) -> None:
        if also_end is not None:
            self.start, self.end = t, also_end
            self._changed("start")
            self._changed("end")
            return
        if key == "start":
            self.start = min(max(t, 0), self.end - MIN_CLIP)
        else:
            self.end = max(min(t, self.dur), self.start + MIN_CLIP)
        self._changed(key)

    def _on_spin(self, sp, key) -> None:
        if self._syncing or not self.dur:
            return
        self._set(key, sp.get_value())

    def _changed(self, key: str) -> None:
        self._syncing = True
        self.spin[key].set_value(getattr(self, key))
        self._syncing = False
        self.len_lbl.set_text(
            f"{_fmt_time(self.start)} → {_fmt_time(self.end)}   "
            f"({_fmt_time(self.end - self.start)})")
        self.timeline.queue_draw()
        self._frame(key)
        self._check_keyframe()

    # --- corte rápido x quadro-chave ------------------------------------
    def _on_fast_toggled(self, *_a) -> None:
        if not self._syncing:
            self._fast_auto = False
        self._check_keyframe()

    def _check_keyframe(self) -> None:
        """Vídeo: o corte rápido começa no quadro-chave anterior. Se ele
        estiver longe do ponto pedido, avisa e (se o usuário não escolheu)
        passa para corte exato."""
        if not self.video or not self.dur:
            return
        t = self.end if self.cut_out.get_active() else self.start
        if t < 0.05:
            self._keyframe_result(t, 0.0)
            return
        path = self.path
        self.keyframe.request(
            lambda: E.keyframe_before(path, t),
            self.alive(lambda r: None if isinstance(r, Exception)
                       else self._keyframe_result(t, r)))

    def _keyframe_result(self, t: float, kf: float) -> None:
        gap = t - kf
        if self._fast_auto:
            self._syncing = True
            self.fast.set_active(gap <= 0.3)
            self._syncing = False
        if gap > 0.3 and self.fast.get_active():
            self.say(f"Atenção: o corte rápido vai começar em {_fmt_time(kf)}"
                     f" (quadro-chave), {gap:.1f} s antes do escolhido. "
                     "Desmarque “Rápido” para corte exato.", error=True)
        elif gap > 0.3:
            self.say(f"Corte exato (recodifica): o quadro-chave mais "
                     f"próximo está {gap:.1f} s antes.")
        else:
            self.say("Corte rápido: começa exatamente no ponto escolhido.")

    def _draw(self, _area, cr, W, H) -> None:
        if not self.dur:
            return
        xs, xe = self._x(self.start), self._x(self.end)
        cr.set_source_rgba(0, 0, 0, 0.5)          # fora da seleção
        cr.rectangle(0, 0, xs, H)
        cr.rectangle(xe, 0, W - xe, H)
        cr.fill()
        cr.set_source_rgba(1.0, 0.54, 0.12, 0.18)  # seleção (mexerica)
        cr.rectangle(xs, 0, xe - xs, H)
        cr.fill()
        cr.set_source_rgba(1.0, 0.54, 0.12, 1.0)
        cr.set_line_width(2)
        cr.rectangle(xs + 1, 1, xe - xs - 2, H - 2)
        cr.stroke()
        for x in (xs, xe):                          # alças
            cr.rectangle(x - 4, H / 2 - 14, 8, 28)
            cr.fill()
        head = self._playhead()
        if head is not None and head <= self.end:
            px = self._x(head)
            cr.set_source_rgba(1, 1, 1, 0.95)
            cr.rectangle(px - 1, 0, 2, H)
            cr.fill()

    def on_key(self, keyval, state) -> bool:
        if keyval == Gdk.KEY_space and self.play_btn.get_visible() and \
                not isinstance(self.get_focus(), (Gtk.Text, Gtk.SpinButton)):
            self._toggle_play()
            return True
        return False

    def build(self):
        s, e = self.start, self.end
        remove = self.cut_out.get_active()
        if e - s < MIN_CLIP:
            raise ValueError("Trecho curto demais.")
        whole = s < 0.05 and e > self.dur - 0.05
        if whole and not remove:
            raise ValueError("O trecho é o arquivo inteiro: mova as alças.")
        if whole and remove:
            raise ValueError("Isso removeria o arquivo inteiro.")
        return (E.trim_op(self.op, s, e, self.fast.get_active(), remove),
                [self.path])

    def cleanup(self) -> None:
        self._stop()
        for f in (*self.frames.values(), self.keyframe):
            f.cancel()


# --------------------------------------------------------------------------
# Tamanho… (vídeo, em lote)
# --------------------------------------------------------------------------

TARGETS: list[tuple[str, float]] = [
    ("Só qualidade (CRF 26)", 0), ("8 MB", 8), ("10 MB", 10), ("25 MB", 25),
    ("50 MB", 50), ("100 MB", 100), ("Outro…", -1),
]
HEIGHTS: list[tuple[str, int]] = [
    ("Original", 0), ("1080p", 1080), ("720p", 720), ("480p", 480),
    ("360p", 360),
]


class VideoSizeWindow(_EditorWindow):
    def __init__(self, app, op: Op, paths: list[Path]):
        n = len(paths)
        name = paths[0].name if n == 1 else f"{n} vídeos"
        super().__init__(app, op, f"Tamanho — {name}", 540, 380)
        self.paths = paths
        self.durs: list[float] = []

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                      margin_top=16, margin_bottom=16, margin_start=18,
                      margin_end=18)
        box.append(_section("Objetivo"))
        self.target_dd = _dropdown([t[0] for t in TARGETS], 3)
        box.append(_row("Caber em", self.target_dd))
        self.custom = Gtk.SpinButton.new_with_range(1, 4000, 1)
        self.custom.set_value(20)
        self.custom_row = _row("Tamanho (MB)", self.custom)
        self.custom_row.set_visible(False)
        box.append(self.custom_row)
        self.height_dd = _dropdown([h[0] for h in HEIGHTS])
        box.append(_row("Resolução máxima", self.height_dd))
        self.mute = Gtk.Switch(valign=Gtk.Align.CENTER)
        box.append(_row("Sem áudio", self.mute))
        box.append(_section("Estimativa"))
        self.result = Gtk.Label(xalign=0, wrap=True, label="Lendo duração…")
        self.result.add_css_class("mexerica-result")
        box.append(self.result)
        box.append(self.status)
        self.set_child(box)

        self.target_dd.connect("notify::selected", lambda *_: self._changed())
        self.height_dd.connect("notify::selected", lambda *_: self._changed())
        self.custom.connect("value-changed", lambda *_: self._changed())
        self.mute.connect("notify::active", lambda *_: self._changed())
        _bg(lambda: [E.duration(p) for p in paths],
            self.alive(self._got_durations))

    def _got_durations(self, res) -> None:
        if isinstance(res, Exception):
            self.result.set_text(f"Não li a duração: {res}")
            return
        self.durs = res
        self.save_btn.set_sensitive(True)
        self._changed()

    def _target(self) -> float:
        mb = TARGETS[self.target_dd.get_selected()][1]
        return self.custom.get_value() if mb < 0 else mb

    def _changed(self) -> None:
        self.custom_row.set_visible(
            TARGETS[self.target_dd.get_selected()][1] < 0)
        if not self.durs:
            return
        mb = self._target()
        size = sum(p.stat().st_size for p in self.paths)
        shortest = min(self.durs)
        msg = (f"{len(self.paths)} arquivo(s), {_fmt_size(size)}, "
               f"{_fmt_time(sum(self.durs))} no total.")
        if mb:
            audio = 0 if self.mute.get_active() else 96
            kbps = mb * 8192 * 0.93 / max(max(self.durs), 0.1) - audio
            msg += f"\nVídeo a ~{max(kbps, 60):.0f} kbps."
            if kbps < 350 and HEIGHTS[self.height_dd.get_selected()][1] in \
                    (0, 1080):
                msg += " Baixo para essa resolução: escolha 720p ou 480p."
        else:
            msg += f"\nMais curto: {_fmt_time(shortest)}."
        self.result.set_text(msg)

    def build(self):
        mb = self._target()
        height = HEIGHTS[self.height_dd.get_selected()][1]
        return (E.video_size_op(self.op, mb, height, self.mute.get_active()),
                self.paths)


# --------------------------------------------------------------------------
# Páginas… (PDF)
# --------------------------------------------------------------------------

THUMB_BATCH = 12


class PdfPagesWindow(_EditorWindow):
    def __init__(self, app, op: Op, path: Path):
        super().__init__(app, op, f"Páginas — {path.name}", 900, 680)
        self.path = path
        self.total = 0
        self.buttons: list[Gtk.ToggleButton] = []

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                      margin_top=12, margin_bottom=14, margin_start=16,
                      margin_end=16)
        bar = Gtk.Box(spacing=8)
        self.mode = {}
        first = None
        for key, label in (("extract", "Extrair"), ("delete", "Apagar"),
                           ("rotate", "Girar 90°")):
            rb = Gtk.CheckButton(label=label, group=first)
            first = first or rb
            self.mode[key] = rb
            bar.append(rb)
        self.mode["extract"].set_active(True)
        bar.append(Gtk.Label(label="as selecionadas", hexpand=True, xalign=0))
        for label, fn in (("Todas", lambda: self._select(lambda i: True)),
                          ("Nenhuma", lambda: self._select(lambda i: False)),
                          ("Inverter", lambda: self._select(None))):
            b = Gtk.Button(label=label)
            b.add_css_class("flat")
            b.connect("clicked", lambda _b, f=fn: f())
            bar.append(b)
        box.append(bar)

        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,
                                homogeneous=True, max_children_per_line=12,
                                min_children_per_line=2, row_spacing=10,
                                column_spacing=10, valign=Gtk.Align.START)
        scroll = Gtk.ScrolledWindow(child=self.flow, vexpand=True)
        box.append(scroll)
        self.count = Gtk.Label(xalign=0)
        self.count.add_css_class("mexerica-result")
        box.append(self.count)
        box.append(self.status)
        self.set_child(box)
        self.say("Lendo páginas…")
        _bg(lambda: E.page_count(path), self.alive(self._got_count))

    def _got_count(self, res) -> None:
        if isinstance(res, Exception):
            self.say(f"Não consegui ler o PDF: {res}", error=True)
            return
        self.total = res
        for i in range(1, res + 1):
            btn = Gtk.ToggleButton()
            btn.add_css_class("mexerica-page")
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            pic = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN,
                              can_shrink=True, width_request=120,
                              height_request=160)
            col.append(pic)
            col.append(Gtk.Label(label=str(i)))
            btn.set_child(col)
            btn.connect("toggled", lambda *_: self._update())
            self.buttons.append(btn)
            self.flow.append(btn)
        self.save_btn.set_sensitive(True)
        self.say("")
        self._update()
        self._thumbs(1)

    def _thumbs(self, first: int) -> None:
        """Miniaturas em lotes: as primeiras aparecem logo."""
        if first > self.total or self.closed:
            return
        last = min(first + THUMB_BATCH - 1, self.total)
        prefix = self.tmp / f"p{first}"

        def work():
            subprocess.run(T.cmd("pdftoppm") + [
                "-f", str(first), "-l", str(last), "-scale-to", "240",
                "-png", str(self.path), str(prefix)],
                check=True, capture_output=True, stdin=subprocess.DEVNULL)
            out = {}
            for f in self.tmp.glob(f"p{first}-*.png"):
                out[int(f.stem.rsplit("-", 1)[1])] = f.read_bytes()
            return out

        def done(res):
            if isinstance(res, Exception):
                self.say(f"Miniaturas falharam: {res}", error=True)
                return
            for page, png in res.items():
                if 1 <= page <= self.total:
                    pic = self.buttons[page - 1].get_child().get_first_child()
                    pic.set_paintable(_texture(png))
            self._thumbs(last + 1)
        _bg(work, self.alive(done))

    def _select(self, pred) -> None:
        for i, b in enumerate(self.buttons):
            b.set_active(not b.get_active() if pred is None else pred(i))

    def _selected(self) -> list[int]:
        return [i + 1 for i, b in enumerate(self.buttons) if b.get_active()]

    def _update(self) -> None:
        sel = self._selected()
        self.count.set_text(f"{len(sel)} de {self.total} página(s) "
                            "selecionada(s). Clique nas páginas para marcar.")

    def on_key(self, keyval, state) -> bool:
        if state & Gdk.ModifierType.CONTROL_MASK and \
                Gdk.keyval_to_lower(keyval) == Gdk.KEY_a:
            self._select(lambda i: True)
            return True
        return False

    def build(self):
        action = next(k for k, rb in self.mode.items() if rb.get_active())
        sel = self._selected()
        if not sel:
            raise ValueError("Selecione ao menos uma página.")
        if action == "delete" and len(sel) == self.total:
            raise ValueError("Isso apagaria todas as páginas.")
        return (E.pdf_pages_op(self.op, action, sel, self.total),
                [self.path])


# --------------------------------------------------------------------------

def open_editor(app, op: Op, paths: list[Path]) -> Gtk.Window | None:
    p = paths[0]
    win: Gtk.Window | None = None
    if op.id == "img-edit":
        win = ImageEditor(app, op, p)
    elif op.id == "img-crop":
        win = ImageEditor(app, op, p, crop_only=True)
    elif op.id == "img-size":
        win = ImageSizeWindow(app, op, paths)
    elif op.id in ("vid-trim", "aud-trim"):
        win = TrimWindow(app, op, p)
    elif op.id == "vid-size":
        win = VideoSizeWindow(app, op, paths)
    elif op.id == "pdf-pages":
        win = PdfPagesWindow(app, op, p)
    if win is None:
        log.warning("sem janela para %s", op.id)
        return None
    win.present()
    return win
