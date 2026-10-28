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

from ..engine.ops import Op  # noqa: E402

TITLE_PREFIX = "Mexerica — "


class EditorWindow(Gtk.Window):
    def __init__(self, app, op: Op, title: str, width: int, height: int,
                 primary: str = "Apply", reset: bool = True):
        super().__init__(application=app, title=TITLE_PREFIX + title,
                         decorated=False, default_width=width,
                         default_height=height)
        self.app = app
        self.op = op
        self.closed = False
        self.tmp = Path(tempfile.mkdtemp(prefix="mexerica-ed-"))
        self.add_css_class("mx-window")

        close = Gtk.Button(label="×", valign=Gtk.Align.CENTER,
                           tooltip_text="Close (Esc)")
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
        self.reset_btn = Gtk.Button(label="Reset", visible=reset)
        self.reset_btn.add_css_class("mx-flat")
        self.reset_btn.connect("clicked", lambda *_: self.reset())
        footer.append(self.reset_btn)
        self.status = Gtk.Label(xalign=0, hexpand=True, wrap=True,
                                ellipsize=3, max_width_chars=60)
        self.status.add_css_class("mx-dim")
        footer.append(self.status)
        self.save_btn = Gtk.Button(label=primary, sensitive=False)
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
        self.status.set_text(text)
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
    lbl = Gtk.Label(label=text, xalign=0, **kw)
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
            b = Gtk.ToggleButton(label=text, group=first)
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


def dropdown(items: list[str], selected: int = 0) -> Gtk.DropDown:
    dd = Gtk.DropDown.new_from_strings(items)
    dd.set_selected(selected)
    dd.set_valign(Gtk.Align.CENTER)
    return dd
