"""Desenho da roda com cairo + Pango.

Recebe um contexto cairo já posicionado na janela; não depende de GTK, então
o mesmo código desenha na janela overlay e em PNG para teste/screenshot.
Cores e medidas: mexerica/theme.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cairo
import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # noqa: E402

from .. import theme as TH  # noqa: E402
from .geometry import Wheel  # noqa: E402
from .icons import draw_icon  # noqa: E402

_R = TH.WHEEL_R


@dataclass
class Snapshot:
    """Conteúdo de uma roda, para o crossfade ao trocar de modo."""
    wheel: Wheel
    labels: list[str]
    icons: list[str | None]


@dataclass
class WheelState:
    mode: str = "convert"
    labels: list[str] = field(default_factory=list)
    icons: list[str | None] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    caption: str = ""               # miolo sem hover: "1.1 MB"
    hover: int | None = None
    cancel_hover: bool = False
    loading: bool = False
    progress: float = 1.0           # entrada 0..1 (linear; a curva é aqui)
    hover_t: dict[int, float] = field(default_factory=dict)  # 0..1 por setor
    fade: float = 1.0               # troca de modo 0..1
    prev: Snapshot | None = None    # conteúdo anterior, sumindo


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# --------------------------------------------------------------------------
# Texto
# --------------------------------------------------------------------------

def _layout(cr, text: str, px: float, weight: int, tracking: float = 0.0,
            max_w: float | None = None):
    layout = PangoCairo.create_layout(cr)
    desc = Pango.FontDescription.from_string(TH.FONT_FAMILY)
    desc.set_absolute_size(px * Pango.SCALE)
    desc.set_weight(Pango.Weight(weight))
    layout.set_font_description(desc)
    layout.set_alignment(Pango.Alignment.CENTER)
    if tracking:
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_letter_spacing_new(int(tracking * Pango.SCALE)))
        layout.set_attributes(attrs)
    if max_w:
        layout.set_width(int(max_w * Pango.SCALE))
        layout.set_wrap(Pango.WrapMode.WORD)
        layout.set_ellipsize(Pango.EllipsizeMode.END)
        layout.set_height(-2)
    layout.set_text(text, -1)
    return layout


def _fit(cr, text: str, px: float, min_px: float, weight: int,
         tracking: float, max_w: float):
    """Maior tamanho (até px) em que o texto cabe numa linha; se nem no
    mínimo couber, quebra em até 2 linhas."""
    size = px
    while size >= min_px:
        lay = _layout(cr, text, size, weight, tracking)
        if lay.get_pixel_extents()[1].width <= max_w:
            return lay
        size -= 0.5
    return _layout(cr, text, min_px, weight, tracking, max_w=max_w)


def _show(cr, layout, x: float, y: float, color) -> None:
    """Centraliza o layout em (x, y)."""
    _ink, logical = layout.get_pixel_extents()
    cr.set_source_rgba(*color)
    cr.move_to(x - logical.width / 2 - logical.x, y - logical.height / 2)
    PangoCairo.show_layout(cr, layout)


def _mix(a, b, t: float):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


# --------------------------------------------------------------------------
# Formas
# --------------------------------------------------------------------------

def _rounded_rect(cr, x, y, w, h, r) -> None:
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def _short_arc(cr, c, r, p_from, p_to) -> None:
    """Arco de concordância de p_from a p_to pelo caminho mais curto."""
    a0 = math.atan2(p_from[1] - c[1], p_from[0] - c[0])
    a1 = math.atan2(p_to[1] - c[1], p_to[0] - c[0])
    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    if d >= 0:
        cr.arc(c[0], c[1], r, a0, a0 + d)
    else:
        cr.arc_negative(c[0], c[1], r, a0, a0 + d)


def _fillet(u, n, d, rc, radius, outer):
    """Círculo de raio rc tangente à borda lateral (reta paralela ao raio u,
    deslocada d na direção n) e ao círculo `radius` (por dentro se outer).
    Devolve (centro, toque na borda, toque no círculo), relativos ao centro
    da roda."""
    rr = radius - rc if outer else radius + rc
    off = d + rc
    s = math.sqrt(max(rr * rr - off * off, 0.0))
    c = (s * u[0] + off * n[0], s * u[1] + off * n[1])
    side = (s * u[0] + d * n[0], s * u[1] + d * n[1])
    k = radius / rr
    circ = (c[0] * k, c[1] * k)
    return c, side, circ


def _pill_sector(cr, cx, cy, r_in, r_out, a0, a1, gap, corner) -> None:
    """Setor anelar com cantos arredondados e folga constante `gap` px
    entre vizinhos (bordas paralelas, não radiais)."""
    cr.new_path()
    if a1 - a0 >= 2 * math.pi - 1e-6:            # um item: anel inteiro
        cr.arc(cx, cy, r_out, 0, 2 * math.pi)
        cr.new_sub_path()
        cr.arc_negative(cx, cy, r_in, 2 * math.pi, 0)
        cr.close_path()
        return
    d = gap / 2
    inner_span = (a1 - a0) * r_in - gap
    rc = max(1.0, min(corner, (r_out - r_in) / 2 - 0.5, inner_span / 2 - 0.5))
    u0 = (math.cos(a0), math.sin(a0))
    n0 = (-math.sin(a0), math.cos(a0))          # para dentro do setor
    u1 = (math.cos(a1), math.sin(a1))
    n1 = (math.sin(a1), -math.cos(a1))
    A = _fillet(u0, n0, d, rc, r_out, True)
    B = _fillet(u1, n1, d, rc, r_out, True)
    C = _fillet(u1, n1, d, rc, r_in, False)
    D = _fillet(u0, n0, d, rc, r_in, False)

    def P(p):
        return (cx + p[0], cy + p[1])

    cr.move_to(*P(A[1]))
    _short_arc(cr, P(A[0]), rc, P(A[1]), P(A[2]))
    aa = math.atan2(A[2][1], A[2][0])
    ab = math.atan2(B[2][1], B[2][0])
    while ab < aa:
        ab += 2 * math.pi
    cr.arc(cx, cy, r_out, aa, ab)
    _short_arc(cr, P(B[0]), rc, P(B[2]), P(B[1]))
    cr.line_to(*P(C[1]))
    _short_arc(cr, P(C[0]), rc, P(C[1]), P(C[2]))
    ac = math.atan2(C[2][1], C[2][0])
    ad = math.atan2(D[2][1], D[2][0])
    while ad > ac:
        ad -= 2 * math.pi
    cr.arc_negative(cx, cy, r_in, ac, ad)
    _short_arc(cr, P(D[0]), rc, P(D[2]), P(D[1]))
    cr.close_path()


# --------------------------------------------------------------------------
# Partes da roda
# --------------------------------------------------------------------------

def _shadow(cr, cx, cy, rim) -> None:
    sx, sy = cx, cy + TH.SHADOW_DY
    g = cairo.RadialGradient(sx, sy, max(rim - TH.SHADOW_BLUR / 2, 0),
                             sx, sy, rim + TH.SHADOW_BLUR)
    g.add_color_stop_rgba(0.0, *TH.SHADOW)
    g.add_color_stop_rgba(1.0, *TH.SHADOW[:3], 0.0)
    cr.arc(sx, sy, rim + TH.SHADOW_BLUR, 0, 2 * math.pi)
    cr.set_source(g)
    cr.fill()


def _rim(cr, cx, cy, rim) -> None:
    cr.arc(cx, cy, rim, 0, 2 * math.pi)
    cr.set_source_rgba(*TH.RIM_FILL)
    cr.fill_preserve()
    cr.set_source_rgba(*TH.RIM_STROKE)
    cr.set_line_width(TH.RIM_STROKE_W)
    cr.stroke()


def _sectors(cr, wheel: Wheel, labels, icons, hover_t: dict) -> None:
    cx, cy = wheel.cx, wheel.cy
    top, bottom = cy - wheel.rim, cy + wheel.rim
    rest = cairo.LinearGradient(0, top, 0, bottom)
    rest.add_color_stop_rgba(0, *TH.SECTOR_TOP)
    rest.add_color_stop_rgba(1, *TH.SECTOR_BOTTOM)
    for s in wheel.sectors:
        t = _ease(hover_t.get(s.index, 0.0))
        r_out = s.r_out * (1 + TH.HOVER_GROW * t)
        _pill_sector(cr, cx, cy, s.r_in, r_out, s.a0, s.a1, TH.SECTOR_GAP,
                     TH.SECTOR_CORNER)
        cr.set_source(rest)
        cr.fill_preserve()
        if t > 0:
            ext = cr.fill_extents()
            hot = cairo.LinearGradient(0, ext[1], 0, ext[3])
            hot.add_color_stop_rgba(0, *TH.HOVER_TOP[:3], t)
            hot.add_color_stop_rgba(1, *TH.HOVER_BOTTOM[:3], t)
            cr.set_source(hot)
            cr.fill_preserve()
        cr.set_source_rgba(*TH.SECTOR_EDGE[:3], TH.SECTOR_EDGE[3] * (1 - t))
        cr.set_line_width(1.0)
        cr.stroke()

        label = labels[s.index] if s.index < len(labels) else "?"
        icon = icons[s.index] if s.index < len(icons) else None
        color = _mix(TH.LABEL_COLOR, TH.LABEL_HOVER, t)
        mid_r = (s.r_in + r_out) / 2
        mx = cx + math.cos(s.mid_angle) * mid_r
        my = cy + math.sin(s.mid_angle) * mid_r
        arc_w = (s.a1 - s.a0) * mid_r - TH.SECTOR_GAP - 10
        max_w = max(min(arc_w, (r_out - s.r_in) * 1.25, 96), 24)
        lay = _fit(cr, label.upper(), TH.LABEL_PX, TH.LABEL_MIN_PX,
                   TH.LABEL_WEIGHT, TH.LABEL_TRACKING, max_w)
        th = lay.get_pixel_extents()[1].height
        if icon:
            block = TH.ICON_PX + TH.ICON_GAP + th
            top_y = my - block / 2
            draw_icon(cr, icon, mx - TH.ICON_PX / 2, top_y, TH.ICON_PX,
                      color, TH.ICON_STROKE)
            _show(cr, lay, mx, top_y + TH.ICON_PX + TH.ICON_GAP + th / 2,
                  color)
        else:
            _show(cr, lay, mx, my, color)


def _empty_band(cr, wheel: Wheel) -> None:
    from .geometry import RINGS
    cr.new_path()
    cr.arc(wheel.cx, wheel.cy, RINGS[0][1], 0, 2 * math.pi)
    cr.new_sub_path()
    cr.arc_negative(wheel.cx, wheel.cy, RINGS[0][0], 2 * math.pi, 0)
    cr.set_source_rgba(*TH.SECTOR_BOTTOM[:3], TH.SECTOR_BOTTOM[3] * 0.6)
    cr.fill()


def _core(cr, wheel: Wheel, st: WheelState) -> None:
    cx, cy = wheel.cx, wheel.cy
    cr.new_path()
    cr.arc(cx, cy, TH.CORE_RING_OUT * _R, 0, 2 * math.pi)
    cr.new_sub_path()
    cr.arc_negative(cx, cy, TH.CORE_RING_IN * _R, 2 * math.pi, 0)
    cr.set_source_rgba(*TH.CORE_RING)
    cr.fill()
    pw, ph = TH.CORE_PILL_W * _R, TH.CORE_PILL_H * _R
    _rounded_rect(cr, cx - pw / 2, cy - ph / 2, pw, ph, ph / 2)
    cr.set_source_rgba(*TH.CORE_PILL)
    cr.fill()

    if st.cancel_hover:
        text = "CANCEL"
    elif st.hover is not None and st.hover < len(st.labels):
        text = st.labels[st.hover]
    elif st.loading:
        text = "…"
    elif not wheel.sectors:
        text = "NO OPTIONS"
    else:
        text = st.caption
    if text:
        lay = _fit(cr, text.upper(), TH.CORE_PX, 7.5, TH.CORE_WEIGHT,
                   TH.LABEL_TRACKING, pw - 14)
        _show(cr, lay, cx, cy, TH.CORE_COLOR)


def draw_disc(cr, cx: float, cy: float, r: float,
              hover: float = 0.0) -> None:
    """Bolha da janela Flutuar, no vidro da roda: sombra curta, disco quase
    opaco (sem borrão atrás, para ler sobre qualquer fundo), aro e, com o
    ponteiro em cima, um anel na cor do estilo."""
    blur, dy = 12.0, 3.0
    g = cairo.RadialGradient(cx, cy + dy, r - blur / 2, cx, cy + dy, r + blur)
    g.add_color_stop_rgba(0, *TH.SHADOW[:3], TH.SHADOW[3] * 1.4)
    g.add_color_stop_rgba(1, *TH.SHADOW[:3], 0.0)
    cr.arc(cx, cy + dy, r + blur, 0, 2 * math.pi)
    cr.set_source(g)
    cr.fill()
    fill = cairo.LinearGradient(0, cy - r, 0, cy + r)
    fill.add_color_stop_rgba(0, *TH.SECTOR_TOP[:3], 0.94)
    fill.add_color_stop_rgba(1, *TH.SECTOR_BOTTOM[:3], 0.90)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.set_source(fill)
    cr.fill_preserve()
    cr.set_source_rgba(*TH.RIM_STROKE)
    cr.set_line_width(TH.RIM_STROKE_W)
    cr.stroke()
    if hover > 0:
        cr.arc(cx, cy, r - 2.5, 0, 2 * math.pi)
        cr.set_source_rgba(*TH.HOVER_TOP[:3], hover)
        cr.set_line_width(3)
        cr.stroke()


# --------------------------------------------------------------------------

def draw(cr, wheel: Wheel, st: WheelState) -> None:
    cx, cy = wheel.cx, wheel.cy
    ease = _ease(st.progress)
    scale = TH.ENTER_SCALE + (1 - TH.ENTER_SCALE) * ease
    cr.save()
    cr.translate(cx, cy)
    cr.scale(scale, scale)
    cr.translate(-cx, -cy)
    cr.push_group()

    rim = wheel.rim
    if st.prev is not None and st.fade < 1:
        rim = max(rim, st.prev.wheel.rim)
    _shadow(cr, cx, cy, rim)
    _rim(cr, cx, cy, rim)

    fade = _ease(st.fade)
    if st.prev is not None and fade < 1:
        cr.push_group()
        _sectors(cr, st.prev.wheel, st.prev.labels, st.prev.icons, {})
        cr.pop_group_to_source()
        cr.paint_with_alpha(1 - fade)
    if wheel.sectors:
        cr.push_group()
        _sectors(cr, wheel, st.labels, st.icons, st.hover_t)
        cr.pop_group_to_source()
        cr.paint_with_alpha(fade if st.prev is not None else 1.0)
    elif st.prev is None or fade >= 1:
        _empty_band(cr, wheel)

    _core(cr, wheel, st)

    cr.pop_group_to_source()
    cr.paint_with_alpha(ease)
    cr.restore()
