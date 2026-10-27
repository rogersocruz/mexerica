"""Geometria da roda radial (puro Python, sem GTK, testável).

Até 10 itens: um anel. Mais que isso: os 10 primeiros no anel interno e o
resto no externo. O setor 0 começa no topo e segue no sentido horário.
O miolo é a zona de cancelar.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

CANCEL_R = 46.0
RINGS = ((62.0, 152.0, 10), (158.0, 240.0, 16))   # (r_in, r_out, capacidade)
SLOP = 48.0          # tolerância além do anel externo que ainda seleciona
MARGIN = 12.0


@dataclass(frozen=True)
class Sector:
    index: int
    ring: int
    r_in: float
    r_out: float
    a0: float        # radianos, 0 = leste, sentido horário (y para baixo)
    a1: float

    @property
    def mid_angle(self) -> float:
        return (self.a0 + self.a1) / 2

    @property
    def mid_radius(self) -> float:
        return (self.r_in + self.r_out) / 2


class Wheel:
    def __init__(self, n_items: int, cx: float, cy: float,
                 width: float | None = None, height: float | None = None):
        self.n = max(0, min(n_items, sum(c for _, _, c in RINGS)))
        self.sectors = self._layout(self.n)
        self.radius = self.sectors[-1].r_out if self.sectors else RINGS[0][1]
        self.cx, self.cy = self._clamp(cx, cy, width, height)

    @staticmethod
    def _layout(n: int) -> list[Sector]:
        sectors: list[Sector] = []
        remaining, idx = n, 0
        for ring, (r_in, r_out, cap) in enumerate(RINGS):
            count = min(remaining, cap)
            if count <= 0:
                break
            step = 2 * math.pi / count
            start = -math.pi / 2 - step / 2      # setor 0 centrado no topo
            for i in range(count):
                a0 = start + i * step
                sectors.append(Sector(idx, ring, r_in, r_out, a0, a0 + step))
                idx += 1
            remaining -= count
        return sectors

    def _clamp(self, cx, cy, w, h):
        r = self.radius + MARGIN
        if w is not None and w > 2 * r:
            cx = min(max(cx, r), w - r)
        if h is not None and h > 2 * r:
            cy = min(max(cy, r), h - r)
        return cx, cy

    def hit(self, x: float, y: float) -> int | None:
        """Índice do item sob (x, y); None no miolo ou longe da roda."""
        dx, dy = x - self.cx, y - self.cy
        dist = math.hypot(dx, dy)
        if dist < CANCEL_R or not self.sectors:
            return None
        if dist > self.radius + SLOP:
            return None
        ang = math.atan2(dy, dx)
        n_rings = self.sectors[-1].ring + 1
        # anel: pelo raio (entre anéis, o mais próximo)
        if n_rings == 1 or dist < (RINGS[0][1] + RINGS[1][0]) / 2:
            ring = 0
        else:
            ring = 1
        for s in self.sectors:
            if s.ring == ring and _angle_in(ang, s.a0, s.a1):
                return s.index
        return None

    def in_cancel(self, x: float, y: float) -> bool:
        return math.hypot(x - self.cx, y - self.cy) < CANCEL_R


def _angle_in(a: float, a0: float, a1: float) -> bool:
    two_pi = 2 * math.pi
    a = (a - a0) % two_pi
    return a < (a1 - a0) or math.isclose(a, a1 - a0)
