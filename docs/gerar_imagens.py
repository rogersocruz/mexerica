"""Gera as imagens do site (docs/assets) com o código de verdade da Mexerica.

  python docs/gerar_imagens.py

As rodas saem do mesmo desenho do app (cairo + Pango); as Configurações, a
Flutuar e as janelas de edição são renderizadas pelo GTK, fora da tela.
Precisa do GTK e do ImageMagick, como o serviço (no Windows, o Python do
MSYS2). As configurações reais do usuário não são lidas nem alteradas.
"""
from __future__ import annotations

import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "assets"
WORK = Path(tempfile.mkdtemp(prefix="mexerica-site-"))

from mexerica import history, settings  # noqa: E402

settings.path = lambda: WORK / "settings.json"     # longe das reais
history.path = lambda: WORK / "history.json"

import cairo  # noqa: E402
import gi  # noqa: E402

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango, PangoCairo  # noqa: E402

from mexerica import theme as TH  # noqa: E402
from mexerica.engine import BY_ID  # noqa: E402
from mexerica.engine import tools as T  # noqa: E402
from mexerica.wheel.geometry import Wheel  # noqa: E402
from mexerica.wheel.render import WheelState, draw  # noqa: E402

CONVERT = ["to-jpg", "to-png", "to-webp", "to-avif", "to-tiff", "to-bmp",
           "to-gif", "to-ico", "to-pdf"]
TOOLS = ["img-edit", "img-crop", "img-addbg", "img-rmbg", "img-size",
         "img-compress", "img-rotate", "img-qr", "strip-meta", "show-meta"]
ACTIONS = ["act-copy-path", "act-terminal", "act-copy-to", "act-move-to",
           "act-float", "act-zip-all"]


# --------------------------------------------------------------------------
# Rodas (só cairo)
# --------------------------------------------------------------------------

def wheel_png(name: str, ids: list[str], hover: int | None = None,
              style: str = "mexerica", size: int = 420, scale: int = 2,
              caption: str = "2.4 MB") -> None:
    TH.apply(style)
    ops = [BY_ID[i] for i in ids]
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size * scale, size * scale)
    cr = cairo.Context(surf)
    cr.scale(scale, scale)
    st = WheelState(labels=[TH.wheel_label(o) for o in ops],
                    icons=[TH.wheel_icon(o) for o in ops], caption=caption,
                    hover=hover,
                    hover_t={hover: 1.0} if hover is not None else {})
    draw(cr, Wheel(len(ops), size / 2, size / 2), st)
    surf.write_to_png(str(OUT / f"{name}.png"))
    TH.apply()


def sample_photo(path: Path) -> None:
    """Uma "foto" desenhada aqui (pôr do sol), para as janelas de edição."""
    w, h = 1600, 1067
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    cr = cairo.Context(surf)
    sky = cairo.LinearGradient(0, 0, 0, h * 0.7)
    for stop, rgb in ((0, (0.33, 0.27, 0.62)), (0.55, (0.98, 0.45, 0.35)),
                      (1, (1.0, 0.76, 0.45))):
        sky.add_color_stop_rgb(stop, *rgb)
    cr.set_source(sky)
    cr.paint()
    sun = cairo.RadialGradient(w * 0.62, h * 0.55, 10, w * 0.62, h * 0.55, 260)
    sun.add_color_stop_rgba(0, 1, 0.95, 0.75, 1)
    sun.add_color_stop_rgba(0.35, 1, 0.82, 0.5, 0.9)
    sun.add_color_stop_rgba(1, 1, 0.6, 0.4, 0)
    cr.set_source(sun)
    cr.paint()
    for i, (base, amp, rgb) in enumerate(((0.62, 60, (0.55, 0.30, 0.45)),
                                          (0.72, 45, (0.36, 0.20, 0.38)),
                                          (0.84, 35, (0.18, 0.11, 0.24)))):
        cr.move_to(0, h)
        for x in range(0, w + 20, 20):
            y = h * base + amp * math.sin(x / (170 + 60 * i) + i * 1.7)
            cr.line_to(x, y)
        cr.line_to(w, h)
        cr.close_path()
        cr.set_source_rgb(*rgb)
        cr.fill()
    png = WORK / "foto.png"
    surf.write_to_png(str(png))
    subprocess.run(T.cmd("magick") + [str(png), "-quality", "90", str(path)],
                   check=True)


def og_image(path: Path) -> None:
    """Imagem de compartilhamento (1200×630): roda + nome."""
    W, H = 1200, 630
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    cr = cairo.Context(surf)
    bg = cairo.LinearGradient(0, 0, W, H)
    bg.add_color_stop_rgb(0, 1.0, 0.95, 0.89)
    bg.add_color_stop_rgb(1, 1.0, 0.83, 0.68)
    cr.set_source(bg)
    cr.paint()
    ops = [BY_ID[i] for i in CONVERT]
    cr.save()
    cr.translate(840, 315)
    cr.scale(1.45, 1.45)
    cr.translate(-210, -210)
    draw(cr, Wheel(len(ops), 210, 210),
         WheelState(labels=[TH.wheel_label(o) for o in ops], icons=[None] * 9,
                    caption="2.4 MB", hover=0, hover_t={0: 1.0}))
    cr.restore()

    def text(markup: str, y: float, size: float) -> None:
        lay = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription.from_string("Inter, Segoe UI, Sans")
        desc.set_absolute_size(size * Pango.SCALE)
        lay.set_font_description(desc)
        lay.set_width(560 * Pango.SCALE)
        lay.set_wrap(Pango.WrapMode.WORD)
        lay.set_markup(markup, -1)
        cr.move_to(80, y)
        cr.set_source_rgb(0.23, 0.16, 0.13)
        PangoCairo.show_layout(cr, lay)
    text("<b>Mexerica</b>", 170, 76)
    text("Segure <b>Shift</b> enquanto arrasta um arquivo e escolha o "
         "formato numa roda.", 285, 34)
    text("Windows 10/11 · GNOME · código aberto", 470, 24)
    surf.write_to_png(str(path))


# --------------------------------------------------------------------------
# Janelas (GTK, fora da tela)
# --------------------------------------------------------------------------

def sample_history(photo: Path) -> None:
    """Três conversões recentes, com arquivos de verdade (a página Início
    mostra a miniatura de cada um)."""
    import datetime as dt
    import json
    now = dt.datetime.now()
    png = WORK / "foto.png"
    subprocess.run(T.cmd("magick") + [str(photo), str(png)], check=True)
    data = WORK / "pedidos.json"
    data.write_text(json.dumps([{"id": 1}]), encoding="utf-8")
    mp3 = WORK / "entrevista.mp3"
    mp3.write_bytes(b"")
    for op, label, src, out, ago in (
            ("to-json-data", "JSON", "pedidos.csv", data, dt.timedelta(days=1)),
            ("to-mp3-audio", "MP3", "entrevista.mp4", mp3,
             dt.timedelta(hours=2)),
            ("to-png", "PNG", photo.name, png, dt.timedelta(minutes=3))):
        history.add(op, label, [WORK / src], [out], when=now - ago)


def gui_shots(photo: Path) -> None:
    from mexerica import desktop
    from mexerica.app import MexericaApp
    from mexerica.editors.addbg import AddBgWindow
    from mexerica.editors.crop import CropWindow
    from mexerica.floating import FloatWindow
    from mexerica.settings_window import SettingsWindow

    class Shots(Gtk.Application):
        apply_settings = MexericaApp.apply_settings

        def __init__(self):
            super().__init__(application_id="io.github.rogersocruz.MexericaSite",
                             flags=Gio.ApplicationFlags.NON_UNIQUE)
            self.overlay = None
            self._css = Gtk.CssProvider()
            self.desktop = desktop.backend(self)

        def open_files(self, *_a):
            pass

        def execute(self, *_a):
            pass

        def do_startup(self):
            Gtk.Application.do_startup(self)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), self._css,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self.apply_settings()

        def do_activate(self):
            self.hold()
            self.wins = {
                "settings": SettingsWindow(self),
                "float": FloatWindow(self, [photo]),
                "crop": CropWindow(self, BY_ID["img-crop"], photo),
                "addbg": AddBgWindow(self, BY_ID["img-addbg"], photo),
            }
            for win in self.wins.values():
                win.present()
                if sys.platform == "win32":          # fora da tela
                    from mexerica.desktop import win32 as W
                    W.move(W.hwnd_of(win), -6000, -6000)
            GLib.timeout_add(4000, self.shoot)     # prévias carregam em threads

        def settle(self):
            ctx = GLib.MainContext.default()
            for _ in range(40):
                ctx.iteration(False)

        def snap(self, win, name):
            """PNG da janela em 2x (texto e desenho refeitos, nítidos)."""
            self.settle()
            w, h = win.get_width(), win.get_height()
            snap = Gtk.Snapshot()
            snap.scale(2, 2)
            Gtk.WidgetPaintable.new(win).snapshot(snap, w, h)
            tex = win.get_native().get_renderer().render_texture(
                snap.to_node(), None)
            tex.save_to_png(str(OUT / f"{name}.png"))
            print("janela", name, w, h)

        def shoot(self):
            sw = self.wins["settings"]
            sw.stack.set_transition_type(Gtk.StackTransitionType.NONE)
            sw.home.set_files([photo])
            for page in ("home", "look", "items"):
                sw.stack.set_visible_child_name(page)
                self.snap(sw, f"settings-{page}")
            for name in ("float", "crop", "addbg"):
                self.snap(self.wins[name], name)
            self.quit()
            return False

    Shots().run([])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    photo = WORK / "foto.jpg"
    sample_photo(photo)
    wheel_png("wheel-convert", CONVERT)
    wheel_png("wheel-convert-hover", CONVERT, hover=0)
    wheel_png("wheel-tools", TOOLS, hover=2)
    wheel_png("wheel-actions", ACTIONS, hover=4)
    for style in TH.STYLES:
        wheel_png(f"style-{style}", CONVERT, hover=1, style=style, scale=1)
    og_image(OUT / "og.png")
    shutil.copy(ROOT / "data" / "icons" / "io.github.rogersocruz.Mexerica.svg",
                OUT / "icon.svg")
    shutil.copy(ROOT / "mexerica" / "data" / "icon.png", OUT / "icon.png")
    sample_history(photo)
    gui_shots(photo)
    shutil.rmtree(WORK, ignore_errors=True)
    print("imagens em", OUT)


if __name__ == "__main__":
    main()
