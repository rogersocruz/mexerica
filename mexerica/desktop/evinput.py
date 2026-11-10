"""Mouse e teclado direto do kernel (/dev/input), sem depender do compositor.

No COSMIC (e em outros compositores Wayland sem extensões) nenhum
aplicativo sabe que um arraste começou nem quais teclas estão pressionadas
durante ele. O kernel sabe: cada teclado e mouse é um /dev/input/eventN que
entrega eventos crus (struct input_event). Daqui só sai o que a roda
precisa: o botão esquerdo, se o ponteiro andou com ele pressionado e o
estado de Shift, Alt e Ctrl. Nenhuma outra tecla é guardada nem registrada.

Ler /dev/input exige estar no grupo `input` (o mesmo acesso de um
keylogger, por isso o README avisa). Sem permissão, o backend segue sem o
gesto e a roda abre pelo "Abrir com" (mexerica wheel).

InputState é puro e testado (tests/test_evinput.py); InputReader é a
thread que lê os dispositivos e alimenta o InputState.
"""
from __future__ import annotations

import glob
import logging
import os
import select
import struct
import threading
import time

log = logging.getLogger("mexerica")

# linux/input-event-codes.h
EV_KEY, EV_REL, EV_ABS = 1, 2, 3
REL_X, REL_Y = 0, 1
BTN_LEFT = 0x110
SHIFT_KEYS = {42, 54}       # KEY_LEFTSHIFT, KEY_RIGHTSHIFT
ALT_KEYS = {56, 100}        # KEY_LEFTALT, KEY_RIGHTALT
CTRL_KEYS = {29, 97}        # KEY_LEFTCTRL, KEY_RIGHTCTRL

# struct input_event: timeval (2 longs), type, code, value
EVENT = struct.Struct("llHHi")

MOVE_THRESHOLD = 12         # unidades relativas até o clique virar arraste
ABS_EVENTS_THRESHOLD = 4    # touchpad/mesa: eventos de posição com o botão


class InputState:
    """Estado do que importa para a roda, alimentado evento a evento."""

    def __init__(self) -> None:
        self.button = False
        self.moved = False
        self._dx = 0
        self._dy = 0
        self._abs = 0
        self._shift: set[int] = set()
        self._alt: set[int] = set()
        self._ctrl: set[int] = set()

    def feed(self, etype: int, code: int, value: int) -> None:
        if etype == EV_KEY:
            down = value != 0           # 1 = pressionou, 2 = repetição
            if code == BTN_LEFT:
                self.button = down
                self._dx = self._dy = self._abs = 0
                self.moved = False
            for keys, held in ((SHIFT_KEYS, self._shift),
                               (ALT_KEYS, self._alt),
                               (CTRL_KEYS, self._ctrl)):
                if code in keys:
                    (held.add if down else held.discard)(code)
        elif not self.button:
            return
        elif etype == EV_REL and code in (REL_X, REL_Y):
            if code == REL_X:
                self._dx += value
            else:
                self._dy += value
            if abs(self._dx) + abs(self._dy) >= MOVE_THRESHOLD:
                self.moved = True
        elif etype == EV_ABS:
            self._abs += 1
            if self._abs >= ABS_EVENTS_THRESHOLD:
                self.moved = True

    @property
    def dragging(self) -> bool:
        """Botão pressionado e o ponteiro andou: pode ser um arraste."""
        return self.button and self.moved

    def modifiers(self) -> tuple[bool, bool, bool]:
        return bool(self._shift), bool(self._alt), bool(self._ctrl)


def readable_devices() -> list[str]:
    return sorted(p for p in glob.glob("/dev/input/event*")
                  if os.access(p, os.R_OK))


class InputReader:
    """Thread que lê todos os /dev/input/event* legíveis. Dispositivos que
    aparecem depois (mouse USB, Bluetooth) entram na próxima varredura."""

    RESCAN_S = 5.0

    def __init__(self) -> None:
        self.state = InputState()
        self._lock = threading.Lock()
        self._fds: dict[int, str] = {}
        self._stop = False
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        return bool(readable_devices())

    def start(self) -> bool:
        if not self._scan():
            return False
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="mexerica-input")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop = True

    def snapshot(self) -> tuple[bool, bool, tuple[bool, bool, bool]]:
        """(botão, arrastando, (shift, alt, ctrl)) para o laço do GTK."""
        with self._lock:
            st = self.state
            return st.button, st.dragging, st.modifiers()

    def _scan(self) -> bool:
        known = set(self._fds.values())
        for path in readable_devices():
            if path in known:
                continue
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            except OSError:
                continue
            self._fds[fd] = path
        return bool(self._fds)

    def _drop(self, fd: int) -> None:
        self._fds.pop(fd, None)
        try:
            os.close(fd)
        except OSError:
            pass

    def _run(self) -> None:
        last_scan = time.monotonic()
        while not self._stop:
            if time.monotonic() - last_scan > self.RESCAN_S:
                self._scan()
                last_scan = time.monotonic()
            if not self._fds:
                time.sleep(1)
                continue
            try:
                ready, _, _ = select.select(list(self._fds), [], [], 1.0)
            except (OSError, ValueError):
                for fd in list(self._fds):
                    self._drop(fd)
                continue
            for fd in ready:
                try:
                    data = os.read(fd, EVENT.size * 64)
                except BlockingIOError:
                    continue
                except OSError:                 # dispositivo desconectado
                    self._drop(fd)
                    continue
                usable = len(data) - len(data) % EVENT.size
                with self._lock:
                    for off in range(0, usable, EVENT.size):
                        _s, _us, etype, code, value = EVENT.unpack_from(
                            data, off)
                        self.state.feed(etype, code, value)
        for fd in list(self._fds):
            self._drop(fd)
