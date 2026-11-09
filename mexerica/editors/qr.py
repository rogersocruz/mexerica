"""QR code: de um link achado no arquivo (.url, .webloc, .txt, .md,
.html) ou colado. Sem arquivo (botão da Início), o QR vai para a pasta de
saída das Configurações ou para Downloads, com o nome do site."""
from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from .. import settings  # noqa: E402
from ..engine import edits as E  # noqa: E402
from ..engine.ops import Op  # noqa: E402
from .base import EditorWindow, Segmented, label  # noqa: E402
from .common import Latest, texture  # noqa: E402

FORMATS = ["png", "svg"]
PREVIEW_PX = 300


def default_folder() -> Path:
    folder = settings.output_dir() or Path.home() / "Downloads"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


class QrWindow(EditorWindow):
    def __init__(self, app, op: Op, path: Path | None = None):
        super().__init__(app, op, "QR Code", 520, 640, primary="Save")
        self.path = path
        self.preview = Latest()
        self.links: list[str] = []

        if path is not None:
            try:
                self.links = E.links_in(path)
            except OSError as exc:
                self.say(f"Could not read the file: {exc}", error=True)

        self.found = Gtk.DropDown.new_from_strings(self.links or [""])
        self.found.set_visible(len(self.links) > 1)
        self.found.connect("notify::selected", self._picked)
        if len(self.links) > 1:
            self.body.append(label(f"{len(self.links)} links in "
                                   f"{path.name}", "mx-dim"))
            self.body.append(self.found)

        row = Gtk.Box(spacing=6)
        self.entry = Gtk.Entry(hexpand=True,
                               placeholder_text="Paste a link or type text")
        self.entry.connect("changed", lambda *_: self._changed())
        self.entry.connect("activate", lambda *_: self.save())
        row.append(self.entry)
        paste = Gtk.Button.new_from_icon_name("edit-paste-symbolic")
        paste.set_tooltip_text("Paste (Ctrl+V)")
        paste.connect("clicked", lambda *_: self._paste(force=True))
        row.append(paste)
        self.body.append(row)

        self.pic = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN,
                               can_shrink=True, width_request=PREVIEW_PX,
                               height_request=PREVIEW_PX, vexpand=True,
                               halign=Gtk.Align.CENTER)
        self.pic.add_css_class("mx-qr")
        self.body.append(self.pic)

        fmt = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        fmt.append(label("Format"))
        self.fmt = Segmented(["PNG", "SVG"])
        fmt.append(self.fmt)
        self.body.append(fmt)

        if self.links:
            self.entry.set_text(self.links[0])
        elif path is not None:
            self.say("No links in this file: paste one", error=True)
        if not self.links:
            self._paste(force=False)
        self._changed()
        self.entry.grab_focus()

    # -- conteúdo ------------------------------------------------------------
    def _picked(self, *_a) -> None:
        i = self.found.get_selected()
        if 0 <= i < len(self.links):
            self.entry.set_text(self.links[i])

    def _paste(self, force: bool) -> None:
        """Abrindo sem link, aproveita um link copiado; o botão cola
        qualquer texto."""
        clip = Gdk.Display.get_default().get_clipboard()

        def done(cb, res):
            try:
                text = (cb.read_text_finish(res) or "").strip()
            except Exception:  # noqa: BLE001 - clipboard vazio ou imagem
                return
            if self.closed or not text:
                return
            if force or E.looks_like_link(text):
                self.entry.set_text(text)
                self.entry.set_position(-1)
        clip.read_text_async(None, done)

    def _text(self) -> str:
        return self.entry.get_text().strip()

    def _changed(self) -> None:
        text = self._text()
        self.save_btn.set_sensitive(bool(text))
        if not text:
            self.pic.set_paintable(None)
            return
        self.preview.request(lambda: E.qr_bytes(text, "png"),
                             self.alive(self._show))

    def _show(self, res) -> None:
        if isinstance(res, Exception):
            self.say(f"Can't make this QR: {res}", error=True)
            return
        self.pic.set_paintable(texture(res))
        where = f"next to {self.path.name}" if self.path else \
            f"in {default_folder().name}"
        self.say(f"Saved {where}")

    def reset(self) -> None:
        self.entry.set_text(self.links[0] if self.links else "")
        self.fmt.set_active(0)

    def cleanup(self) -> None:
        self.preview.cancel()

    def build(self):
        text = self._text()
        op = E.qr_op(self.op, text, FORMATS[self.fmt.get_active()])
        src = self.path or E.qr_anchor(text, default_folder())
        return op, [src]
