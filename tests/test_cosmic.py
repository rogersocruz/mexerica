"""Backend experimental do COSMIC: leitura crua de /dev/input (InputState)
e a ligação com a regra de abrir/fechar a roda (CosmicDesktop._poll).

Sem COSMIC nem /dev/input: os eventos são simulados.
"""
import os

import pytest

from mexerica.desktop import evinput as E
from mexerica.desktop import is_cosmic, preload_layer_shell
from mexerica.engine.ops import ACTIONS, CONVERT, TOOLS

LSHIFT, RSHIFT, LALT, LCTRL = 42, 54, 56, 29


def feed(st, *events):
    for ev in events:
        st.feed(*ev)


def press(code):
    return (E.EV_KEY, code, 1)


def release(code):
    return (E.EV_KEY, code, 0)


def move(dx, dy=0):
    return [(E.EV_REL, E.REL_X, dx), (E.EV_REL, E.REL_Y, dy)]


# ------------------------------------------------------------ InputState

def test_click_without_motion_is_not_a_drag():
    st = E.InputState()
    feed(st, press(E.BTN_LEFT), *move(2, 1))
    assert st.button and not st.dragging


def test_drag_after_threshold_and_reset_on_release():
    st = E.InputState()
    feed(st, press(E.BTN_LEFT), *move(8, 0), *move(6, 0))
    assert st.dragging
    feed(st, release(E.BTN_LEFT))
    assert not st.button and not st.dragging
    feed(st, press(E.BTN_LEFT))
    assert not st.dragging, "o movimento conta de novo a cada clique"


def test_motion_without_button_is_ignored():
    st = E.InputState()
    feed(st, *move(500, 500))
    feed(st, press(E.BTN_LEFT))
    assert not st.dragging


def test_touchpad_absolute_events_count_as_motion():
    st = E.InputState()
    feed(st, press(E.BTN_LEFT))
    for _ in range(E.ABS_EVENTS_THRESHOLD):
        st.feed(E.EV_ABS, 0, 100)
    assert st.dragging


def test_modifiers_left_right_and_autorepeat():
    st = E.InputState()
    feed(st, press(LSHIFT), (E.EV_KEY, LSHIFT, 2), press(RSHIFT))
    assert st.modifiers() == (True, False, False)
    feed(st, release(LSHIFT))
    assert st.modifiers()[0], "o Shift direito continua pressionado"
    feed(st, release(RSHIFT), press(LALT), press(LCTRL))
    assert st.modifiers() == (False, True, True)


def test_other_keys_are_not_kept():
    st = E.InputState()
    feed(st, press(30), press(31))          # A, S
    assert st.modifiers() == (False, False, False)
    assert not hasattr(st, "keys")


def test_event_struct_matches_kernel_layout():
    # struct input_event em 64 bits: timeval (16) + type, code (2+2) + value (4)
    if E.EVENT.size != 24:
        pytest.skip("arquitetura de 32 bits")
    raw = E.EVENT.pack(0, 0, E.EV_KEY, E.BTN_LEFT, 1)
    assert E.EVENT.unpack(raw)[2:] == (E.EV_KEY, E.BTN_LEFT, 1)


# ------------------------------------------------------------ detecção

def test_is_cosmic(monkeypatch):
    monkeypatch.delenv("MEXERICA_DESKTOP", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "COSMIC")
    assert is_cosmic()
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "ubuntu:GNOME")
    assert not is_cosmic()
    monkeypatch.setenv("MEXERICA_DESKTOP", "cosmic")
    assert is_cosmic()


def test_preload_is_noop_outside_cosmic(monkeypatch):
    monkeypatch.delenv("MEXERICA_DESKTOP", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    called = []
    monkeypatch.setattr(os, "execve", lambda *a: called.append(a))
    preload_layer_shell([])
    assert not called


def test_preload_reexecs_once_with_ld_preload(monkeypatch):
    from mexerica import desktop as Dk
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "COSMIC")
    monkeypatch.delenv("MEXERICA_DESKTOP", raising=False)
    monkeypatch.delenv("MEXERICA_PRELOADED", raising=False)
    monkeypatch.delenv("LD_PRELOAD", raising=False)
    monkeypatch.setattr(Dk, "layer_shell_library",
                        lambda: "/usr/lib/libgtk4-layer-shell.so.1")
    calls = []
    monkeypatch.setattr(os, "execve", lambda exe, args, env: calls.append(
        (args, env)))
    preload_layer_shell(["--gapplication-service"])
    (args, env), = calls
    assert args[-1] == "--gapplication-service"
    assert env["LD_PRELOAD"].startswith("/usr/lib/libgtk4-layer-shell.so")
    assert env["MEXERICA_PRELOADED"] == "1"
    monkeypatch.setenv("MEXERICA_PRELOADED", "1")
    preload_layer_shell([])
    assert len(calls) == 1, "não entra em laço"


# ------------------------------------------------------------ backend

class FakeReader:
    def __init__(self):
        self.button = self.moved = False
        self.mods = (False, False, False)

    def snapshot(self):
        return self.button, self.button and self.moved, self.mods


class FakeOverlay:
    def __init__(self):
        self.paths = []
        self.wheel = object()
        self.drawn = 0
        self.area = self

    def queue_draw(self):
        self.drawn += 1


class FakeApp:
    def __init__(self):
        self.overlay = FakeOverlay()
        self.calls = []

    def show_wheel(self, mode, paths):
        self.calls.append(("show", mode))

    def hide_wheel(self):
        self.calls.append(("hide",))


@pytest.fixture
def backend(monkeypatch):
    pytest.importorskip("gi")
    from mexerica.desktop import cosmic as C
    clock = [0.0]
    monkeypatch.setattr(C.time, "monotonic", lambda: clock[0] / 1000)
    app = FakeApp()
    b = C.CosmicDesktop(app)
    b.reader = FakeReader()
    return b, app, clock


def step(b, clock, ms):
    clock[0] += ms
    b._poll()


def test_shift_drag_opens_invisible_until_pointer_seen(backend):
    b, app, clock = backend
    r = b.reader
    r.button = True
    step(b, clock, 30)
    r.moved = True
    r.mods = (True, False, False)
    step(b, clock, 30)
    assert app.calls == [("show", CONVERT)]
    assert not b.ready_to_draw(app.overlay)
    assert b.wheel_center(app.overlay, 1920, 1080) is None
    b.pointer_seen(app.overlay, 640.0, 300.0)
    assert b.ready_to_draw(app.overlay)
    assert b.wheel_center(app.overlay, 1920, 1080) == (640.0, 300.0)
    assert app.overlay.wheel is None, "a roda é recalculada no ponto"
    b.pointer_seen(app.overlay, 900.0, 900.0)
    assert b.wheel_center(app.overlay, 1920, 1080) == (640.0, 300.0), \
        "a roda não segue o ponteiro"


def test_mode_switch_keeps_center_and_end_hides(backend):
    b, app, clock = backend
    r = b.reader
    r.button = r.moved = True
    r.mods = (True, False, False)
    step(b, clock, 30)
    b.pointer_seen(app.overlay, 100.0, 100.0)
    r.mods = (True, True, False)
    step(b, clock, 30)
    assert app.calls[-1] == ("show", TOOLS)
    assert b.wheel_center(app.overlay, 1, 1) == (100.0, 100.0)
    r.mods = (True, False, True)
    step(b, clock, 30)
    assert app.calls[-1] == ("show", ACTIONS)
    app.overlay.paths = ["foto.png"]       # o drop trouxe arquivos
    r.button = r.moved = False
    step(b, clock, 30)
    step(b, clock, 500)
    assert app.calls[-1] == ("hide",)
    assert b.wheel_center(app.overlay, 1, 1) is None


def test_shift_text_selection_without_files_gives_up(backend):
    b, app, clock = backend
    r = b.reader
    r.button = r.moved = True
    r.mods = (True, False, False)
    step(b, clock, 30)
    for _ in range(30):                     # ~900 ms sem arquivos
        step(b, clock, 30)
    assert app.calls[-1] == ("hide",)
    assert b._center is None and not b._await_enter


def test_plain_drag_without_shift_does_nothing(backend):
    b, app, clock = backend
    r = b.reader
    r.button = r.moved = True
    for _ in range(10):
        step(b, clock, 30)
    assert app.calls == []
