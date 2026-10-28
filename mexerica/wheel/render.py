"""Desenho da roda com cairo + Pango.

Recebe um contexto cairo já posicionado na janela; não depende de GTK, então
o mesmo código desenha na janela overlay e em PNG para teste/screenshot.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cairo
import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # noqa: E402

from .geometry import CANCEL_R, Wheel  # noqa: E402

ACCENT = {
    "convert": (1.00, 0.54, 0.12),   # mexerica
    "tools": (0.18, 0.77, 0.71),     # verde-água
    "actions": (0.61, 0.36, 0.90),   # roxo
}
TITLE = {"convert": "Converter", "tools": "Ferramentas", "actions": "Ações"}

# Vidro: tinta escura translúcida + brilho branco por cima. O borrão do
# fundo vem da extensão (Shell.BlurEffect); a tinta é leve para ele aparecer.
GLASS = (0.10, 0.10, 0.14, 0.26)
GLASS_ALT = (0.10, 0.10, 0.14, 0.34)
SHEEN = (1.0, 1.0, 1.0)
EDGE = (1.0, 1.0, 1.0, 0.28)
FG = (0.98, 0.98, 0.98)
FG_DIM = (0.82, 0.82, 0.85)


@dataclass
class WheelState:
    mode: str = "convert"
    labels: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    caption: str = ""               # "3 arquivos", "foto.png"
    hover: int | None = None
    cancel_hover: bool = False
    loading: bool = False
    progress: float = 1.0           # animação de entrada 0..1


def _text(cr, txt: str, x: float, y: float, size: float, bold=False,
          color=FG, max_w: float | None = None, shadow=True):
    layout = PangoCairo.create_layout(cr)
    desc = Pango.FontDescription.from_string(
        f"Sans {'Bold ' if bold else ''}{size}")
    layout.set_font_description(desc)
    layout.set_alignment(Pango.Alignment.CENTER)
    if max_w:
        layout.set_width(int(max_w * Pango.SCALE))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        layout.set_ellipsize(Pango.EllipsizeMode.END)
        layout.set_height(-2)          # no máximo 2 linhas
    layout.set_text(txt, -1)
    _, logical = layout.get_pixel_extents()
    tx, ty = x - logical.width / 2 - logical.x, y - logical.height / 2
    if shadow:          # contorno suave: legível sobre qualquer fundo
        cr.set_source_rgba(0, 0, 0, 0.45)
        cr.move_to(tx, ty + 1)
        PangoCairo.show_layout(cr, layout)
    cr.set_source_rgb(*color)
    cr.move_to(tx, ty)
    PangoCairo.show_layout(cr, layout)


def _sector_path(cr, cx, cy, s, gap=0.012):
    a0, a1 = s.a0 + gap, s.a1 - gap
    cr.new_path()
    cr.arc(cx, cy, s.r_out, a0, a1)
    cr.arc_negative(cx, cy, s.r_in, a1, a0)
    cr.close_path()


def _glass(cr, cx, cy, r_in, r_out, tint, extent=None):
    """Preenche o caminho atual como vidro: tinta + reflexo diagonal.

    `extent` = (r_in, r_out) do anel inteiro, para o reflexo ser contínuo
    entre setores vizinhos.
    """
    r_in, r_out = extent or (r_in, r_out)
    cr.set_source_rgba(*tint)
    cr.fill_preserve()
    # reflexo: mais claro em cima à esquerda, some no meio
    lg = cairo.LinearGradient(cx - r_out, cy - r_out, cx + r_out, cy + r_out)
    lg.add_color_stop_rgba(0.0, *SHEEN, 0.26)
    lg.add_color_stop_rgba(0.45, *SHEEN, 0.08)
    lg.add_color_stop_rgba(1.0, *SHEEN, 0.0)
    cr.set_source(lg)
    cr.fill_preserve()
    # luz na borda interna/externa (efeito de espessura)
    rg = cairo.RadialGradient(cx, cy, r_in, cx, cy, r_out)
    rg.add_color_stop_rgba(0.0, *SHEEN, 0.07)
    rg.add_color_stop_rgba(0.5, *SHEEN, 0.0)
    rg.add_color_stop_rgba(1.0, *SHEEN, 0.09)
    cr.set_source(rg)
    cr.fill()


def _ring_edge(cr, cx, cy, r, alpha=1.0):
    """Fio de luz: forte no topo, fraco embaixo."""
    lg = cairo.LinearGradient(cx, cy - r, cx, cy + r)
    lg.add_color_stop_rgba(0.0, *EDGE[:3], EDGE[3] * 1.6 * alpha)
    lg.add_color_stop_rgba(1.0, *EDGE[:3], EDGE[3] * 0.35 * alpha)
    cr.new_path()
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.set_line_width(1.0)
    cr.set_source(lg)
    cr.stroke()


def draw(cr, wheel: Wheel, st: WheelState) -> None:
    accent = ACCENT.get(st.mode, ACCENT["convert"])
    cx, cy = wheel.cx, wheel.cy
    p = max(0.0, min(1.0, st.progress))
    ease = 1 - (1 - p) ** 3
    cr.save()
    cr.translate(cx, cy)
    cr.scale(0.85 + 0.15 * ease, 0.85 + 0.15 * ease)
    cr.translate(-cx, -cy)
    cr.push_group()

    outer = wheel.radius if wheel.sectors else 152.0
    inner = wheel.sectors[0].r_in if wheel.sectors else CANCEL_R + 16
    # sombra difusa
    for i in range(8):
        cr.arc(cx, cy + 6, outer + 1 + i * 2.5, 0, 2 * math.pi)
        cr.set_source_rgba(0, 0, 0, 0.035)
        cr.fill()

    if not wheel.sectors:
        cr.arc(cx, cy, outer, 0, 2 * math.pi)
        cr.arc_negative(cx, cy, inner, 2 * math.pi, 0)
        _glass(cr, cx, cy, inner, outer, GLASS)
        msg = "Lendo arquivos…" if st.loading else "Nada para este tipo"
        _text(cr, msg, cx, cy - outer + 45, 10, color=FG_DIM, max_w=180)

    for s in wheel.sectors:
        hovered = s.index == st.hover
        _sector_path(cr, cx, cy, s)
        tint = GLASS if s.index % 2 == 0 else GLASS_ALT
        _glass(cr, cx, cy, s.r_in, s.r_out, tint,
               extent=(inner, outer))
        if hovered:
            # vidro colorido: brilho da cor de destaque + fio aceso
            _sector_path(cr, cx, cy, s)
            rg = cairo.RadialGradient(cx, cy, s.r_in, cx, cy, s.r_out)
            rg.add_color_stop_rgba(0.0, *accent, 0.55)
            rg.add_color_stop_rgba(1.0, *accent, 0.85)
            cr.set_source(rg)
            cr.fill_preserve()
            cr.set_source_rgba(*accent, 1.0)
            cr.set_line_width(1.5)
            cr.stroke()
        else:
            _sector_path(cr, cx, cy, s)
            cr.set_source_rgba(*EDGE[:3], 0.12)
            cr.set_line_width(1.0)
            cr.stroke()
        label = st.labels[s.index] if s.index < len(st.labels) else "?"
        mx = cx + math.cos(s.mid_angle) * s.mid_radius
        my = cy + math.sin(s.mid_angle) * s.mid_radius
        arc_len = (s.a1 - s.a0) * s.mid_radius
        width = min(arc_len * 0.9, (s.r_out - s.r_in) * 1.1, 96)
        size = 11 if len(label) <= 5 else 9
        _text(cr, label, mx, my, size, bold=hovered or len(label) <= 5,
              color=FG, max_w=width)

    # bordas de luz do anel
    _ring_edge(cr, cx, cy, outer)
    _ring_edge(cr, cx, cy, inner, alpha=0.6)

    # miolo: lente de vidro com aro na cor do modo
    core = CANCEL_R + 12
    cr.arc(cx, cy, core, 0, 2 * math.pi)
    _glass(cr, cx, cy, 0, core, (0.08, 0.08, 0.10, 0.55))
    if st.cancel_hover:
        cr.arc(cx, cy, core, 0, 2 * math.pi)
        cr.set_source_rgba(0.90, 0.25, 0.25, 0.35)
        cr.fill()
    cr.arc(cx, cy, core, 0, 2 * math.pi)
    cr.set_line_width(2.0)
    cr.set_source_rgba(*accent, 0.9)
    cr.stroke()
    _ring_edge(cr, cx, cy, core - 2.5, alpha=0.7)

    if st.cancel_hover:
        _text(cr, "✕", cx, cy - 6, 18, bold=True, color=FG)
        _text(cr, "cancelar", cx, cy + 16, 8, color=FG_DIM)
    elif st.hover is not None and st.hover < len(st.labels):
        hint = st.hints[st.hover] if st.hover < len(st.hints) else ""
        _text(cr, st.labels[st.hover], cx, cy - (7 if hint else 0), 10,
              bold=True, color=accent, max_w=(CANCEL_R + 6) * 2)
        if hint:
            _text(cr, hint, cx, cy + 13, 7, color=FG_DIM,
                  max_w=(CANCEL_R + 4) * 2)
    else:
        _text(cr, TITLE.get(st.mode, ""), cx, cy - 8, 9, bold=True,
              color=accent)
        _text(cr, st.caption, cx, cy + 10, 7.5, color=FG_DIM,
              max_w=(CANCEL_R + 4) * 2)

    cr.pop_group_to_source()
    cr.paint_with_alpha(ease)
    cr.restore()
