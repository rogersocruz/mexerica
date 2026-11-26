"""Fundo borrado da roda feito pela própria Mexerica ("Desfoque: Próprio").

O Windows só oferece o borrão do DWM, que some (ou pinta a tela de preto)
com a transparência desligada e não deixa escolher a intensidade. Aqui a
tela é fotografada antes da roda aparecer (desktop/win32.capture) e borrada
em memória: nada vai para o disco.

O borrão é uma pirâmide (reduzir pela metade N vezes e ampliar de volta,
sempre com filtro bilinear), parecido com o dual-Kawase dos compositores:
barato até em 4K e sem precisar de numpy. Puro cairo, sem GTK.
"""
from __future__ import annotations

import math

import cairo


def levels_for(radius: float) -> int:
    """Quantas reduções pela metade dão um borrão de ~radius px."""
    if radius <= 0:
        return 0
    return max(1, min(6, round(math.log2(max(radius, 2) / 2)) + 1))


def _scaled(src: cairo.ImageSurface, w: int, h: int) -> cairo.ImageSurface:
    out = cairo.ImageSurface(cairo.FORMAT_RGB24, max(1, w), max(1, h))
    cr = cairo.Context(out)
    cr.scale(out.get_width() / src.get_width(),
             out.get_height() / src.get_height())
    cr.set_source_surface(src, 0, 0)
    pat = cr.get_source()
    pat.set_filter(cairo.FILTER_GOOD)
    pat.set_extend(cairo.EXTEND_PAD)        # bordas sem halo escuro
    cr.paint()
    return out


def blur(src: cairo.ImageSurface, radius: float) -> cairo.ImageSurface:
    """Uma versão borrada de `src`. Pode sair menor que a original: quem
    desenha amplia (paint_backdrop) e o filtro bilinear completa o borrão."""
    n = levels_for(radius)
    if n == 0:
        return src
    pyramid = [src]
    for _ in range(n):
        top = pyramid[-1]
        if top.get_width() <= 4 or top.get_height() <= 4:
            break
        pyramid.append(_scaled(top, top.get_width() // 2,
                               top.get_height() // 2))
    out = pyramid[-1]
    # sobe de volta até a metade do tamanho original: a última ampliação
    # fica para o paint, que já escala para a janela
    for level in reversed(pyramid[1:-1]):
        out = _scaled(out, level.get_width(), level.get_height())
    return out


def paint_backdrop(cr, surface: cairo.ImageSurface, w: float, h: float,
                   alpha: float = 1.0) -> None:
    """Desenha o fundo borrado cobrindo w×h."""
    cr.save()
    cr.scale(w / surface.get_width(), h / surface.get_height())
    cr.set_source_surface(surface, 0, 0)
    pat = cr.get_source()
    pat.set_filter(cairo.FILTER_GOOD)
    pat.set_extend(cairo.EXTEND_PAD)
    cr.paint_with_alpha(alpha)
    cr.restore()


__all__ = ["levels_for", "blur", "paint_backdrop"]
