"""A janela da Mexerica: Início (home.py), aparência, itens das rodas,
comportamento e sobre.

Abre pelo menu de apps, pelo ícone da bandeja (Windows) ou da barra
superior (GNOME) e pelo "Converter com a Mexerica" do menu de contexto.
Toda mudança vale na hora e fica gravada (settings.py): não há botão de
salvar.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from . import __version__, cache_dir, settings  # noqa: E402
from . import theme as TH  # noqa: E402
from .engine import ACTIONS, CONVERT, TOOLS  # noqa: E402
from .engine import formats as F  # noqa: E402
from .engine import office  # noqa: E402
from .engine import tools as T  # noqa: E402
from .engine.ops import ALL_OPS, Op  # noqa: E402
from .wheel.geometry import Wheel  # noqa: E402
from .wheel.render import WheelState, draw  # noqa: E402

ICON = Path(__file__).with_name("data") / "icon.png"
GROUPS = [(CONVERT, "Converter", "Shift"),
          (TOOLS, "Ferramentas", "Shift + Alt"),
          (ACTIONS, "Ações", "Shift + Ctrl")]
SECTIONS = [(F.IMAGE, "Imagens"), (F.VECTOR, "SVG"), (F.VIDEO, "Vídeo"),
            (F.AUDIO, "Áudio"), (F.PDF, "PDF"), (F.DATA, "Dados"),
            (F.FONT, "Fontes"), (F.DOC_TEXT, "Documentos"),
            (F.DOC_SHEET, "Planilhas"), (F.DOC_SLIDES, "Apresentações"),
            (F.TEXT, "Texto e Markdown"), (F.EBOOK, "E-book"),
            (F.SUBTITLE, "Legendas"), (F.XOPP, "Xournal++")]
SIZES = [("small", "Pequena"), ("medium", "Média"), ("large", "Grande")]
PREVIEW = ["JPG", "PNG", "WEBP", "HEIC", "PDF", "GIF", "AVIF", "TIFF"]
GESTURES = [("Shift", "Converter: formatos de saída para o arquivo"),
            ("Shift + Alt", "Ferramentas: editar, recortar, comprimir…"),
            ("Shift + Ctrl", "Ações: copiar caminho, terminal, flutuar…"),
            ("Soltar no miolo", "Cancela"),
            ("Soltar o Shift", "A roda some e o arraste segue normal")]


def section_of(op: Op) -> str:
    """Em que grupo de tipo o item aparece na lista de itens."""
    kinds = op.kinds
    if len(kinds) >= 5:
        return "Qualquer arquivo"
    if F.ARCHIVE in kinds:
        return "Compactados e pastas"
    if len(kinds) >= 3:
        return "Vários tipos"
    if F.AUDIO in kinds:
        return "Áudio"                 # inclui o áudio extraído de vídeos
    return next((name for kind, name in SECTIONS if kind in kinds), "Outros")


class SettingsWindow(Gtk.Window):
    def __init__(self, app):
        from .home import HomePage          # home.py usa as peças daqui
        super().__init__(application=app, title="Mexerica",
                         default_width=900, default_height=660)
        self.app = app
        self.add_css_class("mx-settings")
        self._quiet = False
        self._chips: list[tuple[Gtk.ToggleButton, Op]] = []
        self.set_titlebar(Gtk.HeaderBar())

        self.home = HomePage(app)
        self.stack = stack = Gtk.Stack(
            hexpand=True, transition_type=Gtk.StackTransitionType.CROSSFADE)
        for name, title, page in (
                ("home", "Início", self.home),
                ("look", "Aparência", self._look()),
                ("items", "Itens da roda", self._items()),
                ("behavior", "Comportamento", self._behavior()),
                ("about", "Sobre", self._about())):
            stack.add_titled(_scroll(page), name, title)
        side = Gtk.StackSidebar(stack=stack, width_request=190)
        body = Gtk.Box()
        body.append(side)
        body.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        body.append(stack)
        self.set_child(body)

    def _set(self, **changes) -> None:
        settings.update(**changes)
        self.app.apply_settings()
        self.preview.queue_draw()

    # -- Aparência -----------------------------------------------------------
    def _look(self) -> Gtk.Box:
        cfg = settings.get()
        page = _page("Aparência",
                     "O visual da roda e das janelas. Vale na hora.")
        self.preview = Gtk.DrawingArea(content_height=320, hexpand=True)
        self.preview.add_css_class("mx-preview")
        self.preview.set_draw_func(self._draw_preview)
        page.append(self.preview)

        page.append(_section("Estilo"))
        styles = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,
                             max_children_per_line=5, min_children_per_line=2,
                             column_spacing=8, row_spacing=8, homogeneous=True)
        first = None
        for key, palette in TH.STYLES.items():
            dot = Gtk.DrawingArea(content_width=26, content_height=26)
            dot.set_draw_func(_draw_swatch, palette)
            inner = Gtk.Box(spacing=8)
            inner.append(dot)
            inner.append(Gtk.Label(label=palette["name"]))
            button = Gtk.ToggleButton(child=inner, group=first,
                                      active=key == cfg["style"])
            first = first or button
            button.add_css_class("mx-style")
            button.connect("toggled", lambda b, k=key:
                           b.get_active() and self._set(style=k))
            styles.append(button)
        page.append(styles)

        page.append(_section("Roda e janelas"))
        page.append(_row("Tamanho da roda", None, _choice(
            SIZES, cfg["wheel_size"], lambda k: self._set(wheel_size=k))))
        page.append(_row("Escurecer o fundo", "A tela atrás da roda",
                         _slider(0, 60, cfg["dim"], "%",
                                 lambda v: self._set(dim=v))))
        page.append(_row("Opacidade das janelas",
                         "Janelas de edição e notificações",
                         _slider(60, 100, cfg["window_opacity"], "%",
                                 lambda v: self._set(window_opacity=v))))
        page.append(_row("Animações", "Entrada da roda, hover e troca de roda",
                         _switch(cfg["animations"],
                                 lambda on: self._set(animations=on))))
        return page

    def _draw_preview(self, _area, cr, w, h) -> None:
        """A roda de verdade, como vai aparecer, sobre um fundo de mesa."""
        _rounded(cr, w, h, 14)
        cr.clip()
        dim = settings.get()["dim"] / 100
        if dim:
            cr.set_source_rgba(0, 0, 0, dim)
            cr.paint()
        s = settings.wheel_scale() * 0.8
        n = len(PREVIEW)
        st = WheelState(labels=PREVIEW, icons=[None] * n, caption="1.1 MB",
                        hover=1, hover_t={1: 1.0})
        cr.scale(s, s)
        draw(cr, Wheel(n, w / 2 / s, h / 2 / s), st)

    # -- Itens da roda -------------------------------------------------------
    def _items(self) -> Gtk.Box:
        page = _page(
            "Itens da roda",
            "Escolha o que aparece em cada roda. Um item só aparece quando "
            "serve para o arquivo arrastado e o programa dele está "
            "instalado (os apagados estão sem o programa). Passe o mouse "
            "para ver o que cada um faz. Na página Início aparecem todos, "
            "inclusive os que estão fora da roda.")
        tabs = Gtk.Stack()
        page.append(Gtk.StackSwitcher(stack=tabs, halign=Gtk.Align.START))
        for group, title, keys in GROUPS:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                          margin_top=6)
            flows: dict[str, Gtk.FlowBox] = {}
            for op in ALL_OPS:
                if op.group != group:
                    continue
                name = section_of(op)
                if name not in flows:
                    box.append(_section(name))
                    flows[name] = Gtk.FlowBox(
                        selection_mode=Gtk.SelectionMode.NONE,
                        column_spacing=6, row_spacing=6,
                        max_children_per_line=12)
                    box.append(flows[name])
                flows[name].append(self._chip(op))
            tabs.add_titled(box, group, f"{title}  ({keys})")
        page.append(tabs)
        reset = Gtk.Button(label="Restaurar o padrão", halign=Gtk.Align.START,
                           margin_top=8)
        reset.connect("clicked", self._reset_items)
        page.append(reset)
        return page

    def _chip(self, op: Op) -> Gtk.ToggleButton:
        chip = Gtk.ToggleButton(label=TH.wheel_label(op),
                                active=settings.shows(op))
        chip.add_css_class("mx-chip")
        tip = op.hint or op.label.rstrip("…")
        if not op.in_wheel:
            tip += " · fora da roda por padrão"
        if not op.is_available():
            chip.add_css_class("mx-missing")
            missing = [n for n in op.needs if not T.has(n)]
            tip += f" · falta {', '.join(missing) or 'um conversor'}"
        chip.set_tooltip_text(tip)
        chip.connect("toggled", self._on_chip, op)
        self._chips.append((chip, op))
        return chip

    def _on_chip(self, chip, op: Op) -> None:
        if not self._quiet:
            settings.set_shown(op, chip.get_active())

    def _reset_items(self, *_a) -> None:
        settings.reset("hidden", "extra")
        self._quiet = True
        for chip, op in self._chips:
            chip.set_active(settings.shows(op))
        self._quiet = False

    # -- Comportamento -------------------------------------------------------
    def _behavior(self) -> Gtk.Box:
        cfg = settings.get()
        page = _page("Comportamento",
                     "Onde os resultados são salvos e como a Mexerica avisa.")
        page.append(_section("Pasta de saída"))
        self._beside = beside = Gtk.CheckButton(
            label="Ao lado do arquivo original",
            active=cfg["output"] != "folder")
        self._fixed = Gtk.CheckButton(label="Sempre nesta pasta:", group=beside,
                                      active=cfg["output"] == "folder")
        self._folder = Gtk.Button(label=_folder_label(cfg["output_folder"]))
        self._folder.connect("clicked", lambda *_: self._pick_folder())
        beside.connect("toggled", lambda b: b.get_active()
                       and settings.update(output="beside"))
        self._fixed.connect("toggled", self._on_fixed)
        line = Gtk.Box(spacing=8)
        line.append(self._fixed)
        line.append(self._folder)
        page.append(beside)
        page.append(line)
        page.append(_hint("O nome nunca sobrescreve: se já existir, vira "
                          "\"foto (2).jpg\". Se a pasta não aceitar escrita, "
                          "o resultado vai para Downloads."))

        page.append(_section("Imagens"))
        page.append(_row("Qualidade do JPG",
                         "Conversões para JPG (o Editar… tem a dele)",
                         _slider(50, 100, cfg["jpeg_quality"], "",
                                 lambda v: settings.update(jpeg_quality=v))))

        page.append(_section("Avisos e início"))
        page.append(_row("Avisar quando um trabalho começa",
                         "O aviso de pronto, com Mostrar na pasta, vem sempre",
                         _switch(cfg["notify_start"],
                                 lambda on: settings.update(notify_start=on))))
        auto = self.app.desktop.autostart()
        start = _switch(bool(auto), self.app.desktop.set_autostart)
        start.set_sensitive(auto is not None)
        page.append(_row(
            "Iniciar com o sistema",
            "A Mexerica sobe sozinha no login" if auto is not None
            else "Disponível quando instalada pelo instalador", start))
        return page

    def _on_fixed(self, button) -> None:
        if not button.get_active():
            return
        if settings.get()["output_folder"]:
            settings.update(output="folder")
        else:
            self._pick_folder()

    def _pick_folder(self) -> None:
        dialog = Gtk.FileDialog(title="Pasta de saída", modal=True)
        current = settings.get()["output_folder"]
        if current:
            dialog.set_initial_folder(Gio.File.new_for_path(current))

        def done(dlg, result):
            try:
                folder = dlg.select_folder_finish(result).get_path()
            except GLib.Error:
                folder = None                       # cancelou
            if folder:
                settings.update(output="folder", output_folder=folder)
                self._folder.set_label(_folder_label(folder))
                self._fixed.set_active(True)
            elif settings.get()["output"] != "folder":
                self._beside.set_active(True)       # sem pasta, volta
        dialog.select_folder(self, None, done)

    # -- Sobre ---------------------------------------------------------------
    def _about(self) -> Gtk.Box:
        page = _page("Sobre", "")
        head = Gtk.Box(spacing=16)
        logo = Gtk.Image.new_from_file(str(ICON))
        logo.set_pixel_size(72)
        head.append(logo)
        names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                        valign=Gtk.Align.CENTER)
        title = Gtk.Label(xalign=0, use_markup=True)
        title.set_markup(f"<span size='x-large'><b>Mexerica "
                         f"{__version__}</b></span>")
        names.append(title)
        names.append(_hint("Converta arquivos segurando Shift enquanto "
                           "arrasta. Tudo local, nada vai para a internet."))
        status = Gtk.Label(xalign=0, use_markup=True)
        status.set_markup(self.app.desktop.status())
        names.append(status)
        head.append(names)
        page.append(head)

        page.append(_section("Gestos (durante um arraste de arquivo)"))
        page.append(_table([(Gtk.Label(label=k, xalign=0, css_classes=["mx-key"]),
                             Gtk.Label(label=v, xalign=0))
                            for k, v in GESTURES]))

        page.append(_section("Programas"))
        rows = []
        checks = [(n, w, T.has(n)) for n, w in T.PROGRAMS]
        checks += [(n, f"{w} (Python)", T.has_module(n)) for n, w in T.MODULES]
        for name, what, ok in checks:
            mark = Gtk.Label(label="✓" if ok else "—", xalign=0.5,
                             css_classes=["mx-ok" if ok else "mx-missing-mark"])
            rows.append((mark, Gtk.Label(label=name, xalign=0),
                         Gtk.Label(label=what, xalign=0,
                                   css_classes=["mx-hint"])))
        page.append(_table(rows))
        who = {office.MS: "Microsoft Office", office.LO: "LibreOffice",
               office.PANDOC: "pandoc + typst (só o conteúdo)"}
        docs = ", ".join(f"{label} → {who.get(office.route(fam, ext, 'pdf'), 'ninguém')}"
                         for fam, label, ext in ((office.TEXT, "textos", "docx"),
                                                 (office.SHEET, "planilhas", "xlsx"),
                                                 (office.SLIDES, "apresentações", "pptx")))
        page.append(_hint(f"Documentos do Office para PDF: {docs}."))
        page.append(_hint(
            "Para instalar o que falta: install.cmd -Converters (na pasta "
            "da Mexerica); o LibreOffice é opcional (-Office)."
            if sys.platform == "win32" else
            "Para instalar o que falta, veja Instalação no README ou na wiki."))

        buttons = Gtk.Box(spacing=8, margin_top=12)
        for label, action in (
                ("Abrir o log", lambda *_: self.app.activate_action(
                    "open-log", None)),
                ("Pasta das configurações", lambda *_: self.app.open_files(
                    [str(settings.path().parent)])),
                ("Sair da Mexerica", lambda *_: self.app.quit())):
            button = Gtk.Button(label=label)
            button.connect("clicked", action)
            buttons.append(button)
        page.append(buttons)
        page.append(_hint(f"Log: {cache_dir() / 'mexerica.log'}  ·  "
                          f"Configurações: {settings.path()}"))
        return page


# --------------------------------------------------------------------------
# Peças
# --------------------------------------------------------------------------

def _scroll(child: Gtk.Widget) -> Gtk.ScrolledWindow:
    return Gtk.ScrolledWindow(child=child, vexpand=True,
                              hscrollbar_policy=Gtk.PolicyType.NEVER)


def _page(title: str, subtitle: str) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                  margin_top=20, margin_bottom=24, margin_start=28,
                  margin_end=28)
    label = Gtk.Label(label=title, xalign=0)
    label.add_css_class("mx-page-title")
    box.append(label)
    if subtitle:
        box.append(_hint(subtitle))
    return box


def _section(text: str) -> Gtk.Label:
    label = Gtk.Label(label=text.upper(), xalign=0)
    label.add_css_class("mx-section")
    return label


def _hint(text: str) -> Gtk.Label:
    label = Gtk.Label(label=text, xalign=0, wrap=True)
    label.add_css_class("mx-hint")
    return label


def _row(title: str, hint: str | None, widget: Gtk.Widget) -> Gtk.Box:
    texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
    texts.append(Gtk.Label(label=title, xalign=0))
    if hint:
        texts.append(_hint(hint))
    row = Gtk.Box(spacing=16)
    row.append(texts)
    widget.set_valign(Gtk.Align.CENTER)
    row.append(widget)
    return row


def _table(rows) -> Gtk.Grid:
    grid = Gtk.Grid(column_spacing=14, row_spacing=4)
    for y, cells in enumerate(rows):
        for x, cell in enumerate(cells):
            grid.attach(cell, x, y, 1, 1)
    return grid


def _choice(options, active: str, on_change) -> Gtk.Box:
    box = Gtk.Box(css_classes=["linked"])
    first = None
    for key, label in options:
        button = Gtk.ToggleButton(label=label, group=first,
                                  active=key == active)
        first = first or button
        button.connect("toggled", lambda b, k=key:
                       b.get_active() and on_change(k))
        box.append(button)
    return box


def _slider(lo: int, hi: int, value: int, unit: str, on_change) -> Gtk.Box:
    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, 1)
    scale.set_draw_value(False)
    scale.set_size_request(220, -1)
    scale.set_value(value)
    shown = Gtk.Label(label=f"{value}{unit}", width_chars=5, xalign=1)

    def changed(s):
        v = int(round(s.get_value()))
        shown.set_text(f"{v}{unit}")
        on_change(v)
    scale.connect("value-changed", changed)
    box = Gtk.Box(spacing=8)
    box.append(scale)
    box.append(shown)
    return box


def _switch(active: bool, on_change) -> Gtk.Switch:
    switch = Gtk.Switch(active=active)
    switch.connect("notify::active", lambda s, _p: on_change(s.get_active()))
    return switch


def _folder_label(folder: str) -> str:
    return Path(folder).name or folder if folder else "Escolher…"


def _rounded(cr, w: float, h: float, r: float) -> None:
    cr.new_sub_path()
    cr.arc(w - r, r, r, -math.pi / 2, 0)
    cr.arc(w - r, h - r, r, 0, math.pi / 2)
    cr.arc(r, h - r, r, math.pi / 2, math.pi)
    cr.arc(r, r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def _draw_swatch(_area, cr, w, h, palette) -> None:
    g = cairo.LinearGradient(0, 0, w, h)
    for stop, color in ((0, palette["top"]), (1, palette["accent"])):
        c = TH._hex(color)
        g.add_color_stop_rgba(stop, *c)
    cr.arc(w / 2, h / 2, min(w, h) / 2 - 1, 0, 2 * math.pi)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgba(0, 0, 0, 0.12)
    cr.set_line_width(1)
    cr.stroke()
