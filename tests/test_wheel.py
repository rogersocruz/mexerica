import math

import pytest

from mexerica.wheel.geometry import CANCEL_R, RINGS, Wheel


def at(w, angle_deg, r):
    a = math.radians(angle_deg)
    return w.cx + math.cos(a) * r, w.cy + math.sin(a) * r


def test_first_sector_is_on_top_and_clockwise():
    w = Wheel(4, 500, 500)
    mid = (RINGS[0][0] + RINGS[0][1]) / 2
    assert w.hit(*at(w, -90, mid)) == 0      # topo
    assert w.hit(*at(w, 0, mid)) == 1        # direita
    assert w.hit(*at(w, 90, mid)) == 2       # baixo
    assert w.hit(*at(w, 180, mid)) == 3      # esquerda


def test_center_cancels_and_far_misses():
    w = Wheel(6, 500, 500)
    assert w.hit(500, 500) is None
    assert w.in_cancel(500 + CANCEL_R - 1, 500)
    assert w.hit(*at(w, 0, w.radius + 200)) is None
    # um pouco além da borda ainda seleciona (tolerância)
    assert w.hit(*at(w, 0, w.radius + 20)) is not None


def test_two_rings():
    w = Wheel(14, 600, 600)
    assert w.radius == RINGS[1][1]
    inner_mid = (RINGS[0][0] + RINGS[0][1]) / 2
    outer_mid = (RINGS[1][0] + RINGS[1][1]) / 2
    assert w.hit(*at(w, -90, inner_mid)) == 0
    assert w.hit(*at(w, -90, outer_mid)) == 10


def test_every_point_maps_to_a_single_sector():
    w = Wheel(9, 400, 400)
    mid = (RINGS[0][0] + RINGS[0][1]) / 2
    seen = {w.hit(*at(w, d, mid)) for d in range(0, 360, 2)}
    assert seen == set(range(9))


def test_clamped_inside_window():
    w = Wheel(8, 5, 5, width=1920, height=1080)
    assert w.cx >= w.radius and w.cy >= w.radius


def test_render_png(tmp_path):
    cairo = pytest.importorskip("cairo")
    pytest.importorskip("gi")
    from mexerica.wheel.render import WheelState, draw
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 520, 520)
    cr = cairo.Context(surf)
    labels = ["JPG", "WEBP", "HEIC", "AVIF", "TIFF", "BMP", "GIF", "ICO",
              "PDF"]
    w = Wheel(len(labels), 260, 260)
    draw(cr, w, WheelState(mode="convert", labels=labels, hover=2,
                           caption="foto.png"))
    out = tmp_path / "roda.png"
    surf.write_to_png(str(out))
    assert out.stat().st_size > 1000
