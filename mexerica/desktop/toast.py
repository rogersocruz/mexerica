"""Notificações do serviço no Windows.

O GLib não tem backend de notificação no Windows: lá o Gio.Notification
simplesmente não aparece. O toast é uma janelinha no vidro das janelas de
edição, no canto da tela, com os mesmos botões ("Mostrar na pasta",
"Abrir") ligados às mesmas ações do app. Clicar fora dos botões dispara a
ação padrão, como clicar numa notificação do GNOME.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

TOAST_TITLE = "mexerica-toast"
TOAST_MS = 6000            # some sozinho; o de progresso fica até ser trocado
TOAST_WIDTH = 340


class Toast(Gtk.Window):
    def __init__(self, app):
        super().__init__(application=app, title=TOAST_TITLE,
                         decorated=False, resizable=False,
                         default_width=TOAST_WIDTH)
        self.app = app
        self.add_css_class("mx-window")
        self._timer = 0
        self._default = None

        self.title_lbl = Gtk.Label(xalign=0, hexpand=True, wrap=True,
                                   max_width_chars=34)
        self.title_lbl.add_css_class("mx-title")
        close = Gtk.Button(label="×", valign=Gtk.Align.START,
                           tooltip_text="Close")
        close.add_css_class("mx-close")
        close.connect("clicked", lambda *_: self.close())
        head = Gtk.Box(spacing=8)
        head.append(self.title_lbl)
        head.append(close)

        self.body_lbl = Gtk.Label(xalign=0, wrap=True, max_width_chars=40)
        self.body_lbl.add_css_class("mx-dim")
        self.buttons = Gtk.Box(spacing=6, halign=Gtk.Align.END)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                      margin_top=12, margin_bottom=10, margin_start=14,
                      margin_end=10)
        box.append(head)
        box.append(self.body_lbl)
        box.append(self.buttons)
        click = Gtk.GestureClick()
        click.connect("released", lambda *_: self._activate(self._default))
        box.add_controller(click)
        self.set_child(box)
        self.connect("close-request", self._on_close)

    def update(self, title: str, body: str, buttons, default,
               sticky: bool) -> None:
        self.title_lbl.set_text(title)
        self.body_lbl.set_text(body)
        self.body_lbl.set_visible(bool(body))
        while (child := self.buttons.get_first_child()) is not None:
            self.buttons.remove(child)
        for i, (label, action, target) in enumerate(buttons):
            btn = Gtk.Button(label=label)
            btn.add_css_class("mx-primary" if i == len(buttons) - 1
                              else "mx-flat")
            btn.connect("clicked", lambda _b, a=(action, target):
                        self._activate(a))
            self.buttons.append(btn)
        self.buttons.set_visible(bool(buttons))
        self._default = default
        self._stop_timer()
        if not sticky:
            self._timer = GLib.timeout_add(TOAST_MS, self._expire)

    def _activate(self, action) -> None:
        if action is None:
            return
        name, target = action
        param = GLib.Variant("as", target) if target is not None else None
        self.app.activate_action(name.removeprefix("app."), param)
        self.close()

    def _expire(self):
        self._timer = 0
        self.close()
        return GLib.SOURCE_REMOVE

    def _stop_timer(self) -> None:
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0

    def _on_close(self, *_):
        self._stop_timer()
        return False
