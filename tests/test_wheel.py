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


@pytest.mark.parametrize("mode,files", [
    ("convert", ["foto.png"]), ("tools", ["foto.png"]),
    ("actions", ["foto.png"]), ("tools", ["clip.mp4", "b.mp4"]),
])
def test_render_each_wheel(tmp_path, mode, files):
    """Cada roda (com hover, ícones e dois anéis) desenha sem erro."""
    cairo = pytest.importorskip("cairo")
    from pathlib import Path
    from mexerica import theme as TH
    from mexerica.engine import options_for
    from mexerica.wheel.render import WheelState, draw
    ops = options_for([Path(f) for f in files], mode)
    if mode == "convert":
        ops = ops + ops[:4]          # força o 2º anel
    W = 640
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, W)
    cr = cairo.Context(surf)
    w = Wheel(len(ops), W / 2, W / 2, W, W)
    st = WheelState(mode=mode, labels=[TH.wheel_label(o) for o in ops],
                    icons=[TH.wheel_icon(o) for o in ops], caption="1.1 MB",
                    hover=0, hover_t={0: 1.0})
    draw(cr, w, st)
    out = tmp_path / f"{mode}.png"
    surf.write_to_png(str(out))
    assert out.stat().st_size > 5000
    if mode != "convert":
        assert all(i for i in st.icons), "ferramentas e ações têm ícone"


def test_backdrop_blur_smooths_and_scales():
    import cairo
    from mexerica.wheel import backdrop as B
    assert B.levels_for(0) == 0 and B.levels_for(4) == 2
    assert B.levels_for(18) == 4 and B.levels_for(40) == 5
    w, h = 320, 200
    src = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    cr = cairo.Context(src)
    for y in range(0, h, 8):                       # xadrez preto e branco
        for x in range(0, w, 8):
            v = float((x // 8 + y // 8) % 2)
            cr.set_source_rgb(v, v, v)
            cr.rectangle(x, y, 8, 8)
            cr.fill()
    assert B.blur(src, 0) is src                   # desligado: igual
    small = B.blur(src, 18)
    assert small.get_width() < w and small.get_height() < h
    out = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    B.paint_backdrop(cairo.Context(out), small, w, h)
    out.flush()
    data, stride = out.get_data(), out.get_stride()
    greens = [data[y * stride + x * 4 + 1]
              for y in range(20, h - 20, 7) for x in range(20, w - 20, 7)]
    # o xadrez vira quase cinza uniforme
    assert max(greens) - min(greens) < 60
    assert 90 < sum(greens) / len(greens) < 165


def test_live_drag_order():
    """Organizador de páginas: o bloco arrastado abre espaço ao vivo e não
    fica pulando quando o ponteiro cai sobre ele mesmo."""
    pytest = __import__("pytest")
    pdf = pytest.importorskip("mexerica.editors.pdf")
    a, b, c, d, e = "abcde"
    items = [a, b, c, d, e]
    assert pdf.live_order(items, [b], d) == [a, c, d, b, e]   # para frente
    assert pdf.live_order(items, [d], a) == [d, a, b, c, e]   # para trás
    assert pdf.live_order(items, [b], b) == items             # sobre si
    # bloco não contíguo vira um bloco só, na ordem da grade
    assert pdf.live_order(items, [e, b], c) == [a, c, b, e, d]
    # estável: depois de mover, o alvo do lado oposto não desfaz a troca
    moved = pdf.live_order(items, [b], c)
    assert moved == [a, c, b, d, e]
    assert pdf.live_order(moved, [b], b) == moved
