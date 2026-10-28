"""PDF: "PDF Pages" (PAGES): extrair, apagar ou girar páginas."""
from __future__ import annotations

import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from ..engine import edits as E  # noqa: E402
from ..engine import tools as T  # noqa: E402
from ..engine.ops import Op  # noqa: E402
from .base import EditorWindow, Segmented, label  # noqa: E402
from .common import bg, texture  # noqa: E402


THUMB_BATCH = 12


class PdfPagesWindow(EditorWindow):
    def __init__(self, app, op: Op, path: Path):
        super().__init__(app, op, "PDF Pages", 900, 660, primary="Save")
        self.path = path
        self.total = 0
        self.buttons: list[Gtk.ToggleButton] = []

        box = self.body
        bar = Gtk.Box(spacing=8)
        self.actions = ["extract", "delete", "rotate"]
        self.mode = Segmented(["Extract", "Delete", "Rotate 90°"])
        bar.append(self.mode)
        bar.append(label("selected pages", "mx-dim", hexpand=True))
        for text, fn in (("All", lambda: self._select(lambda i: True)),
                         ("None", lambda: self._select(lambda i: False)),
                         ("Invert", lambda: self._select(None))):
            b = Gtk.Button(label=text)
            b.add_css_class("mx-flat")
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
        self.count.add_css_class("mx-label")
        box.append(self.count)
        self.say("Reading pages…")
        bg(lambda: E.page_count(path), self.alive(self._got_count))

    def _got_count(self, res) -> None:
        if isinstance(res, Exception):
            self.say(f"Could not read the PDF: {res}", error=True)
            return
        self.total = res
        for i in range(1, res + 1):
            btn = Gtk.ToggleButton()
            btn.add_css_class("mx-page")
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
                self.say(f"Thumbnails failed: {res}", error=True)
                return
            for page, png in res.items():
                if 1 <= page <= self.total:
                    pic = self.buttons[page - 1].get_child().get_first_child()
                    pic.set_paintable(texture(png))
            self._thumbs(last + 1)
        bg(work, self.alive(done))

    def _select(self, pred) -> None:
        for i, b in enumerate(self.buttons):
            b.set_active(not b.get_active() if pred is None else pred(i))

    def _selected(self) -> list[int]:
        return [i + 1 for i, b in enumerate(self.buttons) if b.get_active()]

    def _update(self) -> None:
        sel = self._selected()
        self.count.set_text(f"{len(sel)} of {self.total} selected · "
                            "click pages to select")

    def on_key(self, keyval, state) -> bool:
        if state & Gdk.ModifierType.CONTROL_MASK and \
                Gdk.keyval_to_lower(keyval) == Gdk.KEY_a:
            self._select(lambda i: True)
            return True
        return False

    def reset(self) -> None:
        self._select(lambda i: False)
        self.mode.set_active(0)

    def build(self):
        action = self.actions[self.mode.get_active()]
        sel = self._selected()
        if not sel:
            raise ValueError("Select at least one page.")
        if action == "delete" and len(sel) == self.total:
            raise ValueError("That would delete every page.")
        return (E.pdf_pages_op(self.op, action, sel, self.total),
                [self.path])
