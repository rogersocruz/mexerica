"""Gerar QR code: nome e link e, em Personalizar, cores, tamanho, margem,
correção de erros e formato, com prévia. Abre a partir de qualquer arquivo
ou pasta (roda de ações), que só define onde o QR é salvo: a pasta do
arquivo, ou a própria pasta. Sem nada arrastado (botão da Início), vai
para a pasta de saída das Configurações ou para Downloads. A última
personalização fica guardada (settings, chaves qr_*)."""
from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from .. import settings  # noqa: E402
from ..engine import edits as E  # noqa: E402
from ..engine.ops import Op  # noqa: E402
from ..i18n import N_, _  # noqa: E402
from .base import ColorButton, EditorWindow, Segmented, label  # noqa: E402
from .common import Latest, texture  # noqa: E402

SIZES = [(N_("Pequeno"), 300), (N_("Médio"), 600), (N_("Grande"), 1200)]
LEVELS = [(N_("Baixa"), "L"), (N_("Média"), "M"), (N_("Alta"), "Q"),
          (N_("Máxima"), "H")]
FORMATS = ["png", "svg"]
PREVIEW_PX = 200


def default_folder() -> Path:
    folder = settings.output_dir() or Path.home() / "Downloads"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _nearest(options, value) -> int:
    return min(range(len(options)),
               key=lambda i: abs(options[i][1] - value))


class QrWindow(EditorWindow):
    def __init__(self, app, op: Op, path: Path | None = None):
        super().__init__(app, op, "Gerar QR code", 480, 220,
                         primary="Gerar")
        self.path = path
        self._named = False            # o usuário já mexeu no nome?
        self._setting_name = False
        self._quiet = False
        self.preview = Latest()
        self.style = E.QrStyle.from_settings(settings.get())

        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        grid.attach(label("Nome"), 0, 0, 1, 1)
        self.name = Gtk.Entry(hexpand=True)
        self.name.connect("changed", self._name_changed)
        self.name.connect("activate", lambda *_: self.save())
        grid.attach(self.name, 1, 0, 1, 1)

        grid.attach(label("Link"), 0, 1, 1, 1)
        self.link = Gtk.Entry(hexpand=True,
                              placeholder_text="https://…",
                              secondary_icon_name="edit-paste-symbolic",
                              secondary_icon_tooltip_text=_(
                                  "Colar o link copiado"))
        self.link.connect("icon-press", lambda *_: self._paste(force=True))
        self.link.connect("changed", lambda *_: self._changed())
        self.link.connect("activate", lambda *_: self.save())
        grid.attach(self.link, 1, 1, 1, 1)
        self.body.append(grid)

        self.expander = Gtk.Expander(label=_("Personalizar"))
        self.expander.connect("notify::expanded", lambda *_: self._refresh())
        self.expander.set_child(self._custom())
        self.body.append(self.expander)

        where = self._folder()
        self.say(_("Salvo em {folder}").format(folder=where.name or where))
        self._paste(force=False)       # um link copiado já entra sozinho
        self._changed()
        self.link.grab_focus()

    # -- Personalizar --------------------------------------------------------
    def _custom(self) -> Gtk.Box:
        st = self.style
        box = Gtk.Box(spacing=16, margin_top=10)
        self.pic = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN,
                               can_shrink=True, width_request=PREVIEW_PX,
                               height_request=PREVIEW_PX,
                               valign=Gtk.Align.START)
        self.pic.add_css_class("mx-qr")
        box.append(self.pic)

        opts = Gtk.Grid(column_spacing=10, row_spacing=8, hexpand=True)
        row = 0

        def add(title, widget, tip=None):
            nonlocal row
            lbl = label(title)
            if tip:
                lbl.set_tooltip_text(_(tip))
                widget.set_tooltip_text(_(tip))
            opts.attach(lbl, 0, row, 1, 1)
            opts.attach(widget, 1, row, 1, 1)
            row += 1

        self.fg = ColorButton(st.fg, lambda _c: self._custom_changed(),
                              N_("Cor do QR"))
        self.fg.set_halign(Gtk.Align.START)
        add(N_("Cor"), self.fg)

        bg_row = Gtk.Box(spacing=8)
        self.bg = ColorButton(st.bg, lambda _c: self._custom_changed(),
                              N_("Cor do fundo"))
        bg_row.append(self.bg)
        self.transparent = Gtk.CheckButton(label=_("Transparente"),
                                           active=st.transparent)
        self.transparent.connect("toggled", lambda *_: self._custom_changed())
        bg_row.append(self.transparent)
        add(N_("Fundo"), bg_row)

        self.size = Segmented([s[0] for s in SIZES],
                              active=_nearest(SIZES, st.size),
                              on_change=lambda _i: self._custom_changed())
        add(N_("Tamanho"), self.size)

        self.margin = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,
                                               0, 8, 1)
        self.margin.set_value(st.margin)
        self.margin.set_hexpand(True)
        self.margin.set_draw_value(True)
        self.margin.set_value_pos(Gtk.PositionType.RIGHT)
        self.margin.set_digits(0)
        self.margin.connect("value-changed", lambda *_: self._custom_changed())
        add(N_("Margem"), self.margin,
            N_("Borda em volta do código. Abaixo de 2, alguns leitores "
               "falham."))

        self.level = Segmented([lv[0] for lv in LEVELS],
                               active="LMQH".index(st.level),
                               on_change=lambda _i: self._custom_changed())
        add(N_("Correção"), self.level,
            N_("Quanto do código pode estar danificado e ainda ser lido. "
               "Mais alta deixa o código mais denso."))

        self.fmt = Segmented(["PNG", "SVG"],
                             active=FORMATS.index(st.fmt),
                             on_change=lambda _i: self._custom_changed())
        add(N_("Formato"), self.fmt,
            N_("SVG fica nítido em qualquer tamanho, bom para impressão."))

        self.warn = label("", "mx-error", wrap=True)
        opts.attach(self.warn, 0, row, 2, 1)
        box.append(opts)
        return box

    def _read_style(self) -> E.QrStyle:
        return E.QrStyle(
            fg=self.fg.get_color(), bg=self.bg.get_color(),
            transparent=self.transparent.get_active(),
            size=SIZES[self.size.get_active()][1],
            margin=int(self.margin.get_value()),
            level=LEVELS[self.level.get_active()][1],
            fmt=FORMATS[self.fmt.get_active()])

    def _custom_changed(self) -> None:
        if self._quiet:
            return
        self.style = self._read_style()
        self.bg.set_sensitive(not self.style.transparent)
        self.warn.set_text(_("Pouco contraste: alguns leitores podem não "
                             "ler este QR.") if self.style.low_contrast()
                           else "")
        self._refresh()

    def _refresh(self) -> None:
        """Prévia (só com o Personalizar aberto)."""
        text = self.link.get_text().strip()
        if not self.expander.get_expanded() or not text:
            self.pic.set_paintable(None)
            return
        preview = E.QrStyle(**{**self.style.__dict__, "size": 400,
                               "fmt": "png"})
        self.preview.request(lambda: E.qr_bytes(text, style=preview),
                             self.alive(self._show))

    def _show(self, res) -> None:
        if isinstance(res, Exception):
            self.warn.set_text(_("Não deu para gerar este QR: {err}").format(
                err=res))
            return
        self.pic.set_paintable(texture(res))

    # -- campos --------------------------------------------------------------
    def _folder(self) -> Path:
        """Onde o QR vai parar (a pasta fixa das Configurações manda)."""
        if self.path is None or settings.output_dir():
            return default_folder()
        return self.path if self.path.is_dir() else self.path.parent

    def _paste(self, force: bool) -> None:
        """Ao abrir, só aproveita um link; o botão cola qualquer texto."""
        clip = Gdk.Display.get_default().get_clipboard()

        def done(cb, res):
            try:
                text = (cb.read_text_finish(res) or "").strip()
            except Exception:  # noqa: BLE001 - clipboard vazio ou imagem
                return
            if self.closed or not text:
                return
            if force or E.looks_like_link(text):
                self.link.set_text(text)
                self.link.set_position(-1)
        clip.read_text_async(None, done)

    def _name_changed(self, *_a) -> None:
        if not self._setting_name:
            self._named = bool(self.name.get_text().strip())

    def _changed(self) -> None:
        """O nome acompanha o link até o usuário escrever o dele."""
        text = self.link.get_text().strip()
        self.save_btn.set_sensitive(bool(text))
        if not self._named:
            self._setting_name = True
            self.name.set_text(E.qr_name(text) if text else "")
            self._setting_name = False
        self._refresh()

    def reset(self) -> None:
        """Volta a personalização ao padrão (preto no branco, médio)."""
        st = E.QrStyle()
        self._quiet = True
        self.fg.set_color(st.fg)
        self.bg.set_color(st.bg)
        self.transparent.set_active(st.transparent)
        self.size.set_active(_nearest(SIZES, st.size))
        self.margin.set_value(st.margin)
        self.level.set_active("LMQH".index(st.level))
        self.fmt.set_active(FORMATS.index(st.fmt))
        self._quiet = False
        self._custom_changed()

    def cleanup(self) -> None:
        self.preview.cancel()

    def build(self):
        text = self.link.get_text().strip()
        if not text:
            raise ValueError(_("Cole um link ou um texto."))
        style = self._read_style()
        settings.update(**style.to_settings())     # a próxima abre igual
        name = self.name.get_text().strip() or E.qr_name(text)
        op = E.qr_op(self.op, text, suffix="", style=style)
        return op, [E.qr_target(name, self.path, default_folder())]
