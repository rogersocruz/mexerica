"""Página Início da janela da Mexerica.

Soltar (ou escolher) arquivos e escolher o que fazer com eles sem o
arraste com Shift: aparecem todas as operações que servem, inclusive as que
estão fora da roda. Embaixo, as conversões recentes, com Abrir e Mostrar
na pasta. O "Converter com a Mexerica" do menu de contexto (Explorer e
Nautilus) abre aqui com os arquivos já escolhidos.
"""
from __future__ import annotations

import time
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

from . import history  # noqa: E402
from . import theme as TH  # noqa: E402
from .engine import options_for  # noqa: E402
from .floating import icon_widget  # noqa: E402
from .settings_window import GROUPS, ICON, _hint, _page, _section  # noqa: E402

RECENT_SHOWN = 12
ROW_ICON_PX = 40
# o menu de contexto do Explorer chama a Mexerica uma vez por arquivo: o
# que chega nesse intervalo soma à seleção em vez de trocá-la
BURST_S = 2.0


class HomePage(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        self.app = app
        self.paths: list[Path] = []
        self._added_at = 0.0

        page = _page("Início",
                     "Solte arquivos aqui, ou escolha, para ver tudo o que dá "
                     "para fazer com eles. Segurar Shift enquanto arrasta "
                     "continua valendo em qualquer lugar.")
        self.append(page)

        self.zone = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                            css_classes=["mx-drop"])
        self.empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                             halign=Gtk.Align.CENTER)
        logo = Gtk.Image.new_from_file(str(ICON))
        logo.set_pixel_size(52)
        self.empty.append(logo)
        self.empty.append(Gtk.Label(label="Solte arquivos aqui",
                                    css_classes=["mx-drop-title"]))
        pick = Gtk.Button(label="Escolher arquivos…", halign=Gtk.Align.CENTER,
                          css_classes=["mx-op"])
        pick.connect("clicked", self._choose)
        self.empty.append(pick)
        self.files = Gtk.Box(spacing=14)
        self.zone.append(self.empty)
        self.zone.append(self.files)
        page.append(self.zone)

        self.ops = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.append(self.ops)

        head = Gtk.Box(margin_top=10)
        title = _section("Recentes")
        title.set_hexpand(True)
        head.append(title)
        self.clear = Gtk.Button(label="Limpar", css_classes=["flat"])
        self.clear.connect("clicked", self._clear_history)
        head.append(self.clear)
        page.append(head)
        self.recent = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.append(self.recent)

        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("enter", self._on_enter)
        drop.connect("leave", lambda *_: self.zone.remove_css_class("mx-over"))
        drop.connect("drop", self._on_drop)
        self.add_controller(drop)

        self._render()
        self.refresh_recent()

    # -- arquivos ------------------------------------------------------------
    def set_files(self, paths: list[Path], merge: bool = False) -> None:
        now = time.monotonic()
        if merge and now - self._added_at < BURST_S:
            paths = self.paths + [p for p in paths if p not in self.paths]
        self._added_at = now
        self.paths = list(paths)
        self._render()

    def _on_enter(self, *_a):
        self.zone.add_css_class("mx-over")
        return Gdk.DragAction.COPY

    def _on_drop(self, _target, value, _x, _y) -> bool:
        self.zone.remove_css_class("mx-over")
        files = value.get_files() if hasattr(value, "get_files") else []
        paths = [Path(f.get_path()) for f in files if f.get_path()]
        if paths:
            self.set_files(paths)
        return bool(paths)

    def _choose(self, *_a) -> None:
        dialog = Gtk.FileDialog(title="Escolher arquivos", modal=True)

        def done(dlg, result):
            try:
                files = dlg.open_multiple_finish(result)
            except GLib.Error:
                return                                  # cancelou
            items = (files.get_item(i) for i in range(files.get_n_items()))
            paths = [Path(f.get_path()) for f in items if f.get_path()]
            if paths:
                self.set_files(paths)
        dialog.open_multiple(self.get_root(), None, done)

    def _render(self) -> None:
        self.empty.set_visible(not self.paths)
        self.files.set_visible(bool(self.paths))
        _clear(self.files)
        _clear(self.ops)
        if not self.paths:
            return

        first, n = self.paths[0], len(self.paths)
        icon = self.app.desktop.file_icon(first, 48)
        self.files.append(icon_widget(icon, 48))
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                        valign=Gtk.Align.CENTER)
        texts.append(Gtk.Label(label=first.name if n == 1 else f"{n} arquivos",
                               xalign=0, css_classes=["mx-drop-title"],
                               ellipsize=Pango.EllipsizeMode.MIDDLE))
        size = sum(p.stat().st_size for p in self.paths if p.is_file())
        parts = [TH.human_size(size) if size else ""]
        if n > 1:
            parts.append(", ".join(p.name for p in self.paths[:3])
                         + ("…" if n > 3 else ""))
        texts.append(_hint(" · ".join(p for p in parts if p)))
        self.files.append(texts)
        other = Gtk.Button(label="Escolher outros…", valign=Gtk.Align.CENTER)
        other.connect("clicked", self._choose)
        self.files.append(other)
        drop = Gtk.Button(label="Limpar", valign=Gtk.Align.CENTER,
                          css_classes=["flat"])
        drop.connect("clicked", lambda *_: self.set_files([]))
        self.files.append(drop)

        found = False
        for group, title, keys in GROUPS:
            ops = options_for(self.paths, group, lambda _op: True)
            if not ops:
                continue
            found = True
            self.ops.append(_section(f"{title}  ·  na roda: {keys}"))
            flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,
                               column_spacing=6, row_spacing=6,
                               max_children_per_line=10)
            for op in ops:
                button = Gtk.Button(label=op.label, css_classes=["mx-op"])
                if op.hint:
                    button.set_tooltip_text(op.hint)
                button.connect("clicked", self._run, op)
                flow.append(button)
            self.ops.append(flow)
        if not found:
            self.ops.append(_hint(
                "Nada a fazer com esses arquivos. Se faltar um programa, "
                "Sobre mostra quais foram encontrados."))

    def _run(self, _button, op) -> None:
        self.app.execute(op, list(self.paths))

    # -- recentes ------------------------------------------------------------
    def refresh_recent(self) -> None:
        _clear(self.recent)
        entries = history.load()[:RECENT_SHOWN]
        self.clear.set_sensitive(bool(entries))
        if not entries:
            self.recent.append(_hint(
                "As conversões aparecem aqui, com Abrir e Mostrar na pasta."))
            return
        for entry in entries:
            self.recent.append(self._row(entry))

    def _row(self, entry: dict) -> Gtk.Box:
        outs = [Path(p) for p in entry["outputs"]]
        there = [p for p in outs if p.exists()]
        row = Gtk.Box(spacing=12, css_classes=["mx-recent"])
        if not there:
            row.add_css_class("mx-gone")
        icon = self.app.desktop.file_icon(there[0], ROW_ICON_PX) \
            if there else None
        row.append(icon_widget(icon, ROW_ICON_PX))
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                        valign=Gtk.Align.CENTER)
        name = outs[0].name
        if len(outs) > 1:
            name += f" e mais {len(outs) - 1}"
        texts.append(Gtk.Label(label=name, xalign=0,
                               ellipsize=Pango.EllipsizeMode.MIDDLE))
        folder = outs[0].parent
        parts = [entry.get("label", ""), history.when_text(entry),
                 folder.name or str(folder)]
        if not there:
            parts.append("não está mais lá")
        texts.append(_hint(" · ".join(p for p in parts if p)))
        texts.set_tooltip_text(_short(folder))
        row.append(texts)
        uris = [Gio.File.new_for_path(str(p)).get_uri() for p in there]
        for label, action in (
                ("Abrir", lambda *_: self.app.open_files(uris[:1])),
                ("Mostrar na pasta", lambda *_: self.app.reveal(uris))):
            button = Gtk.Button(label=label, valign=Gtk.Align.CENTER,
                                sensitive=bool(there))
            button.connect("clicked", action)
            row.append(button)
        return row

    def _clear_history(self, *_a) -> None:
        history.clear()
        self.refresh_recent()


def _clear(box: Gtk.Box) -> None:
    while (child := box.get_first_child()) is not None:
        box.remove(child)


def _short(path: Path) -> str:
    home = str(Path.home())
    s = str(path)
    return "~" + s[len(home):] if s.startswith(home) else s
