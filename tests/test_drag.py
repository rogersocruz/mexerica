"""Regra de abrir/fechar a roda durante um arraste (backend do Windows).

Os mesmos casos que tests/extension_logic.test.mjs cobre na extensão do
GNOME: Shift abre, Alt/Ctrl trocam a roda, soltar o Shift por pouco tempo
não fecha, o fim do arraste fecha com atraso e arraste sem arquivos
desiste.
"""
from mexerica.desktop import drag as D
from mexerica.engine.ops import ACTIONS, CONVERT, TOOLS

P = (500, 400)


def run(steps):
    """steps: (ms, arrastando, modo, ponteiro) -> ações não vazias."""
    w = D.DragWatch()
    out = []
    for now, dragging, mode, *pt in steps:
        act = w.step(dragging, mode, pt[0] if pt else P, now)
        if act:
            out.append((now, act))
    return w, out


def test_mode_for():
    assert D.mode_for(False, True, True) is None
    assert D.mode_for(True, False, False) == CONVERT
    assert D.mode_for(True, True, False) == TOOLS
    assert D.mode_for(True, False, True) == ACTIONS
    assert D.mode_for(True, True, True) == TOOLS      # Alt ganha, como no GNOME


def test_shift_opens_at_the_anchor_and_switches_modes():
    _, acts = run([
        (0, True, None),
        (30, True, CONVERT, (100, 100)),
        (60, True, CONVERT, (300, 300)),
        (90, True, TOOLS, (320, 320)),
    ])
    assert acts == [(30, (D.SHOW, CONVERT, (100, 100))),
                    (90, (D.SHOW, TOOLS, (100, 100)))]   # a roda não anda


def test_short_release_keeps_the_wheel():
    _, acts = run([
        (0, True, CONVERT), (30, True, None), (120, True, None),
        (150, True, CONVERT), (180, True, None),
        (200, True, None), (360, True, None),
    ])
    assert acts == [(0, (D.SHOW, CONVERT, P)), (360, (D.HIDE,))]


def test_drag_end_hides_after_the_drop_delay():
    _, acts = run([
        (0, True, CONVERT), (30, False, None), (300, False, None),
        (430, False, None), (460, False, None),
    ])
    assert acts == [(0, (D.SHOW, CONVERT, P)), (430, (D.HIDE,))]


def test_no_shift_no_wheel():
    _, acts = run([(t, True, None) for t in range(0, 600, 30)]
                  + [(600, False, None), (1200, False, None)])
    assert acts == []


def test_drag_without_files_gives_up_until_the_next_drag():
    w, acts = run([(0, True, CONVERT)])
    assert w.probe(False, 100) is None                 # ainda esperando
    assert w.probe(True, D.PROBE_MS + 1) is None       # com arquivos fica
    assert w.probe(False, D.PROBE_MS) == (D.HIDE,)
    assert w.step(True, CONVERT, P, 900) is None       # desistiu deste
    assert w.step(False, None, P, 930) is None
    assert w.step(True, CONVERT, P, 2000) == (D.SHOW, CONVERT, P)
