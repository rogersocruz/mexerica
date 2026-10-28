"""Ícones de linha da roda, desenhados com cairo numa caixa de 16×16.

Desenhados aqui (e não lidos do tema de ícones) para ficarem iguais em
qualquer distro e sem GTK: o Adwaita não tem, por exemplo, crop nem tag.
Quem chama define a cor e a posição; cada função só traça o caminho.
"""
from __future__ import annotations

import math

TAU = 2 * math.pi


def _rrect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def _line(cr, *pts):
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)


def _arrow_head(cr, x, y, dx, dy, size=3.0):
    """Ponta em V no ponto (x, y) apontando na direção (dx, dy)."""
    n = math.hypot(dx, dy) or 1
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    _line(cr, (x - ux * size + px * size, y - uy * size + py * size), (x, y),
          (x - ux * size - px * size, y - uy * size - py * size))


def crop(cr):
    _line(cr, (4, 1), (4, 12), (15, 12))
    _line(cr, (1, 4), (12, 4), (12, 15))


def compress(cr):
    _line(cr, (2, 2), (6.5, 6.5))
    _arrow_head(cr, 6.5, 6.5, 1, 1)
    _line(cr, (14, 14), (9.5, 9.5))
    _arrow_head(cr, 9.5, 9.5, -1, -1)


def resize(cr):
    _rrect(cr, 1.5, 6.5, 8, 8, 1.5)
    _line(cr, (8, 8), (14, 2))
    _line(cr, (10, 2), (14, 2), (14, 6))


def tag(cr):
    _line(cr, (1.5, 2.5), (1.5, 8), (8.5, 15), (15, 8.5), (8, 1.5),
          (2.5, 1.5))
    cr.close_path()
    cr.new_sub_path()
    cr.arc(5, 5, 1.2, 0, TAU)


def sliders(cr):
    for y, x in ((3, 10), (8, 5), (13, 11)):
        _line(cr, (1.5, y), (x - 2, y))
        _line(cr, (x + 2, y), (14.5, y))
        cr.new_sub_path()
        cr.arc(x, y, 2, 0, TAU)


def image(cr):
    _rrect(cr, 1.5, 2.5, 13, 11, 2)
    _line(cr, (2, 12), (6, 8), (9, 11), (11, 9), (14, 12))
    cr.new_sub_path()
    cr.arc(10.5, 6, 1.3, 0, TAU)


def eye_off(cr):
    cr.move_to(1.5, 8)
    cr.curve_to(4, 3.5, 12, 3.5, 14.5, 8)
    cr.curve_to(12, 12.5, 4, 12.5, 1.5, 8)
    cr.new_sub_path()
    cr.arc(8, 8, 2.2, 0, TAU)
    _line(cr, (2.5, 14), (13.5, 2))


def rotate(cr):
    cr.new_sub_path()
    cr.arc(8, 8.5, 5.5, math.radians(200), math.radians(500))
    _arrow_head(cr, 2.9, 6.6, -0.2, -1, 2.6)


def scissors(cr):
    for cy in (4, 12):
        cr.new_sub_path()
        cr.arc(3.5, cy, 2.2, 0, TAU)
    _line(cr, (5.5, 5.2), (14.5, 12))
    _line(cr, (5.5, 10.8), (14.5, 4))


def qr(cr):
    for x, y in ((1.5, 1.5), (9.5, 1.5), (1.5, 9.5)):
        _rrect(cr, x, y, 5, 5, 1)
    _line(cr, (10, 10), (10, 14.5))
    _line(cr, (12.5, 10), (14.5, 10))
    _line(cr, (12.5, 12.5), (12.5, 14.5), (14.5, 14.5))


def doc(cr):
    _line(cr, (3, 1.5), (10, 1.5), (13, 4.5), (13, 14.5), (3, 14.5))
    cr.close_path()
    _line(cr, (5.5, 8), (10.5, 8))
    _line(cr, (5.5, 11), (10.5, 11))


def pages(cr):
    _rrect(cr, 4.5, 1.5, 10, 11, 1.5)
    _line(cr, (2, 4), (2, 14.5), (11.5, 14.5))


def grid(cr):
    for x, y in ((1.5, 1.5), (9, 1.5), (1.5, 9), (9, 9)):
        _rrect(cr, x, y, 5.5, 5.5, 1)


def split(cr):
    _line(cr, (8, 1.5), (8, 14.5))
    _rrect(cr, 1.5, 3.5, 4, 9, 1)
    _rrect(cr, 10.5, 3.5, 4, 9, 1)


def merge(cr):
    _line(cr, (2, 2), (8, 8), (14, 8))
    _line(cr, (2, 14), (8, 8))
    _arrow_head(cr, 14, 8, 1, 0)


def mute(cr):
    _line(cr, (1.5, 6), (4.5, 6), (8.5, 2.5), (8.5, 13.5), (4.5, 10),
          (1.5, 10))
    cr.close_path()
    _line(cr, (11, 6), (15, 10))
    _line(cr, (15, 6), (11, 10))


def speed(cr):
    for x in (1.5, 8):
        _line(cr, (x, 3), (x + 6, 8), (x, 13))
        cr.close_path()


def camera(cr):
    _rrect(cr, 1.5, 4.5, 13, 9.5, 2)
    _line(cr, (5.5, 4.5), (6.5, 2.5), (9.5, 2.5), (10.5, 4.5))
    cr.new_sub_path()
    cr.arc(8, 9.2, 2.5, 0, TAU)


def wave(cr):
    for x, h in ((2, 3), (5, 8), (8, 12), (11, 7), (14, 4)):
        _line(cr, (x, 8 - h / 2), (x, 8 + h / 2))


def link(cr):
    _rrect(cr, 1.5, 5.5, 7, 5, 2.5)
    _rrect(cr, 7.5, 5.5, 7, 5, 2.5)


def terminal(cr):
    _rrect(cr, 1.5, 2.5, 13, 11, 2)
    _line(cr, (4.5, 6), (6.5, 8), (4.5, 10))
    _line(cr, (8, 10.5), (11.5, 10.5))


def copy(cr):
    _rrect(cr, 5, 5, 9.5, 9.5, 1.5)
    _line(cr, (11, 2.5), (11, 1.5), (1.5, 1.5), (1.5, 11), (2.5, 11))


def move(cr):
    _line(cr, (1.5, 8), (13.5, 8))
    _arrow_head(cr, 14, 8, 1, 0, 3.5)


def pin(cr):
    _line(cr, (5, 1.5), (11, 1.5))
    _line(cr, (6, 1.5), (6, 6.5), (3.5, 9.5), (12.5, 9.5), (10, 6.5),
          (10, 1.5))
    _line(cr, (8, 9.5), (8, 14.5))


def archive(cr):
    _rrect(cr, 1.5, 2, 13, 4, 1)
    _line(cr, (2.5, 6), (2.5, 14), (13.5, 14), (13.5, 6))
    _line(cr, (6.5, 9), (9.5, 9))


def eraser(cr):
    _line(cr, (9.5, 2), (14.5, 7), (7.5, 14), (4, 14), (1.5, 11.5))
    cr.close_path()
    _line(cr, (5.5, 6), (10.5, 11))
    _line(cr, (7.5, 14), (14.5, 14))


ICONS = {
    "crop": crop, "compress": compress, "resize": resize, "tag": tag,
    "sliders": sliders, "image": image, "eye-off": eye_off,
    "rotate": rotate, "scissors": scissors, "qr": qr, "doc": doc,
    "pages": pages, "grid": grid, "split": split, "merge": merge,
    "mute": mute, "speed": speed, "camera": camera, "wave": wave,
    "link": link, "terminal": terminal, "copy": copy, "move": move,
    "pin": pin, "archive": archive, "eraser": eraser,
}


def draw_icon(cr, name: str, x: float, y: float, size: float,
              color: tuple, stroke: float) -> bool:
    """Desenha o ícone com o canto superior esquerdo em (x, y)."""
    fn = ICONS.get(name)
    if fn is None:
        return False
    cr.save()
    cr.translate(x, y)
    cr.scale(size / 16, size / 16)
    cr.new_path()
    fn(cr)
    cr.restore()
    cr.save()
    cr.set_source_rgba(*color)
    cr.set_line_width(stroke)
    cr.set_line_cap(1)    # ROUND
    cr.set_line_join(1)   # ROUND
    cr.stroke()
    cr.restore()
    return True
