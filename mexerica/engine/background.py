"""Imagem sobre um fundo (estilo CleanShot): cantos arredondados, sombra e
margem, num fundo em gradiente, cor sólida ou outra imagem.

O mesmo `paint()` desenha a prévia ao vivo da janela (com a imagem
reduzida e `k` < 1) e o PNG final, então o que se vê é o que se salva.
Só pycairo, sem GTK.
"""
from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cairo

from . import tools as T

SHADOW_LAYERS = 18


@dataclass
class BgStyle:
    kind: str = "gradient"                 # gradient | solid | image
    colors: tuple[str, str] = ("#FF9A5A", "#FF4E50")
    color: str = "#FFFFFF"
    image: str | None = None               # caminho do fundo (kind=image)
    padding: int = 100                     # px da imagem original
    corners: int = 104
    shadow: int = 24                       # 0..100
    ratio: float | None = None             # None = automático


def _rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def canvas_size(w: float, h: float, style: BgStyle,
                k: float = 1.0) -> tuple[int, int]:
    pad = style.padding * k
    cw, ch = w + 2 * pad, h + 2 * pad
    if style.ratio:
        if cw / ch < style.ratio:
            cw = ch * style.ratio
        else:
            ch = cw / style.ratio
    return max(1, round(cw)), max(1, round(ch))


def _rrect(cr, x, y, w, h, r) -> None:
    r = max(0.0, min(r, w / 2, h / 2))
    if r <= 0:
        cr.rectangle(x, y, w, h)
        return
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def _background(cr, W, H, style: BgStyle, bg_img) -> None:
    if style.kind == "solid":
        cr.set_source_rgb(*_rgb(style.color))
        cr.paint()
        return
    if style.kind == "image" and bg_img is not None:
        iw, ih = bg_img.get_width(), bg_img.get_height()
        s = max(W / iw, H / ih)                     # cobre o quadro
        cr.save()
        cr.translate((W - iw * s) / 2, (H - ih * s) / 2)
        cr.scale(s, s)
        cr.set_source_surface(bg_img, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_GOOD)
        cr.paint()
        cr.restore()
        return
    g = cairo.LinearGradient(0, 0, W, H)            # 135°
    g.add_color_stop_rgb(0, *_rgb(style.colors[0]))
    g.add_color_stop_rgb(1, *_rgb(style.colors[1]))
    cr.set_source(g)
    cr.paint()


def _shadow(cr, x, y, w, h, r, strength: float, k: float) -> None:
    """Sombra difusa aproximada por camadas de retângulos arredondados
    (o cairo não tem blur)."""
    if strength <= 0:
        return
    blur = (8 + strength * 0.9) * k
    dy = strength * 0.30 * k
    alpha = 0.10 + 0.32 * strength / 100
    per = alpha * 2.2 / SHADOW_LAYERS
    for i in range(SHADOW_LAYERS):
        t = i / (SHADOW_LAYERS - 1)
        grow = -blur * 0.25 + blur * t
        _rrect(cr, x - grow, y - grow + dy, w + 2 * grow, h + 2 * grow,
               r + max(grow, 0))
        cr.set_source_rgba(0, 0, 0, per * (1 - t) ** 1.6)
        cr.fill()


def paint(cr, img: cairo.ImageSurface, style: BgStyle, k: float = 1.0,
          bg_img: cairo.ImageSurface | None = None) -> tuple[int, int]:
    """Desenha o quadro inteiro a partir de (0, 0). `img` pode estar
    reduzida: `k` = largura dela / largura original, e todas as medidas do
    estilo (em px da original) são multiplicadas por `k`."""
    w, h = img.get_width(), img.get_height()
    W, H = canvas_size(w, h, style, k)
    _background(cr, W, H, style, bg_img)
    x, y = (W - w) / 2, (H - h) / 2
    r = style.corners * k
    _shadow(cr, x, y, w, h, r, style.shadow, k)
    cr.save()
    _rrect(cr, x, y, w, h, r)
    cr.clip()
    cr.set_source_surface(img, x, y)
    cr.paint()
    cr.restore()
    return W, H


def load_png(path: Path, work: Path, name: str,
             max_side: int | None = None) -> cairo.ImageSurface:
    """Qualquer formato -> PNG (orientação corrigida) -> superfície cairo."""
    out = work / f"{name}.png"
    args = [f"{path}[0]", "-auto-orient"]
    if max_side:
        args += ["-thumbnail", f"{max_side}x{max_side}>"]
    subprocess.run(T.cmd("magick") + [*args, "-define",
                                      "png:compression-level=1", str(out)],
                   check=True, capture_output=True, stdin=subprocess.DEVNULL)
    return cairo.ImageSurface.create_from_png(str(out))


def render_file(src: Path, out: Path, style: BgStyle, work: Path) -> None:
    img = load_png(src, work, "imagem")
    bg = None
    if style.kind == "image" and style.image:
        bg = load_png(Path(style.image), work, "fundo")
    W, H = canvas_size(img.get_width(), img.get_height(), style)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    paint(cairo.Context(surf), img, style, 1.0, bg)
    surf.write_to_png(str(out))
