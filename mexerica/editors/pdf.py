"""PDF: o organizador de páginas (Juntar e Páginas…), Dividir… e
Desbloquear….

O organizador mostra as páginas de um ou mais PDFs numa grade: arrastar
reordena (uma página ou as selecionadas), ↺/↻ giram, ✕ apaga, Inverter
inverte a ordem. Ctrl+Z desfaz. O resultado é um PDF só, montado pelo qpdf
(engine/edits.py, pdf_organize_op).
"""
from __future__ import annotations

import io
import math
import subprocess
import sys
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GObject, Gtk, Pango  # noqa: E402

from .. import theme as TH  # noqa: E402
from ..engine import edits as E  # noqa: E402
from ..engine import tools as T  # noqa: E402
from ..engine.ops import Op  # noqa: E402
from ..i18n import N_, _, plural  # noqa: E402
from .base import EditorWindow, Segmented, label, spin  # noqa: E402
from .common import bg, texture  # noqa: E402


THUMB_BATCH = 12
UNDO_LIMIT = 60
# uma cor por arquivo no Juntar (faixa embaixo da miniatura)
FILE_COLORS = [(0.95, 0.55, 0.18), (0.24, 0.52, 0.89), (0.30, 0.69, 0.38),
               (0.80, 0.33, 0.62), (0.55, 0.42, 0.85), (0.15, 0.67, 0.70),
               (0.85, 0.30, 0.25), (0.60, 0.60, 0.20)]


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
            win.say(_("As miniaturas falharam: {err}").format(err=res),
                    error=True)
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


def live_order(items: list, moving: list, target) -> list:
    """A ordem com o bloco `moving` no lugar de `target` (o arraste ao
    vivo). Alvo depois do bloco: o bloco entra depois dele; antes: antes.
    Depois da troca o ponteiro fica sobre o próprio bloco, então a ordem
    não fica pulando de um lado para o outro."""
    if not moving or any(target is m for m in moving):
        return items
    ids = {id(m) for m in moving}
    block = [it for it in items if id(it) in ids]
    rest = [it for it in items if id(it) not in ids]
    first = next(i for i, it in enumerate(items) if id(it) in ids)
    after = items.index(target) > first
    at = rest.index(target) + (1 if after else 0)
    return rest[:at] + block + rest[at:]


def read_pdfs(paths: list[Path]) -> list[tuple[Path, int, str]]:
    """(caminho, páginas, estado) de cada PDF; estado 'ok', 'locked' (pede
    senha) ou 'bad' (não abre). Lento: numa thread."""
    out = []
    for path in paths:
        try:
            out.append((path, E.page_count(path), "ok"))
        except (subprocess.CalledProcessError, ValueError, OSError):
            try:
                state = "locked" if E.needs_password(path) else "bad"
            except OSError:
                state = "bad"
            out.append((path, 0, state))
    return out


# --------------------------------------------------------------------------
# Organizador de páginas
# --------------------------------------------------------------------------

class _Page:
    """Uma página na grade. `uid` não muda (é o que o arraste carrega)."""
    __slots__ = ("uid", "src", "page", "rotate", "child", "area", "caption")

    def __init__(self, uid: int, src: int, page: int):
        self.uid, self.src, self.page, self.rotate = uid, src, page, 0
        self.child = self.area = self.caption = None


class PageOrganizer(Gtk.Box):
    """Grade de páginas de `srcs` [(caminho, nº de páginas)], na ordem dada.
    `on_change()` avisa a janela (contagem, botão salvar)."""

    def __init__(self, win: EditorWindow, srcs: list[tuple[Path, int]],
                 on_change):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                         vexpand=True)
        self.win = win
        self.srcs = [p for p, _n in srcs]
        self.multi = len(srcs) > 1
        self.on_change = on_change
        self.thumbs: dict[tuple[int, int], cairo.ImageSurface] = {}
        self.items: list[_Page] = []
        uid = 0
        for s, (_path, n) in enumerate(srcs):
            for page in range(1, n + 1):
                self.items.append(_Page(uid, s, page))
                uid += 1
        self.all = list(self.items)
        self.by_uid = {it.uid: it for it in self.items}
        self.undo: list[list[tuple[_Page, int]]] = []
        self._dragging: list[_Page] = []
        self._origin: list[_Page] | None = None    # ordem antes do arraste
        self._dropped_ok = False

        bar = Gtk.Box(spacing=6)
        bar.append(label("Arraste para reordenar · clique, Ctrl+clique ou "
                         "Shift+clique para selecionar", "mx-dim",
                         hexpand=True,
                         ellipsize=Pango.EllipsizeMode.END))
        for icon, tip, fn in (
                ("object-rotate-left-symbolic", N_("Girar à esquerda (Shift+R)"),
                 lambda: self.rotate(-90)),
                ("object-rotate-right-symbolic", N_("Girar à direita (R)"),
                 lambda: self.rotate(90)),
                ("view-sort-descending-symbolic",
                 N_("Inverter a ordem (das selecionadas, ou de todas)"),
                 self.reverse),
                ("user-trash-symbolic", N_("Apagar as selecionadas (Delete)"),
                 self.delete),
                ("edit-undo-symbolic", N_("Desfazer (Ctrl+Z)"), self.undo_last)):
            b = Gtk.Button.new_from_icon_name(icon)
            b.set_tooltip_text(_(tip))
            b.add_css_class("mx-flat")
            b.connect("clicked", lambda _b, f=fn: f())
            bar.append(b)
        for text, fn in ((N_("Todas"), self.select_all),
                         (N_("Nenhuma"), lambda: self.flow.unselect_all())):
            b = Gtk.Button(label=_(text))
            b.add_css_class("mx-flat")
            b.connect("clicked", lambda _b, f=fn: f())
            bar.append(b)
        self.append(bar)

        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.MULTIPLE,
                                homogeneous=True, max_children_per_line=12,
                                min_children_per_line=2, row_spacing=10,
                                column_spacing=10, valign=Gtk.Align.START,
                                activate_on_single_click=False)
        self.flow.add_css_class("mx-pages")
        self.flow.connect("selected-children-changed",
                          lambda *_: self.on_change())
        drop = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop.connect("motion", lambda _t, x, y: self._drag_motion(x, y))
        drop.connect("drop", lambda *_a: self._drag_drop())
        self.flow.add_controller(drop)
        self.scroll = Gtk.ScrolledWindow(child=self.flow, vexpand=True)
        self.append(self.scroll)
        for it in self.items:
            self._make_tile(it)
        self._relayout()
        self._load_next(0, 1)

    # -- miniaturas ----------------------------------------------------------
    def _load_next(self, src: int, first: int) -> None:
        """Lotes de miniaturas, arquivo por arquivo."""
        while src < len(self.srcs):
            total = sum(1 for it in self.all if it.src == src)
            if first <= total:
                break
            src, first = src + 1, 1
        else:
            return
        if self.win.closed:
            return
        last = min(first + THUMB_BATCH - 1, total)
        path = self.srcs[src]

        def done(res):
            if isinstance(res, Exception):
                self.win.say(_("As miniaturas falharam: {err}").format(err=res),
                    error=True)
                return
            for page, png in res.items():
                try:
                    self.thumbs[(src, page)] = \
                        cairo.ImageSurface.create_from_png(io.BytesIO(png))
                except (cairo.Error, MemoryError):
                    continue
            for it in self.all:
                if it.src == src and first <= it.page <= last:
                    it.area.queue_draw()
            self._load_next(src, last + 1)
        bg(lambda: render_pages(path, first, last,
                                self.win.tmp / f"s{src}p{first}"),
           self.win.alive(done))

    def _draw(self, _area, cr, w, h, it: _Page) -> None:
        strip = 5 if self.multi else 0
        ph = h - strip - 2
        img = self.thumbs.get((it.src, it.page))
        rot = it.rotate % 360
        if img is None:
            iw, ih = 85.0, 110.0
        else:
            iw, ih = float(img.get_width()), float(img.get_height())
        rw, rh = (ih, iw) if rot in (90, 270) else (iw, ih)
        s = min(w / rw, ph / rh)
        cr.save()
        cr.translate(w / 2, ph / 2)
        cr.rotate(math.radians(rot))
        cr.scale(s, s)
        cr.rectangle(-iw / 2, -ih / 2, iw, ih)
        if img is None:
            cr.set_source_rgba(1, 1, 1, 0.55)
            cr.fill()
        else:
            cr.set_source_rgb(1, 1, 1)
            cr.fill()
            cr.set_source_surface(img, -iw / 2, -ih / 2)
            cr.paint()
        cr.restore()
        if strip:
            cr.set_source_rgb(*FILE_COLORS[it.src % len(FILE_COLORS)])
            cr.rectangle(w * 0.15, h - strip, w * 0.7, strip)
            cr.fill()
        if rot:
            text = f"{rot}°"
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL,
                                cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(11)
            ext = cr.text_extents(text)
            bw, bh = ext.width + 10, 16
            cr.set_source_rgba(*TH._hex(TH.ORANGE, 0.95))
            cr.rectangle(4, 4, bw, bh)
            cr.fill()
            cr.set_source_rgb(1, 1, 1)
            cr.move_to(9 - ext.x_bearing, 4 + bh / 2 - ext.y_bearing
                       - ext.height / 2)
            cr.show_text(text)

    def _make_tile(self, it: _Page) -> None:
        area = Gtk.DrawingArea(content_width=120, content_height=160)
        area.set_draw_func(self._draw, it)
        caption = Gtk.Label(ellipsize=Pango.EllipsizeMode.MIDDLE,
                            max_width_chars=16)
        caption.add_css_class("mx-dim")
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col.append(area)
        col.append(caption)

        tools = Gtk.Box(spacing=2, halign=Gtk.Align.END,
                        valign=Gtk.Align.START, visible=False)
        tools.add_css_class("mx-tile-tools")
        for icon, tip, fn in (
                ("object-rotate-left-symbolic", N_("Girar à esquerda"),
                 lambda: self.rotate(-90, [it])),
                ("object-rotate-right-symbolic", N_("Girar à direita"),
                 lambda: self.rotate(90, [it])),
                ("window-close-symbolic", N_("Apagar esta página"),
                 lambda: self.delete([it]))):
            b = Gtk.Button.new_from_icon_name(icon)
            b.set_tooltip_text(_(tip))
            b.connect("clicked", lambda _b, f=fn: f())
            tools.append(b)
        over = Gtk.Overlay(child=col)
        over.add_overlay(tools)

        child = Gtk.FlowBoxChild(child=over)
        child.add_css_class("mx-tile")
        hover = Gtk.EventControllerMotion()
        hover.connect("enter", lambda *_: tools.set_visible(True))
        hover.connect("leave", lambda *_: tools.set_visible(False))
        child.add_controller(hover)

        drag = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
        drag.connect("prepare", lambda *_a: self._drag_prepare(it))
        drag.connect("drag-begin", lambda s, _d: self._drag_begin(s, area))
        drag.connect("drag-cancel", lambda *_a: self._drag_end() or False)
        drag.connect("drag-end", lambda *_a: self._drag_end())
        child.add_controller(drag)
        it.child, it.area, it.caption = child, area, caption

    # -- grade ---------------------------------------------------------------
    def _relayout(self, select: list[_Page] | None = None) -> None:
        keep = self.selected() if select is None else select
        while (c := self.flow.get_first_child()) is not None:
            self.flow.remove(c)
        for it in self.items:
            self.flow.append(it.child)
        self._captions()
        for it in keep:
            if it in self.items:
                self.flow.select_child(it.child)
        self.on_change()

    def _captions(self) -> None:
        for pos, it in enumerate(self.items, 1):
            if self.multi:
                name = self.srcs[it.src].stem
                text = _("{pos} · {name} p.{page}").format(
                    pos=pos, name=name, page=it.page)
            else:
                text = str(pos) if pos == it.page else \
                    _("{pos} (p.{page})").format(pos=pos, page=it.page)
            it.caption.set_text(text)
            it.caption.set_tooltip_text(
                _("{name}, página {page}").format(
                    name=self.srcs[it.src].name, page=it.page))
            it.area.queue_draw()

    def selected(self) -> list[_Page]:
        """As selecionadas, na ordem da grade."""
        chosen = {c for c in self.flow.get_selected_children()}
        return [it for it in self.items if it.child in chosen]

    def select_all(self) -> None:
        self.flow.select_all()

    def changed(self) -> bool:
        return [(it, it.rotate % 360) for it in self.items] != \
            [(it, 0) for it in self.all]

    def refs(self, only: list[_Page] | None = None) -> list[E.PageRef]:
        return [E.PageRef(it.src, it.page, it.rotate % 360)
                for it in (self.items if only is None else only)]

    # -- desfazer ------------------------------------------------------------
    def _remember(self) -> None:
        self.undo.append([(it, it.rotate) for it in self.items])
        del self.undo[:-UNDO_LIMIT]

    def undo_last(self) -> None:
        if not self.undo:
            return
        state = self.undo.pop()
        for it, rot in state:
            it.rotate = rot
        self.items = [it for it, _r in state]
        self._relayout()

    def restore(self) -> None:
        self._remember()
        for it in self.all:
            it.rotate = 0
        self.items = list(self.all)
        self._relayout(select=[])

    # -- ações ---------------------------------------------------------------
    def _targets(self, only) -> list[_Page]:
        return only if only is not None else self.selected()

    def rotate(self, delta: int, only: list[_Page] | None = None) -> None:
        pages = self._targets(only)
        if not pages:
            self.win.say("Selecione as páginas para girar.")
            return
        self._remember()
        for it in pages:
            it.rotate = (it.rotate + delta) % 360
            it.area.queue_draw()
        self.on_change()

    def delete(self, only: list[_Page] | None = None) -> None:
        pages = self._targets(only)
        if not pages:
            self.win.say("Selecione as páginas para apagar.")
            return
        if len(pages) >= len(self.items):
            self.win.say("Isso apagaria todas as páginas.", error=True)
            return
        self._remember()
        gone = set(id(p) for p in pages)
        self.items = [it for it in self.items if id(it) not in gone]
        self._relayout(select=[])

    def reverse(self) -> None:
        sel = self.selected()
        self._remember()
        if len(sel) >= 2:
            slots = [i for i, it in enumerate(self.items) if it in sel]
            for i, it in zip(slots, reversed(sel)):
                self.items[i] = it
        else:
            self.items.reverse()
        self._relayout()

    def move_selected(self, delta: int) -> None:
        sel = self.selected()
        if not sel:
            return
        idx = [self.items.index(it) for it in sel]
        if (delta < 0 and min(idx) == 0) or \
                (delta > 0 and max(idx) == len(self.items) - 1):
            return
        self._remember()
        rest = [it for it in self.items if it not in sel]
        at = max(0, min(len(rest), min(idx) + delta))
        self.items = rest[:at] + sel + rest[at:]
        self._relayout(select=sel)

    # -- arrastar ------------------------------------------------------------
    # Durante o arraste as outras páginas abrem espaço (a ordem muda na
    # tela); soltar confirma, cancelar (Esc, soltar fora) volta ao que era.
    def _drag_prepare(self, it: _Page):
        sel = self.selected()
        self._dragging = sel if it in sel else [it]
        self._origin = list(self.items)
        self._dropped_ok = False
        return Gdk.ContentProvider.new_for_value(str(it.uid))

    def _drag_begin(self, source, area) -> None:
        source.set_icon(Gtk.WidgetPaintable.new(area), 30, 40)
        for it in self._dragging:
            it.child.add_css_class("mx-dragging")

    def _drag_motion(self, x: float, y: float):
        if not self._dragging:
            return 0
        self._autoscroll(y)
        child = self.flow.get_child_at_pos(x, y)
        target = next((it for it in self.items if it.child is child), None)
        if target is not None:
            new = live_order(self.items, self._dragging, target)
            if new != self.items:
                self._apply_order(new)
        return Gdk.DragAction.MOVE

    def _autoscroll(self, y: float) -> None:
        """Perto da borda de cima ou de baixo, a grade rola."""
        adj = self.scroll.get_vadjustment()
        seen = y - adj.get_value()
        edge = 48
        if seen < edge:
            adj.set_value(adj.get_value() - 16)
        elif seen > adj.get_page_size() - edge:
            adj.set_value(adj.get_value() + 16)

    def _apply_order(self, new: list[_Page]) -> None:
        """Mostra `new` sem tirar da grade as miniaturas arrastadas (tirar a
        origem do arraste o cancelaria): só as outras mudam de lugar."""
        moving = {id(it) for it in self._dragging}
        for it in self.items:
            if id(it) not in moving:
                self.flow.remove(it.child)
        for pos, it in enumerate(new):
            if id(it) not in moving:
                self.flow.insert(it.child, pos)
        self.items = new
        self._captions()

    def _drag_drop(self) -> bool:
        if not self._dragging or self._origin is None:
            return False
        self._dropped_ok = True
        moved = self._dragging
        if self.items != self._origin:
            # desfazer volta para antes do arraste
            self.undo.append([(it, it.rotate) for it in self._origin])
            del self.undo[:-UNDO_LIMIT]
        self._finish_drag()
        self._relayout(select=moved)
        return True

    def _drag_end(self) -> None:
        if self._origin is not None and not self._dropped_ok:
            self._apply_order(self._origin)       # cancelado: volta
            self.on_change()
        self._finish_drag()

    def _finish_drag(self) -> None:
        for it in self._dragging:
            it.child.remove_css_class("mx-dragging")
        self._dragging = []
        self._origin = None

    # -- teclado -------------------------------------------------------------
    def on_key(self, keyval, state) -> bool:
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        alt = bool(state & Gdk.ModifierType.ALT_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        low = Gdk.keyval_to_lower(keyval)
        if ctrl and low == Gdk.KEY_a:
            self.select_all()
        elif ctrl and low == Gdk.KEY_z:
            self.undo_last()
        elif alt and keyval in (Gdk.KEY_Left, Gdk.KEY_Right, Gdk.KEY_Up,
                                Gdk.KEY_Down):
            self.move_selected(-1 if keyval in (Gdk.KEY_Left, Gdk.KEY_Up)
                               else 1)
        elif keyval in (Gdk.KEY_Delete, Gdk.KEY_BackSpace):
            self.delete()
        elif low == Gdk.KEY_r and not ctrl and not alt:
            self.rotate(-90 if shift else 90)
        else:
            return False
        return True


class _OrganizerWindow(EditorWindow):
    """Base do Juntar e do Páginas…: lê os PDFs numa thread, monta o
    organizador e mantém o rodapé."""

    def __init__(self, app, op: Op, title: str, primary: str,
                 paths: list[Path]):
        super().__init__(app, op, title, 960, 700, primary=primary)
        self.paths = list(paths)
        self.org: PageOrganizer | None = None
        self.locked: list[Path] = []
        self.holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                              vexpand=True)
        self.body.append(self.holder)
        self.count = Gtk.Label(xalign=0, wrap=True)
        self.count.add_css_class("mx-label")
        self.body.append(self.count)
        self.say("Lendo as páginas…")
        bg(lambda: self.prepare(self.paths), self.alive(self._ready))

    def prepare(self, paths: list[Path]):
        return read_pdfs(paths)

    def _ready(self, res) -> None:
        if isinstance(res, Exception):
            self.say(_("Não deu para ler os PDFs: {err}").format(err=res),
                     error=True)
            return
        good = [(p, n) for p, n, st in res if st == "ok" and n]
        self.locked = [p for p, _n, st in res if st == "locked"]
        bad = [p for p, _n, st in res if st == "bad"]
        notes = []
        if self.locked:
            notes.append(_("com senha: {names}").format(
                names=", ".join(p.name for p in self.locked)))
        if bad:
            notes.append(_("ilegíveis: {names}").format(
                names=", ".join(p.name for p in bad)))
        if self.locked:
            unlock = Gtk.Button(label=_("Desbloquear…"),
                                halign=Gtk.Align.START,
                                tooltip_text=_("Abre o DESBLOQUEAR para "
                                               "esses arquivos"))
            unlock.add_css_class("mx-flat")
            unlock.connect("clicked", lambda *_: self._open_unlock())
            self.body.insert_child_after(unlock, self.holder)
        if not good:
            self.say(_("Ficaram de fora: {list}").format(
                list="; ".join(notes)) if notes
                else "Nenhuma página para mostrar.", error=True)
            return
        self.say(_("Ficaram de fora: {list}").format(list="; ".join(notes))
                 if notes else "", error=bool(notes))
        self.org = PageOrganizer(self, good, self._update)
        self.holder.append(self.org)
        self.save_btn.set_sensitive(True)
        self._update()

    def _open_unlock(self) -> None:
        from ..engine import BY_ID
        from . import open_editor
        open_editor(self.app, BY_ID["pdf-unlock"], list(self.locked))

    def _update(self) -> None:
        if self.org is None:
            return
        n, sel = len(self.org.items), len(self.org.selected())
        files = len({it.src for it in self.org.items})
        text = (_("{n} arquivos").format(n=files) + " · "
                if self.org.multi else "") + \
            plural(n, "1 página", "{n} páginas") + " → 1 PDF"
        if sel:
            text += " · " + plural(sel, "1 selecionada", "{n} selecionadas")
        rotated = sum(1 for it in self.org.items if it.rotate % 360)
        if rotated:
            text += " · " + plural(rotated, "1 girada", "{n} giradas")
        self.count.set_text(text)

    def on_key(self, keyval, state) -> bool:
        return bool(self.org and self.org.on_key(keyval, state))

    def reset(self) -> None:
        if self.org:
            self.org.restore()


# --------------------------------------------------------------------------
# Juntar (Merge PDFs)
# --------------------------------------------------------------------------

class PdfMergeWindow(_OrganizerWindow):
    """Todas as páginas dos PDFs, na ordem em que os arquivos aparecem na
    lista do Explorer/Nautilus; reordenar, inverter, girar e apagar antes
    de juntar."""

    def __init__(self, app, op: Op, paths: list[Path]):
        super().__init__(app, op, _("Juntar {n} PDFs").format(n=len(paths)),
                         "Juntar", paths)

    def prepare(self, paths: list[Path]):
        if sys.platform == "win32":
            # o arraste do Explorer traz primeiro o arquivo clicado; a
            # ordem que vale é a da lista na tela
            from ..desktop import shellview
            # sem a janela (área de trabalho fechada, outro app): por nome
            paths = (shellview.view_order(paths)
                     or sorted(paths, key=shellview.natural_key))
        self.paths = paths
        return read_pdfs(paths)

    def build(self):
        if self.org is None:
            raise ValueError(_("Ainda lendo os PDFs."))
        used = sorted({it.src for it in self.org.items})
        if not used:
            raise ValueError(_("Não sobrou nenhuma página."))
        # só os arquivos que ainda têm páginas, renumerados
        remap = {s: i for i, s in enumerate(used)}
        refs = [E.PageRef(remap[r.src], r.page, r.rotate)
                for r in self.org.refs()]
        srcs = [self.org.srcs[s] for s in used]
        return E.pdf_organize_op(self.op, refs, suffix=" Merged"), srcs


# --------------------------------------------------------------------------
# Páginas… (PDF Pages)
# --------------------------------------------------------------------------

class PdfPagesWindow(_OrganizerWindow):
    """Um PDF: reordenar, girar e apagar páginas (Save) ou tirar as
    selecionadas para um PDF novo (Extract)."""

    def __init__(self, app, op: Op, path: Path):
        super().__init__(app, op, "Páginas do PDF", "Salvar", [path])
        self.path = path
        self._extract = False
        extract = Gtk.Button(label=_("Extrair as selecionadas"),
                             tooltip_text=_("Um PDF novo só com as páginas "
                                            "selecionadas, nesta ordem e "
                                            "rotação"))
        extract.add_css_class("mx-flat")
        extract.connect("clicked", lambda *_: self._do_extract())
        self.body.append(extract)

    def _do_extract(self) -> None:
        self._extract = True
        try:
            self.save()
        finally:
            self._extract = False

    def build(self):
        if self.org is None:
            raise ValueError(_("Ainda lendo o PDF."))
        if self._extract:
            sel = self.org.selected()
            if not sel:
                raise ValueError(_("Selecione as páginas para extrair."))
            pages = sorted(it.page for it in sel)
            label_ = "Page" if len(pages) == 1 else "Pages"
            suffix = f" {label_} " + E._ranges(pages).replace(",", " ")
            return (E.pdf_organize_op(self.op, self.org.refs(sel),
                                      suffix=suffix), [self.path])
        if not self.org.changed():
            raise ValueError(_("Nada mudou ainda: arraste, gire ou apague "
                               "páginas antes."))
        return (E.pdf_organize_op(self.op, self.org.refs(),
                                  suffix=" Edited"), [self.path])


# --------------------------------------------------------------------------
# Dividir… (Split PDF)
# --------------------------------------------------------------------------

SINGLE, ONE, RANGES, EVERY = 0, 1, 2, 3


class PdfSplitWindow(EditorWindow):
    """Página a página, um intervalo (um PDF só), vários intervalos
    ("1-3, 4-8, 9-"; clicar numa página começa uma parte nela) ou a cada N
    páginas."""

    def __init__(self, app, op: Op, path: Path):
        super().__init__(app, op, "Dividir PDF", 900, 680, primary="Dividir")
        self.path = path
        self.total = 0
        self.tiles: list[tuple[Gtk.Button, Gtk.Label]] = []
        self._next_end = False

        bar = Gtk.Box(spacing=10)
        self.mode = Segmented(["Página a página", "Um intervalo",
                               "Intervalos", "A cada N páginas"],
                              active=RANGES,
                              on_change=lambda _i: self._mode_changed())
        bar.append(self.mode)
        self.ranges = Gtk.Entry(hexpand=True, placeholder_text="1-3, 4-8, 9-")
        self.ranges.connect("changed", lambda *_: self._update())
        self.ranges.connect("activate", lambda *_: self.save())
        bar.append(self.ranges)
        self.one_box = Gtk.Box(spacing=8, visible=False, hexpand=True)
        self.one_box.append(label("de"))
        self.first = spin(1, 9999, 1)
        self.one_box.append(self.first)
        self.one_box.append(label("até"))
        self.last = spin(1, 9999, 1)
        self.one_box.append(self.last)
        for sp in (self.first, self.last):
            sp.connect("value-changed", lambda *_: self._update())
        bar.append(self.one_box)
        self.every_box = Gtk.Box(spacing=8, visible=False, hexpand=True)
        self.every_box.append(label("páginas por arquivo"))
        self.n = spin(1, 9999, 2)
        self.n.connect("value-changed", lambda *_: self._update())
        self.every_box.append(self.n)
        bar.append(self.every_box)
        self.single_lbl = label("um PDF por página", "mx-dim", hexpand=True,
                                visible=False)
        bar.append(self.single_lbl)
        self.body.append(bar)

        self.flow, scroll = page_grid()
        self.body.append(scroll)
        self.count = Gtk.Label(xalign=0, wrap=True)
        self.count.add_css_class("mx-label")
        self.body.append(self.count)
        self.say("Lendo as páginas…")
        bg(lambda: E.page_count(path), self.alive(self._got_count))

    def _got_count(self, res) -> None:
        if isinstance(res, Exception):
            self.say(_("Não deu para ler o PDF: {err}").format(err=res),
                     error=True)
            return
        self.total = res
        for sp in (self.n, self.first, self.last):
            sp.get_adjustment().set_upper(max(res, 1))
        self.last.set_value(res)
        pics = []
        for i in range(1, res + 1):
            btn = Gtk.Button(tooltip_text=_("Começar um arquivo novo nesta "
                                             "página"))
            pic, caption = page_tile(i, btn)
            pics.append(pic)
            btn.connect("clicked", lambda _b, p=i: self._clicked(p))
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
        mode = self.mode.get_active()
        self.ranges.set_visible(mode == RANGES)
        self.one_box.set_visible(mode == ONE)
        self.every_box.set_visible(mode == EVERY)
        self.single_lbl.set_visible(mode == SINGLE)
        tip = {SINGLE: "", ONE: N_("Clique: a primeira página, depois a última"),
               RANGES: N_("Começar um arquivo novo nesta página"),
               EVERY: ""}[mode]
        for btn, _c in self.tiles:
            btn.set_tooltip_text(_(tip) or None)
        self._update()

    def _parts(self) -> list[list[int]]:
        mode = self.mode.get_active()
        if mode == SINGLE:
            return E.every(1, self.total)
        if mode == EVERY:
            return E.every(int(self.n.get_value()), self.total)
        if mode == ONE:
            a, b = int(self.first.get_value()), int(self.last.get_value())
            if a > b:
                raise ValueError(_("O intervalo começa em {a}, depois de "
                                   "onde termina ({b}).").format(a=a, b=b))
            return [list(range(a, b + 1))]
        return E.parse_ranges(self.ranges.get_text(), self.total)

    def _clicked(self, page: int) -> None:
        mode = self.mode.get_active()
        if mode == ONE:
            # 1º clique: começo; 2º: fim (se vier antes, vira o começo)
            if self._next_end and page >= self.first.get_value():
                self.last.set_value(page)
                self._next_end = False
            else:
                self.first.set_value(page)
                self.last.set_value(max(page, self.last.get_value()))
                self._next_end = True
            return
        if mode != RANGES:
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
        many = len(parts) > 1
        for i, (btn, caption) in enumerate(self.tiles, 1):
            k = part_of.get(i)
            caption.set_text(_("{i}  ·  arquivo {k}").format(i=i, k=k)
                             if i in starts and many
                             else str(i))
            for css, on in (("mx-cut", i in starts and i > 1 and many),
                            ("mx-gone", k is None)):
                (btn.add_css_class if on else btn.remove_css_class)(css)
        left = self.total - len(part_of)
        files = plural(len(parts), "1 arquivo", "{n} arquivos")
        listed = ", ".join(E._ranges(p).replace(",", " ") for p in parts[:6])
        if len(parts) > 6:
            listed += ", …"
        self.count.set_text(
            f"{files}: {listed}"
            + (" · " + plural(left, "1 página fica de fora",
                              "{n} páginas ficam de fora") if left else "")
            + (" · " + _("clique numa página para começar um arquivo novo "
                         "nela") if self.mode.get_active() == RANGES
               else ""))

    def reset(self) -> None:
        self.mode.set_active(RANGES, notify=True)
        self.ranges.set_text(E.cuts_to_text({self.total // 2 + 1},
                                            self.total))

    def build(self):
        return E.pdf_split_op(self.op, self._parts()), [self.path]


# --------------------------------------------------------------------------
# Desbloquear… (Unlock PDF)
# --------------------------------------------------------------------------

class PdfUnlockWindow(EditorWindow):
    """Tira a senha de abertura (pedindo a senha) e as restrições (imprimir,
    copiar, editar) de um ou mais PDFs. A senha só vai para o qpdf, pelo
    stdin."""

    STATES = {"open": N_("sem bloqueio"), "restricted": N_("só restrições"),
              "password": N_("pede senha"), "bad": N_("ilegível")}

    def __init__(self, app, op: Op, paths: list[Path]):
        n = len(paths)
        super().__init__(app, op, _("Desbloquear PDF") if n == 1
                         else _("Desbloquear {n} PDFs").format(n=n), 520, 360,
                         primary="Desbloquear",
                         reset=False)
        self.paths = list(paths)
        self.states: dict[Path, str] = {}
        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.body.append(Gtk.ScrolledWindow(child=self.list, vexpand=True,
                                            min_content_height=120))
        self.pw_row = Gtk.Box(spacing=8, visible=False)
        self.pw_row.append(label("Senha"))
        self.password = Gtk.PasswordEntry(show_peek_icon=True, hexpand=True)
        self.password.connect("activate", lambda *_: self.save())
        self.pw_row.append(self.password)
        self.body.append(self.pw_row)
        self.body.append(label("A cópia sai sem senha e sem restrições. "
                               "O original continua como está.",
                               "mx-dim", wrap=True))
        self.say("Conferindo…")
        bg(self._check, self.alive(self._checked))

    def _check(self) -> dict[Path, str]:
        out = {}
        for p in self.paths:
            try:
                out[p] = E.pdf_lock_state(p)
            except OSError:
                out[p] = "bad"
        return out

    def _checked(self, res) -> None:
        if isinstance(res, Exception):
            self.say(_("Não deu para ler o PDF: {err}").format(err=res),
                     error=True)
            return
        self.states = res
        for p in self.paths:
            row = Gtk.Box(spacing=8)
            name = label(p.name, hexpand=True,
                         ellipsize=Pango.EllipsizeMode.MIDDLE)
            name.set_tooltip_text(str(p))
            row.append(name)
            row.append(label(self.STATES[res[p]], "mx-dim"))
            self.list.append(row)
        need = any(s == "password" for s in res.values())
        self.pw_row.set_visible(need)
        todo = [p for p in self.paths if res[p] in ("password", "restricted")]
        self.save_btn.set_sensitive(bool(todo))
        if not todo:
            self.say("Nada para desbloquear: estes PDFs não estão bloqueados.")
        else:
            self.say("")
            if need:
                self.password.grab_focus()

    def build(self):
        todo = [p for p in self.paths
                if self.states.get(p) in ("password", "restricted")]
        if not todo:
            raise ValueError(_("Estes PDFs não estão bloqueados."))
        pw = self.password.get_text()
        if any(self.states[p] == "password" for p in todo) and not pw:
            raise ValueError(_("Digite a senha para abrir o PDF."))
        return E.pdf_unlock_op(self.op, pw), todo
