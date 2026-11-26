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
import threading
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from . import __version__, i18n, settings  # noqa: E402
from .i18n import _, N_  # noqa: E402
from . import theme as TH  # noqa: E402
from .engine import ACTIONS, CONVERT, TOOLS  # noqa: E402
from .engine import formats as F  # noqa: E402
from .engine import tools as T  # noqa: E402
from .engine.ops import ALL_OPS, Op  # noqa: E402
from .wheel.geometry import Wheel  # noqa: E402
from .wheel.render import WheelState, draw  # noqa: E402

ICON = Path(__file__).with_name("data") / "icon.png"
COFFEE = "https://buymeacoffee.com/rogersocruz"
GROUPS = [(CONVERT, N_("Converter"), "Shift"),
          (TOOLS, N_("Ferramentas"), "Shift + Alt"),
          (ACTIONS, N_("Ações"), "Shift + Ctrl")]
SECTIONS = [(F.IMAGE, N_("Imagens")), (F.VECTOR, "SVG"), (F.VIDEO, N_("Vídeo")),
            (F.AUDIO, N_("Áudio")), (F.PDF, "PDF"), (F.DATA, N_("Dados")),
            (F.FONT, N_("Fontes")), (F.DOC_TEXT, N_("Documentos")),
            (F.DOC_SHEET, N_("Planilhas")),
            (F.DOC_SLIDES, N_("Apresentações")),
            (F.TEXT, N_("Texto e Markdown")), (F.EBOOK, "E-book"),
            (F.SUBTITLE, N_("Legendas")), (F.XOPP, "Xournal++")]
SIZES = [("small", N_("Pequena")), ("medium", N_("Média")),
         ("large", N_("Grande"))]
LANGS = [("system", N_("Automático")), ("pt", "Português"),
         ("en", "English")]
PREVIEW = ["JPG", "PNG", "WEBP", "HEIC", "PDF", "GIF", "AVIF", "TIFF"]
BLUR_MODES = [("system", N_("Do sistema")), ("custom", N_("Próprio")),
              ("off", N_("Desligado"))]
# (extensão, chave nas configurações, nome, mínimo do slider)
QUALITY = [("jpg", "jpeg_quality", "JPG", 50),
           ("webp", "webp_quality", "WEBP", 30),
           ("avif", "avif_quality", "AVIF", 20),
           ("heic", "heic_quality", "HEIC", 20),
           ("jxl", "jxl_quality", "JPEG XL", 30)]
# atalhos com o Ctrl + botão direito ligado (no lugar do Shift + arrastar)
CLICK_GESTURES = [(N_("Ctrl + botão direito"), N_("Roda de ações")),
                  ("Tab", N_("Próxima roda")),
                  ("Shift + Tab", N_("Roda anterior")),
                  ("Esc", N_("Fecha a roda"))]
GESTURES = [("Shift", N_("Roda de conversão")),
            ("Shift + Alt", N_("Roda de ferramentas")),
            ("Shift + Ctrl", N_("Roda de ações")),
            (N_("Soltar no centro da roda"), N_("Cancela")),
            (N_("Soltar o Shift"),
             N_("Fecha a roda; o arraste continua normal"))]


def section_of(op: Op) -> str:
    """Em que grupo de tipo o item aparece na lista de itens."""
    kinds = op.kinds
    if len(kinds) >= 5:
        return N_("Qualquer arquivo")
    if F.ARCHIVE in kinds:
        return N_("Compactados e pastas")
    if len(kinds) >= 3:
        return N_("Vários tipos")
    if F.AUDIO in kinds:
        return N_("Áudio")             # inclui o áudio extraído de vídeos
    return next((name for kind, name in SECTIONS if kind in kinds),
                N_("Outros"))


class SettingsWindow(Gtk.Window):
    def __init__(self, app):
        from .home import HomePage          # home.py usa as peças daqui
        super().__init__(application=app, title="Mexerica",
                         default_width=900, default_height=660)
        self.app = app
        self.add_css_class("mx-settings")
        self._quiet = False
        self._pending = 0
        self._chips: list[tuple[Gtk.ToggleButton, Op]] = []
        self.set_titlebar(Gtk.HeaderBar())
        self.connect("close-request", lambda *_: self._flush())

        self.home = HomePage(app)
        self.stack = stack = Gtk.Stack(
            hexpand=True, transition_type=Gtk.StackTransitionType.CROSSFADE)
        for name, title, page in (
                ("home", N_("Início"), self.home),
                ("look", N_("Aparência"), self._look()),
                ("items", N_("Itens da roda"), self._items()),
                ("behavior", N_("Comportamento"), self._behavior()),
                ("about", N_("Sobre"), self._about())):
            stack.add_titled(_scroll(page), name, _(title))
        side = Gtk.StackSidebar(stack=stack, width_request=190)
        body = Gtk.Box()
        body.append(side)
        body.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        body.append(stack)
        self.set_child(body)

    def _set(self, **changes) -> None:
        """Muda o visual: vale na hora e grava logo depois (_store)."""
        self._store(**changes)
        self.app.apply_settings()
        self.preview.queue_draw()

    def _store(self, **changes) -> None:
        """Vale na hora (memória) e grava 300 ms depois da última mudança:
        um arraste de slider não regrava o arquivo dezenas de vezes (no
        Windows o replace falhava com o arquivo ocupado e a mudança se
        perdia)."""
        settings.stage(**changes)
        if self._pending:
            GLib.source_remove(self._pending)
        self._pending = GLib.timeout_add(300, self._flush)

    def _language(self, key: str) -> None:
        """Troca o idioma: grava, refaz esta janela já no idioma novo e
        avisa o resto do app (bandeja, rodas)."""
        settings.update(language=key)
        i18n.reset()
        self._rebuild()

    def _rebuild(self) -> None:
        """Refaz a janela na mesma página (idioma novo, atalhos do Sobre)."""
        def rebuild():
            page = self.stack.get_visible_child_name()
            app = self.app
            self.close()
            app.settings_window = None
            app.relabel()
            app.show_settings(page)
            return False
        GLib.idle_add(rebuild)

    def _flush(self, *_a) -> bool:
        if self._pending:
            GLib.source_remove(self._pending)
            self._pending = 0
        settings.flush()
        return False

    # -- Aparência -----------------------------------------------------------
    def _look(self) -> Gtk.Box:
        cfg = settings.get()
        page = _page("Aparência", "Idioma, cores e efeitos da roda e das "
                                  "janelas.")
        self.preview = Gtk.DrawingArea(content_height=320, hexpand=True)
        self.preview.add_css_class("mx-preview")
        self.preview.set_draw_func(self._draw_preview)
        page.append(self.preview)

        page.append(_section("Idioma"))
        page.append(_row("Idioma",
                         "Automático: português se o sistema estiver em "
                         "português; inglês nos demais idiomas.",
                         _choice(LANGS, cfg["language"], self._language)))

        page.append(_section("Cores"))
        styles = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,
                             max_children_per_line=5, min_children_per_line=2,
                             column_spacing=8, row_spacing=8, homogeneous=True)
        first = None
        for key, palette in TH.STYLES.items():
            dot = Gtk.DrawingArea(content_width=26, content_height=26)
            dot.set_draw_func(_draw_swatch, palette)
            inner = Gtk.Box(spacing=8)
            inner.append(dot)
            inner.append(Gtk.Label(label=_(palette["name"])))
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
        page.append(_row("Escurecer a tela",
                         "Quanto a tela atrás da roda fica mais escura.",
                         _slider(0, 60, cfg["dim"], "%",
                                 lambda v: self._set(dim=v))))
        opacity = _slider(60, 100, cfg["window_opacity"], "%",
                          lambda v: self._set(window_opacity=v))
        hint = N_("Das janelas de edição e dos avisos. Menos opaco deixa "
                  "ver o que está atrás.")
        if sys.platform == "win32":
            from .desktop import win32 as W
            if not W.transparency_on():
                # as janelas ficam sólidas: o slider não teria efeito
                opacity.set_sensitive(False)
                hint = N_("Indisponível: a transparência está desligada "
                          "nas configurações do sistema.")
        page.append(_row("Opacidade das janelas", hint, opacity))
        page.append(_row("Animações",
                         "Movimento ao abrir a roda e ao passar o mouse "
                         "pelos itens.",
                         _switch(cfg["animations"],
                                 lambda on: self._set(animations=on))))

        page.append(_section("Desfoque de fundo"))
        radius = _slider(0, 40, cfg["blur_radius"], " px",
                         lambda v: self._set(blur_radius=v))

        def radius_works(key: str) -> bool:
            # o efeito do sistema no Windows não tem intensidade
            return key == "custom" or (key == "system"
                                       and sys.platform != "win32")
        radius.set_sensitive(radius_works(cfg["blur"]))

        def blur_mode(key):
            radius.set_sensitive(radius_works(key))
            self._set(blur=key)
        page.append(_row(
            "Tipo de desfoque",
            "Do sistema: usa o efeito do próprio sistema. Próprio: a "
            "Mexerica desfoca uma imagem da tela, que fica só na memória; "
            "funciona mesmo com a transparência do sistema desligada.",
            _choice(BLUR_MODES, cfg["blur"], blur_mode)))
        page.append(_row("Intensidade do desfoque",
                         "Desfoque do fundo atrás da roda.", radius))
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
            "Ligue ou desligue os itens de cada roda. Cada item só aparece "
            "para os arquivos em que funciona. Itens apagados precisam de um "
            "programa que não está instalado. Passe o mouse para ver o que "
            "cada um faz.")
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
            tabs.add_titled(box, group, f"{_(title)}  ({keys})")
        page.append(tabs)
        reset = Gtk.Button(label=_("Restaurar o padrão"),
                           halign=Gtk.Align.START, margin_top=8)
        reset.connect("clicked", self._reset_items)
        page.append(reset)
        return page

    def _chip(self, op: Op) -> Gtk.ToggleButton:
        chip = Gtk.ToggleButton(label=TH.wheel_label(op),
                                active=settings.shows(op))
        chip.add_css_class("mx-chip")
        tip = _(op.hint) if op.hint else _(op.label).rstrip("…")
        if not op.in_wheel:
            tip += " · " + _("fora da roda por padrão")
        if not op.is_available():
            chip.add_css_class("mx-missing")
            missing = [n for n in op.needs if not T.has(n)]
            tip += " · " + _("falta {what}").format(
                what=", ".join(missing) or _("um conversor"))
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
                     "Onde salvar os arquivos, qualidade e avisos.")
        page.append(_section("Onde salvar"))
        self._beside = beside = Gtk.CheckButton(
            label=_("Na mesma pasta do arquivo original"),
            active=cfg["output"] != "folder")
        self._fixed = Gtk.CheckButton(label=_("Sempre nesta pasta:"),
                                      group=beside,
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
        page.append(_hint("Nenhum arquivo é substituído: se o nome já "
                          "existir, o novo vira \"foto (2).jpg\"."))

        page.append(_section("Qualidade das imagens"))
        page.append(_hint("Usada ao converter para cada formato. Mais alta: "
                          "imagem melhor e arquivo maior."))
        # todos aparecem: perguntar ao magick o que ele escreve leva ~10 s
        # no Windows na primeira vez, e a janela não pode esperar
        for ext, key, name, lo in QUALITY:
            slider = _slider(lo, 100, cfg[key], "",
                             lambda v, k=key: self._store(**{k: v}))
            if ext == "webp":
                page.append(_row("WEBP sem perda",
                                 "Imagem idêntica à original, arquivo maior. "
                                 "Ignora a qualidade do WEBP.",
                                 _switch(cfg["webp_lossless"],
                                         lambda on, sl=slider: (
                                             sl.set_sensitive(not on),
                                             self._store(webp_lossless=on)))))
                slider.set_sensitive(not cfg["webp_lossless"])
            page.append(_row(_("Qualidade do {fmt}").format(fmt=name), None,
                             slider))
        page.append(_row(
            "Compressão do PNG",
            "Não muda a imagem. Mais alta: arquivo menor, conversão mais "
            "lenta.",
            _slider(0, 9, cfg["png_compression"], "",
                    lambda v: self._store(png_compression=v))))

        page.append(_section("Avisos e inicialização"))
        page.append(_row("Avisar quando uma conversão começa",
                         "O aviso de conclusão aparece sempre.",
                         _switch(cfg["notify_start"],
                                 lambda on: settings.update(notify_start=on))))
        auto = self.app.desktop.autostart()
        start = _switch(bool(auto), self.app.desktop.set_autostart)
        start.set_sensitive(auto is not None)
        page.append(_row(
            "Abrir ao entrar no sistema",
            N_("Deixa a roda pronta logo depois do login.")
            if auto is not None
            else N_("Disponível só na versão instalada."), start))
        if sys.platform == "win32":
            self._right_click_row(page, cfg)
            from .desktop import hotkeys
            from .desktop.win32 import packaged
            page.append(_section("Teclado"))
            if packaged():
                # Store: sem unvirtualizedResources, quem muda é o Windows
                open_btn = Gtk.Button(label=_("Abrir configurações"),
                                      valign=Gtk.Align.CENTER)
                open_btn.connect("clicked",
                                 lambda *_: hotkeys.open_windows_settings())
                page.append(_row(
                    "Liberar Shift+Alt e Shift+Ctrl",
                    _("Para essas teclas abrirem as rodas, desative os "
                      "atalhos do sistema que trocam o idioma do teclado "
                      "com elas:") + " " + _(hotkeys.STEPS) + ".",
                    open_btn))
                return page
            page.append(_row(
                "Liberar Shift+Alt e Shift+Ctrl",
                "Desativa os atalhos do sistema que trocam o idioma do "
                "teclado com essas teclas, para elas abrirem as rodas.",
                _switch(not hotkeys.conflicting(), lambda on:
                        hotkeys.disable() if on else hotkeys.restore())))
        return page

    def _right_click_row(self, page: Gtk.Box, cfg: dict) -> None:
        """Windows: a roda no Ctrl + botão direito (no lugar do menu)."""
        page.append(_section("Botão direito"))

        def wheel(on):
            settings.update(right_click_wheel=on)
            self.app.desktop.set_right_click(on)
            self._rebuild()             # o Sobre mostra os atalhos do modo
        page.append(_row(
            "Roda com Ctrl + botão direito",
            "Ctrl + botão direito sobre arquivos selecionados abre a roda "
            "de ações no lugar do menu. Tab passa para a próxima roda "
            "(conversão, ferramentas, ações) e Shift+Tab volta; Esc fecha. "
            "Ligada, substitui o Shift + arrastar, que deixa de abrir a "
            "roda. Sem o Ctrl, o botão direito abre o menu de sempre.",
            _switch(cfg["right_click_wheel"], wheel)))

    def _on_fixed(self, button) -> None:
        if not button.get_active():
            return
        if settings.get()["output_folder"]:
            settings.update(output="folder")
        else:
            self._pick_folder()

    def _pick_folder(self) -> None:
        dialog = Gtk.FileDialog(title=_("Onde salvar"), modal=True)
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
        names.append(_hint("Converta e edite arquivos segurando Shift "
                           "enquanto arrasta. Tudo acontece no seu "
                           "computador."))
        if self.app.desktop.drag_ok() is False:
            warn = _hint("A roda não vai abrir: a detecção de arraste está "
                         "desligada.")
            warn.add_css_class("mx-error")
            names.append(warn)
        coffee = Gtk.Button(label="☕  " + _("Pague me um café"),
                            halign=Gtk.Align.START,
                            margin_top=4, css_classes=["suggested-action"],
                            tooltip_text=COFFEE)
        coffee.connect("clicked", lambda *_: self.app.desktop.open_uri(COFFEE))
        names.append(coffee)
        head.append(names)
        page.append(head)

        self._packages(page)

        click_mode = sys.platform == "win32" and \
            settings.get()["right_click_wheel"]
        page.append(_section("Atalhos" if click_mode
                             else "Atalhos durante o arraste"))
        page.append(_table([(Gtk.Label(label=_(k), xalign=0,
                                       css_classes=["mx-key"]),
                             Gtk.Label(label=_(v), xalign=0))
                            for k, v in (CLICK_GESTURES if click_mode
                                         else GESTURES)]))

        quit_btn = Gtk.Button(label=_("Sair da Mexerica"),
                              halign=Gtk.Align.START, margin_top=12)
        quit_btn.connect("clicked", lambda *_a: self.app.quit())
        page.append(quit_btn)
        return page


    # -- formatos extras (engine/packages.py) ---------------------------------
    def _packages(self, page: Gtk.Box) -> None:
        from .engine import packages as PK
        self._pk = PK
        self._pk_system = system = PK.detect()
        self._pk_busy = False
        self._pk_rows: dict[str, tuple] = {}
        page.append(_section("Formatos extras"))
        if system.can_install:
            page.append(_hint("Baixe o suporte só aos tipos de arquivo que "
                              "você usa. Remover libera espaço e tira esses "
                              "itens da roda."))
        elif system.kind == "store":
            page.append(_hint("Os formatos principais já vêm incluídos. Os "
                              "que aparecem sem \"Instalado\" precisam de "
                              "um programa instalado à parte."))
        else:
            page.append(_hint("Instale os programas pelo gerenciador de "
                              "pacotes do sistema."))
        for pkg in PK.PACKAGES:
            spinner = Gtk.Spinner()
            status = Gtk.Label(css_classes=["mx-hint"], xalign=1)
            button = Gtk.Button(label=_("Baixar"), sensitive=False,
                                width_request=96,
                                visible=system.can_install)
            button.connect("clicked", self._pk_clicked, pkg)
            box = Gtk.Box(spacing=8)
            box.append(spinner)
            box.append(status)
            box.append(button)
            spinner.start()
            self._pk_rows[pkg.id] = (spinner, status, button)
            page.append(_row(pkg.title, pkg.formats, box))
        self._pk_check()

    def _pk_check(self) -> None:
        """Quem está instalado, numa thread (o ImageMagick demora para
        dizer se escreve HEIC na primeira vez)."""
        PK = self._pk

        def work():
            states = {pkg.id: pkg.installed() for pkg in PK.PACKAGES}
            GLib.idle_add(lambda: (self._pk_show(states), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def _pk_show(self, states: dict[str, bool]) -> None:
        PK, system = self._pk, self._pk_system
        for pkg in PK.PACKAGES:
            spinner, status, button = self._pk_rows[pkg.id]
            spinner.stop()
            spinner.set_visible(False)
            on = states[pkg.id]
            if not status.has_css_class("mx-error"):
                status.set_text(_("Instalado") if on else "")
            action = PK.REMOVE if on else PK.INSTALL
            button.set_label(_("Remover") if on else _("Baixar"))
            ok = PK.supported(pkg, system, action) and not self._pk_busy
            button.set_sensitive(ok)
            button.set_tooltip_text(
                None if ok or self._pk_busy else
                _("Remova pelo gerenciador de pacotes do sistema.")
                if on and system.can_install else None)
            button.installed = on
        # os itens da roda que ganharam ou perderam o programa
        for chip, op in self._chips:
            (chip.remove_css_class if op.is_available()
             else chip.add_css_class)("mx-missing")

    def _pk_clicked(self, button, pkg) -> None:
        if self._pk_busy:
            return
        if not getattr(button, "installed", False):
            self._pk_run(pkg, self._pk.INSTALL)
            return
        dialog = Gtk.AlertDialog(
            message=_("Remover {name}?").format(name=_(pkg.title)),
            detail=_("Os itens da roda que usam esses formatos deixam de "
                     "aparecer. Dá para baixar de novo depois."),
            buttons=[_("Cancelar"), _("Remover")], cancel_button=0,
            default_button=0)

        def done(dlg, result):
            try:
                if dlg.choose_finish(result) == 1:
                    self._pk_run(pkg, self._pk.REMOVE)
            except GLib.Error:
                pass                                # fechou o diálogo
        dialog.choose(self, None, done)

    def _pk_run(self, pkg, action: str) -> None:
        PK = self._pk
        self._pk_busy = True
        for _sp, _st, btn in self._pk_rows.values():
            btn.set_sensitive(False)
        spinner, status, _btn = self._pk_rows[pkg.id]
        spinner.set_visible(True)
        spinner.start()
        status.remove_css_class("mx-error")
        status.set_tooltip_text(None)
        status.set_text(_("Baixando…") if action == PK.INSTALL
                        else _("Removendo…"))

        def work():
            ok, msg = PK.apply(pkg, action, self._pk_system)
            GLib.idle_add(lambda: (self._pk_done(pkg, ok, msg), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def _pk_done(self, pkg, ok: bool, msg: str) -> None:
        self._pk_busy = False
        _spinner, status, _btn = self._pk_rows[pkg.id]
        if not ok:
            status.add_css_class("mx-error")
            status.set_text(_("Falhou"))
            status.set_tooltip_text(msg)
        self.app.relabel()
        self._pk_check()


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
    label = Gtk.Label(label=_(title), xalign=0)
    label.add_css_class("mx-page-title")
    box.append(label)
    if subtitle:
        box.append(_hint(subtitle))
    return box


def _section(text: str) -> Gtk.Label:
    label = Gtk.Label(label=_(text).upper(), xalign=0)
    label.add_css_class("mx-section")
    return label


def _hint(text: str) -> Gtk.Label:
    label = Gtk.Label(label=_(text), xalign=0, wrap=True)
    label.add_css_class("mx-hint")
    return label


def _row(title: str, hint: str | None, widget: Gtk.Widget) -> Gtk.Box:
    texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
    texts.append(Gtk.Label(label=_(title), xalign=0))
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
        button = Gtk.ToggleButton(label=_(label), group=first,
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
    return Path(folder).name or folder if folder else _("Escolher…")


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
