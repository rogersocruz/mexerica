"""Janela base das ferramentas: vidro laranja sem barra do sistema.

Cabeçalho próprio ("×" à esquerda, título no centro, arrastável), corpo
livre e rodapé com Reset à esquerda e a ação primária em pílula à direita.
O título real é "Mexerica — <título>": a extensão do Shell mantém essas
janelas acima das outras.

Esc fecha; Enter ou Ctrl+S executa a ação primária.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

import re  # noqa: E402

from ..engine.ops import Op  # noqa: E402
from ..i18n import _  # noqa: E402

TITLE_PREFIX = "Mexerica — "


class EditorWindow(Gtk.Window):
    def __init__(self, app, op: Op, title: str, width: int, height: int,
                 primary: str = "Aplicar", reset: bool = True):
        title = _(title)
        super().__init__(application=app, title=TITLE_PREFIX + title,
                         decorated=False, default_width=width,
                         default_height=height)
        self.app = app
        self.op = op
        self.closed = False
        self.tmp = Path(tempfile.mkdtemp(prefix="mexerica-ed-"))
        self.add_css_class("mx-window")

        close = Gtk.Button(label="×", valign=Gtk.Align.CENTER,
                           tooltip_text=_("Fechar (Esc)"))
        close.add_css_class("mx-close")
        close.connect("clicked", lambda *_: self.close())
        title_lbl = Gtk.Label(label=title, ellipsize=3)   # END
        title_lbl.add_css_class("mx-title")
        spacer = Gtk.Box(width_request=22)
        bar = Gtk.CenterBox(start_widget=close, center_widget=title_lbl,
                            end_widget=spacer)
        bar.add_css_class("mx-header")
        header = Gtk.WindowHandle(child=bar)

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                            margin_start=14, margin_end=14, margin_top=6,
                            vexpand=True)

        footer = Gtk.Box(spacing=8)
        footer.add_css_class("mx-footer")
        self.reset_btn = Gtk.Button(label=_("Restaurar"), visible=reset)
        self.reset_btn.add_css_class("mx-flat")
        self.reset_btn.connect("clicked", lambda *_: self.reset())
        footer.append(self.reset_btn)
        self.status = Gtk.Label(xalign=0, hexpand=True, wrap=True,
                                ellipsize=3, max_width_chars=60)
        self.status.add_css_class("mx-dim")
        footer.append(self.status)
        self.save_btn = Gtk.Button(label=_(primary), sensitive=False)
        self.save_btn.add_css_class("mx-primary")
        self.save_btn.connect("clicked", lambda *_: self.save())
        footer.append(self.save_btn)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.append(header)
        outer.append(self.body)
        outer.append(footer)
        self.set_child(outer)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)
        self.connect("close-request", self._on_close)

    # --- para as subclasses -----------------------------------------------
    def build(self) -> tuple[Op, list[Path]]:
        raise NotImplementedError

    def reset(self) -> None:
        pass

    def on_key(self, keyval: int, state) -> bool:
        return False

    def cleanup(self) -> None:
        pass

    # --- comum ------------------------------------------------------------
    def alive(self, fn):
        """Embrulha um callback de thread: ignora se a janela já fechou."""
        return lambda res: None if self.closed else fn(res)

    def say(self, text: str, error: bool = False) -> None:
        self.status.set_text(_(text))
        if error:
            self.status.add_css_class("mx-error")
        else:
            self.status.remove_css_class("mx-error")

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
# Controles
# --------------------------------------------------------------------------

def label(text: str, css: str = "mx-label", **kw) -> Gtk.Label:
    lbl = Gtk.Label(label=_(text), xalign=0, **kw)
    lbl.add_css_class(css)
    return lbl


def row(title: str, *widgets: Gtk.Widget, spacing: int = 8) -> Gtk.Box:
    box = Gtk.Box(spacing=spacing)
    box.append(label(title, hexpand=True))
    for w in widgets:
        box.append(w)
    return box


class Segmented(Gtk.Box):
    """Pílulas exclusivas: a ativa em laranja, as outras em branco 35%."""

    def __init__(self, options: list[str], active: int = 0, on_change=None):
        super().__init__(spacing=0, valign=Gtk.Align.CENTER)
        self.add_css_class("mx-segmented")
        self.buttons: list[Gtk.ToggleButton] = []
        self._on_change = on_change
        self._quiet = False
        first = None
        for i, text in enumerate(options):
            b = Gtk.ToggleButton(label=_(text), group=first)
            first = first or b
            b.connect("toggled", self._toggled, i)
            self.buttons.append(b)
            self.append(b)
        self.set_active(active)

    def _toggled(self, button, i) -> None:
        if button.get_active() and not self._quiet and self._on_change:
            self._on_change(i)

    def get_active(self) -> int:
        return next(i for i, b in enumerate(self.buttons) if b.get_active())

    def set_active(self, i: int, notify: bool = False) -> None:
        self._quiet = not notify
        self.buttons[i].set_active(True)
        self._quiet = False


class SliderRow(Gtk.Box):
    """Rótulo, slider e o valor em px à direita."""

    def __init__(self, title: str, lo: float, hi: float, value: float,
                 unit: str = "px", on_change=None, step: float = 1):
        super().__init__(spacing=10)
        self.unit = unit
        self.append(label(title, width_request=64))
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,
                                              lo, hi, step)
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        self.scale.set_value(value)
        self.append(self.scale)
        self.value_lbl = Gtk.Label(xalign=1)
        self.value_lbl.add_css_class("mx-value")
        self.append(self.value_lbl)
        self.scale.connect("value-changed", self._changed)
        self._on_change = on_change
        self._show()

    def _show(self) -> None:
        v = self.get()
        self.value_lbl.set_text(f"{v} {self.unit}".strip())

    def _changed(self, *_a) -> None:
        self._show()
        if self._on_change:
            self._on_change(self.get())

    def get(self) -> int:
        return int(round(self.scale.get_value()))

    def set(self, v: float) -> None:
        self.scale.set_value(v)


def spin(lo: float, hi: float, value: float, step: float = 1,
         digits: int = 0, width: int = 6) -> Gtk.SpinButton:
    sp = Gtk.SpinButton.new_with_range(lo, hi, step)
    sp.set_digits(digits)
    sp.set_value(value)
    sp.set_width_chars(width)
    sp.set_valign(Gtk.Align.CENTER)
    return sp


# paleta do seletor de cor (ColorButton)
PALETTE = ["#000000", "#404040", "#808080", "#C0C0C0", "#FFFFFF",
           "#7F1D1D", "#DC2626", "#F97316", "#F59E0B", "#FACC15",
           "#14532D", "#16A34A", "#0D9488", "#0EA5E9", "#1E3A8A",
           "#2563EB", "#7C3AED", "#C026D3", "#DB2777", "#78350F"]


def _rgb(color: str) -> tuple[float, float, float]:
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


class ColorButton(Gtk.MenuButton):
    """Botão de cor com a escolha num popover (paleta e código #RRGGBB).
    O popover faz parte da própria janela: a janela de cores do sistema
    (Gtk.ColorDialog) abria atrás das janelas de edição, que ficam acima
    de tudo. `on_change(cor)` recebe '#RRGGBB'."""

    def __init__(self, color: str, on_change, title: str = "",
                 text: str = ""):
        super().__init__(valign=Gtk.Align.CENTER)
        self.add_css_class("mx-colorbtn")
        self._color = color.upper()
        self._on_change = on_change
        self._quiet = False
        self.dot = Gtk.DrawingArea(content_width=22, content_height=22)
        self.dot.set_draw_func(self._draw_dot)
        if text:                        # cor + texto ("Outra cor")
            inner = Gtk.Box(spacing=6)
            inner.append(self.dot)
            inner.append(Gtk.Label(label=_(text)))
            self.set_child(inner)
        else:
            self.set_child(self.dot)
        if title:
            self.set_tooltip_text(_(title))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                      margin_top=8, margin_bottom=8, margin_start=8,
                      margin_end=8)
        grid = Gtk.Grid(row_spacing=6, column_spacing=6)
        for i, c in enumerate(PALETTE):
            b = Gtk.Button(tooltip_text=c)
            b.add_css_class("mx-swatch")
            area = Gtk.DrawingArea(content_width=22, content_height=22)
            area.set_draw_func(self._draw_swatch, c)
            b.set_child(area)
            b.connect("clicked", lambda _b, col=c: self._pick(col, True))
            grid.attach(b, i % 5, i // 5, 1, 1)
        box.append(grid)
        self.entry = Gtk.Entry(text=self._color, max_length=7,
                               width_chars=9, placeholder_text="#RRGGBB")
        self.entry.connect("changed", self._typed)
        self.entry.connect("activate", lambda *_: self.popdown())
        box.append(self.entry)
        self.set_popover(Gtk.Popover(child=box))

    def get_color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        self._quiet = True
        self._pick(color, False)
        self._quiet = False

    def _pick(self, color: str, close: bool) -> None:
        self._color = color.upper()
        if self.entry.get_text().upper() != self._color:
            self.entry.set_text(self._color)
        self.dot.queue_draw()
        if close:
            self.popdown()
        if not self._quiet:
            self._on_change(self._color)

    def _typed(self, entry) -> None:
        text = entry.get_text().strip()
        if not text.startswith("#"):
            text = "#" + text
        if re.fullmatch(r"#[0-9a-fA-F]{6}", text) and \
                text.upper() != self._color:
            self._pick(text, False)

    def _draw_dot(self, _a, cr, w, h) -> None:
        self._draw_swatch(_a, cr, w, h, self._color)

    @staticmethod
    def _draw_swatch(_a, cr, w, h, color) -> None:
        r = 6
        cr.new_sub_path()
        cr.arc(w - r, r, r, -1.5708, 0)
        cr.arc(w - r, h - r, r, 0, 1.5708)
        cr.arc(r, h - r, r, 1.5708, 3.1416)
        cr.arc(r, r, r, 3.1416, 4.7124)
        cr.close_path()
        cr.set_source_rgb(*_rgb(color))
        cr.fill_preserve()
        cr.set_source_rgba(0, 0, 0, 0.25)
        cr.set_line_width(1)
        cr.stroke()


def dropdown(items: list[str], selected: int = 0) -> Gtk.DropDown:
    dd = Gtk.DropDown.new_from_strings([_(i) for i in items])
    dd.set_selected(selected)
    dd.set_valign(Gtk.Align.CENTER)
    return dd
