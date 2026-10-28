"""Matemática do retângulo de recorte (puro Python, sem GTK).

Tudo em coordenadas normalizadas (0..1) sobre a imagem como ela aparece.
A proporção pedida está em pixels (16:9 = 1.777); `img_w/img_h` convertem
para as unidades normalizadas.
"""
from __future__ import annotations

MIN_CROP = 0.02          # menor recorte (fração da imagem)

Rect = list[float]       # [x, y, w, h]


def norm_ratio(ratio_px: float | None, img_w: float, img_h: float):
    """w/h do recorte em unidades normalizadas, ou None (livre)."""
    if not ratio_px:
        return None
    return ratio_px * img_h / img_w


def largest_centered(ratio_px: float | None, img_w: float,
                     img_h: float) -> Rect:
    """Maior recorte centrado com a proporção pedida."""
    k = norm_ratio(ratio_px, img_w, img_h)
    if not k:
        return [0.0, 0.0, 1.0, 1.0]
    w, h = (1.0, 1.0 / k) if k >= 1 else (k, 1.0)
    if h > 1:
        w, h = w / h, 1.0
    if w > 1:
        w, h = 1.0, h / w
    return [(1 - w) / 2, (1 - h) / 2, w, h]


def resized(mode: str, start: Rect, ndx: float, ndy: float,
            k: float | None) -> Rect:
    """Puxa um canto/borda (`mode` em n, s, e, w, ne, ...) de `start` por
    (ndx, ndy), mantendo a proporção `k` (normalizada) se houver."""
    x0, y0, w0, h0 = start
    l, t, r, b = x0, y0, x0 + w0, y0 + h0
    if "w" in mode:
        l = min(l + ndx, r - MIN_CROP)
    if "e" in mode:
        r = max(r + ndx, l + MIN_CROP)
    if "n" in mode:
        t = min(t + ndy, b - MIN_CROP)
    if "s" in mode:
        b = max(b + ndy, t + MIN_CROP)
    l, t, r, b = max(l, 0.0), max(t, 0.0), min(r, 1.0), min(b, 1.0)
    if not k:
        return [l, t, r - l, b - t]
    w, h = r - l, b - t
    if mode in ("n", "s"):
        w = h * k
    elif mode in ("e", "w"):
        h = w / k
    elif w / h > k:
        w = h * k
    else:
        h = w / k
    # ponto fixo: o lado/canto oposto ao que está sendo puxado
    ax = r if "w" in mode else l if "e" in mode else (l + r) / 2
    ay = b if "n" in mode else t if "s" in mode else (t + b) / 2
    avail_w = ax if "w" in mode else 1 - ax if "e" in mode \
        else 2 * min(ax, 1 - ax)
    avail_h = ay if "n" in mode else 1 - ay if "s" in mode \
        else 2 * min(ay, 1 - ay)
    f = min(1.0, avail_w / w if w else 1, avail_h / h if h else 1)
    w, h = w * f, h * f
    x = ax - w if "w" in mode else ax if "e" in mode else ax - w / 2
    y = ay - h if "n" in mode else ay if "s" in mode else ay - h / 2
    return [x, y, w, h]


def moved(start: Rect, ndx: float, ndy: float) -> Rect:
    x = min(max(start[0] + ndx, 0.0), 1 - start[2])
    y = min(max(start[1] + ndy, 0.0), 1 - start[3])
    return [x, y, start[2], start[3]]


def with_size_px(rect: Rect, w_px: float, h_px: float, img_w: float,
                 img_h: float) -> Rect:
    """Novo tamanho em pixels, mantendo o centro e dentro da imagem."""
    w = min(max(w_px / img_w, MIN_CROP), 1.0)
    h = min(max(h_px / img_h, MIN_CROP), 1.0)
    cx, cy = rect[0] + rect[2] / 2, rect[1] + rect[3] / 2
    x = min(max(cx - w / 2, 0.0), 1 - w)
    y = min(max(cy - h / 2, 0.0), 1 - h)
    return [x, y, w, h]


def rotated(rect: Rect, deg: int) -> Rect:
    """O mesmo recorte depois de girar a imagem 90° (horário se > 0)."""
    x, y, w, h = rect
    return [1 - y - h, x, h, w] if deg > 0 else [y, 1 - x - w, h, w]


def flipped(rect: Rect, horizontal: bool) -> Rect:
    x, y, w, h = rect
    return [1 - x - w, y, w, h] if horizontal else [x, 1 - y - h, w, h]


def is_full(rect: Rect) -> bool:
    x, y, w, h = rect
    return x < 1e-4 and y < 1e-4 and w > 1 - 1e-4 and h > 1 - 1e-4
