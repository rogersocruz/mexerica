"""PDF: "PDF Pages" (extrair, apagar ou girar páginas), "Split PDF"
(partes por intervalo ou a cada N páginas) e "Merge PDFs" (juntar na
ordem escolhida)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GObject, Gtk, Pango  # noqa: E402

from ..engine import edits as E  # noqa: E402
from ..engine import formats as F  # noqa: E402
from ..engine import tools as T  # noqa: E402
from ..engine.ops import Op  # noqa: E402
from .base import EditorWindow, Segmented, label, spin  # noqa: E402
from .common import bg, fmt_size, texture  # noqa: E402


THUMB_BATCH = 12


def render_pages(path: Path, first: int, last: int, prefix: Path,
                 scale: int = 240) -> dict[int, bytes]:
    """PNGs das páginas first..last ({página: bytes})."""
    subprocess.run(T.cmd("pdftoppm") + [
        "-f", str(first), "-l", str(last), "-scale-to", str(scale),
        "-png", str(path), str(prefix)],
        check=True, capture_output=True, stdin=subprocess.DEVNULL)
    out = {}
    for f in prefix.parent.glob(f"{prefix.name}-*.png"):
        out[int(f.stem.rsplit("-", 1)[1])] = f.read_bytes()
    return out


def load_thumbs(win: EditorWindow, path: Path, total: int,
                pics: list[Gtk.Picture], first: int = 1) -> None:
    """Miniaturas em lotes: as primeiras aparecem logo."""
    if first > total or win.closed:
        return
    last = min(first + THUMB_BATCH - 1, total)

    def done(res):
        if isinstance(res, Exception):
            win.say(f"Thumbnails failed: {res}", error=True)
            return
        for page, png in res.items():
            if 1 <= page <= total:
                pics[page - 1].set_paintable(texture(png))
        load_thumbs(win, path, total, pics, last + 1)
    bg(lambda: render_pages(path, first, last, win.tmp / f"p{first}"),
       win.alive(done))


def page_tile(number: int, button: Gtk.Button) -> tuple[Gtk.Picture,
                                                         Gtk.Label]:
    """Miniatura com o número embaixo, dentro de `button`."""
    col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    pic = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN, can_shrink=True,
                      width_request=120, height_request=160)
    col.append(pic)
    caption = Gtk.Label(label=str(number))
    col.append(caption)
    button.set_child(col)
    button.add_css_class("mx-page")
    return pic, caption


def page_grid() -> tuple[Gtk.FlowBox, Gtk.ScrolledWindow]:
    flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,
                       homogeneous=True, max_children_per_line=12,
                       min_children_per_line=2, row_spacing=10,
                       column_spacing=10, valign=Gtk.Align.START)
    return flow, Gtk.ScrolledWindow(child=flow, vexpand=True)


# --------------------------------------------------------------------------
# PDF Pages
# --------------------------------------------------------------------------

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

        self.flow, scroll = page_grid()
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
        pics = []
        for i in range(1, res + 1):
            btn = Gtk.ToggleButton()
            pic, _ = page_tile(i, btn)
            pics.append(pic)
            btn.connect("toggled", lambda *_: self._update())
            self.buttons.append(btn)
            self.flow.append(btn)
        self.save_btn.set_sensitive(True)
        self.say("")
        self._update()
        load_thumbs(self, self.path, self.total, pics)

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


# --------------------------------------------------------------------------
# Split PDF
# --------------------------------------------------------------------------

RANGES, EVERY = 0, 1


class PdfSplitWindow(EditorWindow):
    """Partes por intervalo ("1-3, 4-8, 9-") ou a cada N páginas. Clicar
    numa página começa (ou desfaz) uma parte nela, como uma tesoura."""

    def __init__(self, app, op: Op, path: Path):
        super().__init__(app, op, "Split PDF", 900, 680, primary="Split")
        self.path = path
        self.total = 0
        self.tiles: list[tuple[Gtk.Button, Gtk.Label]] = []

        bar = Gtk.Box(spacing=10)
        self.mode = Segmented(["Ranges", "Every N pages"],
                              on_change=lambda _i: self._mode_changed())
        bar.append(self.mode)
        self.ranges = Gtk.Entry(hexpand=True, placeholder_text="1-3, 4-8, 9-")
        self.ranges.connect("changed", lambda *_: self._update())
        self.ranges.connect("activate", lambda *_: self.save())
        bar.append(self.ranges)
        self.every_box = Gtk.Box(spacing=8, visible=False, hexpand=True)
        self.every_box.append(label("pages per file"))
        self.n = spin(1, 9999, 1)
        self.n.connect("value-changed", lambda *_: self._update())
        self.every_box.append(self.n)
        bar.append(self.every_box)
        self.body.append(bar)

        self.flow, scroll = page_grid()
        self.body.append(scroll)
        self.count = Gtk.Label(xalign=0, wrap=True)
        self.count.add_css_class("mx-label")
        self.body.append(self.count)
        self.say("Reading pages…")
        bg(lambda: E.page_count(path), self.alive(self._got_count))

    def _got_count(self, res) -> None:
        if isinstance(res, Exception):
            self.say(f"Could not read the PDF: {res}", error=True)
            return
        self.total = res
        self.n.get_adjustment().set_upper(max(res, 1))
        pics = []
        for i in range(1, res + 1):
            btn = Gtk.Button(tooltip_text="Start a new file at this page")
            pic, caption = page_tile(i, btn)
            pics.append(pic)
            btn.connect("clicked", lambda _b, p=i: self._toggle_cut(p))
            self.tiles.append((btn, caption))
            self.flow.append(btn)
        # começa dividindo ao meio: o caso comum, e mostra como funciona
        self.ranges.set_text(E.cuts_to_text({res // 2 + 1}, res)
                             if res > 1 else "1")
        self.save_btn.set_sensitive(True)
        self.say("")
        self._update()
        load_thumbs(self, self.path, self.total, pics)

    def _mode_changed(self) -> None:
        every = self.mode.get_active() == EVERY
        self.ranges.set_visible(not every)
        self.every_box.set_visible(every)
        self._update()

    def _parts(self) -> list[list[int]]:
        if self.mode.get_active() == EVERY:
            return E.every(int(self.n.get_value()), self.total)
        return E.parse_ranges(self.ranges.get_text(), self.total)

    def _toggle_cut(self, page: int) -> None:
        if self.mode.get_active() == EVERY:
            self.mode.set_active(RANGES, notify=True)
        try:
            cuts = {part[0] for part in self._parts()}
        except ValueError:
            cuts = set()
        cuts ^= {page}
        self.ranges.set_text(E.cuts_to_text(cuts, self.total))

    def _update(self) -> None:
        if not self.total:
            return
        try:
            parts = self._parts()
        except ValueError as exc:
            self.count.set_text(str(exc))
            self.count.add_css_class("mx-error")
            self.save_btn.set_sensitive(False)
            return
        self.count.remove_css_class("mx-error")
        self.save_btn.set_sensitive(True)
        part_of: dict[int, int] = {}
        starts = set()
        for k, part in enumerate(parts, 1):
            starts.add(part[0])
            for p in part:
                part_of.setdefault(p, k)
        for i, (btn, caption) in enumerate(self.tiles, 1):
            k = part_of.get(i)
            caption.set_text(f"{i}  ·  file {k}" if i in starts else str(i))
            for css, on in (("mx-cut", i in starts and i > 1),
                            ("mx-gone", k is None)):
                (btn.add_css_class if on else btn.remove_css_class)(css)
        left = self.total - len(part_of)
        files = "1 file" if len(parts) == 1 else f"{len(parts)} files"
        self.count.set_text(
            f"{files} from {self.total} pages"
            + (f" · {left} pages left out" if left else "")
            + " · click a page to start a new file there")

    def reset(self) -> None:
        self.mode.set_active(RANGES, notify=True)
        self.ranges.set_text(E.cuts_to_text({self.total // 2 + 1},
                                            self.total))

    def build(self):
        return E.pdf_split_op(self.op, self._parts()), [self.path]


# --------------------------------------------------------------------------
# Merge PDFs
# --------------------------------------------------------------------------

class PdfMergeWindow(EditorWindow):
    """Lista na ordem da seleção; arrastar (ou Alt+↑/↓) muda a ordem."""

    def __init__(self, app, op: Op, paths: list[Path]):
        super().__init__(app, op, f"Merge {len(paths)} PDFs", 640, 640,
                         primary="Merge")
        self.original = list(paths)
        self.items = list(paths)
        self.thumbs: dict[Path, Gdk.Texture] = {}
        self.pages: dict[Path, int] = {}

        bar = Gtk.Box(spacing=8)
        bar.append(label("Drag to reorder · the top file comes first",
                         "mx-dim", hexpand=True))
        for text, tip, fn in (
                ("A–Z", "Sort by name", self._sort),
                ("Reverse", "Reverse the order", self._reverse),
                ("Selection order", "Back to the order you selected",
                 self._restore)):
            b = Gtk.Button(label=text, tooltip_text=tip)
            b.add_css_class("mx-flat")
            b.connect("clicked", lambda _b, f=fn: f())
            bar.append(b)
        self.body.append(bar)

        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.list.add_css_class("mx-files")
        self.body.append(Gtk.ScrolledWindow(child=self.list, vexpand=True))
        self.count = Gtk.Label(xalign=0)
        self.count.add_css_class("mx-label")
        self.body.append(self.count)
        self.save_btn.set_sensitive(True)
        self._render()
        bg(self._load, self.alive(self._loaded))

    # -- dados -----------------------------------------------------------------
    def _load(self) -> dict[Path, tuple[int, bytes | None]]:
        out = {}
        for i, path in enumerate(dict.fromkeys(self.original)):
            try:
                n = E.page_count(path)
            except (subprocess.CalledProcessError, ValueError, OSError):
                n = 0
            png = None
            if n:
                try:
                    # pequena: o Gtk.Picture pede o tamanho natural
                    png = render_pages(path, 1, 1, self.tmp / f"m{i}",
                                       scale=60).get(1)
                except (subprocess.CalledProcessError, OSError):
                    pass
            out[path] = (n, png)
        return out

    def _loaded(self, res) -> None:
        if isinstance(res, Exception):
            self.say(f"Could not read the PDFs: {res}", error=True)
            return
        for path, (n, png) in res.items():
            self.pages[path] = n
            if png:
                self.thumbs[path] = texture(png)
        self._render()

    # -- lista -------------------------------------------------------------------
    def _render(self, select: int | None = None) -> None:
        while (child := self.list.get_first_child()) is not None:
            self.list.remove(child)
        for i, path in enumerate(self.items):
            self.list.append(self._row(i, path))
        if select is not None and 0 <= select < len(self.items):
            row = self.list.get_row_at_index(select)
            self.list.select_row(row)
            row.grab_focus()
        known = [self.pages[p] for p in self.items if p in self.pages]
        bad = [p.name for p in self.items if self.pages.get(p) == 0]
        text = f"{len(self.items)} files"
        if len(known) == len(self.items):
            text += f" · {sum(known)} pages"
        if bad:
            text += f" · can't read {', '.join(bad)}"
        self.count.set_text(text)

    def _row(self, i: int, path: Path) -> Gtk.ListBoxRow:
        box = Gtk.Box(spacing=10, margin_top=4, margin_bottom=4,
                      margin_start=6, margin_end=6)
        grip = Gtk.Image.new_from_icon_name("list-drag-handle-symbolic")
        grip.add_css_class("mx-dim")
        grip.set_tooltip_text("Drag to reorder")
        box.append(grip)
        box.append(label(f"{i + 1}.", "mx-value", width_chars=3))
        pic = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN,
                          can_shrink=True, width_request=44,
                          height_request=58)
        if path in self.thumbs:
            pic.set_paintable(self.thumbs[path])
        box.append(pic)
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                        valign=Gtk.Align.CENTER, hexpand=True)
        name = label(path.name, ellipsize=Pango.EllipsizeMode.MIDDLE)
        name.set_tooltip_text(str(path))
        texts.append(name)
        info = []
        if path in self.pages:
            n = self.pages[path]
            info.append("unreadable" if n == 0 else
                        "1 page" if n == 1 else f"{n} pages")
        try:
            info.append(fmt_size(path.stat().st_size))
        except OSError:
            pass
        texts.append(label(" · ".join(info), "mx-dim"))
        box.append(texts)
        for icon, tip, delta in (("go-up-symbolic", "Move up (Alt+↑)", -1),
                                 ("go-down-symbolic", "Move down (Alt+↓)",
                                  1)):
            b = Gtk.Button.new_from_icon_name(icon)
            b.set_tooltip_text(tip)
            b.add_css_class("mx-flat")
            b.set_valign(Gtk.Align.CENTER)
            b.set_sensitive(0 <= i + delta < len(self.items))
            b.connect("clicked", lambda _b, d=delta, k=i: self._move(k, k + d))
            box.append(b)
        rm = Gtk.Button.new_from_icon_name("window-close-symbolic")
        rm.set_tooltip_text("Leave this file out (Delete)")
        rm.add_css_class("mx-flat")
        rm.set_valign(Gtk.Align.CENTER)
        rm.connect("clicked", lambda _b, k=i: self._remove(k))
        box.append(rm)

        row = Gtk.ListBoxRow(child=box)
        row.index = i
        drag = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
        drag.connect("prepare", lambda _s, _x, _y, k=i:
                     Gdk.ContentProvider.new_for_value(str(k)))
        drag.connect("drag-begin", lambda s, _d, r=row: s.set_icon(
            Gtk.WidgetPaintable.new(r), 20, 20))
        row.add_controller(drag)
        drop = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop.connect("enter", lambda *_a, r=row: (
            r.add_css_class("mx-over"), Gdk.DragAction.MOVE)[1])
        drop.connect("leave", lambda *_a, r=row: r.remove_css_class("mx-over"))
        drop.connect("drop", lambda _t, value, _x, _y, k=i:
                     self._dropped(value, k))
        row.add_controller(drop)
        return row

    def _dropped(self, value, to: int) -> bool:
        try:
            frm = int(value)
        except (TypeError, ValueError):
            return False
        self._move(frm, to)
        return True

    def _move(self, frm: int, to: int) -> None:
        if frm == to or not (0 <= frm < len(self.items)) \
                or not (0 <= to < len(self.items)):
            return
        self.items.insert(to, self.items.pop(frm))
        self._render(select=to)

    def _remove(self, i: int) -> None:
        if len(self.items) <= 2:
            self.say("Merging needs at least two files.", error=True)
            return
        del self.items[i]
        self.say("")
        self._render(select=min(i, len(self.items) - 1))

    def _sort(self) -> None:
        self.items.sort(key=lambda p: F.stem(p).casefold())
        self._render()

    def _reverse(self) -> None:
        self.items.reverse()
        self._render()

    def _restore(self) -> None:
        self.items = list(self.original)
        self.say("")
        self._render()

    def _selected(self) -> int | None:
        row = self.list.get_selected_row()
        return row.get_index() if row is not None else None

    def on_key(self, keyval, state) -> bool:
        i = self._selected()
        if i is None:
            return False
        if state & Gdk.ModifierType.ALT_MASK and \
                keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
            self._move(i, i + (-1 if keyval == Gdk.KEY_Up else 1))
            return True
        if keyval == Gdk.KEY_Delete:
            self._remove(i)
            return True
        return False

    def reset(self) -> None:
        self._restore()

    def build(self):
        if len(self.items) < 2:
            raise ValueError("Merging needs at least two files.")
        if any(self.pages.get(p) == 0 for p in self.items):
            raise ValueError("Leave out the files that can't be read.")
        return E.pdf_merge_op(self.op), list(self.items)
