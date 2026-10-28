"""Quando mostrar e esconder a roda durante um arraste.

É a regra da extensão do GNOME Shell (`_tick`), separada da leitura do
sistema para dar para testar: a cada passo o backend informa o botão do
mouse, se a imagem de arraste do shell está visível, a roda pedida pelos
modificadores, o ponteiro e o relógio, e recebe o que fazer. Puro Python.

A imagem de arraste só marca o começo: quem a mostra é o alvo do drop, e
sobre a própria roda (GTK) ela some. Daí em diante o arraste dura enquanto
o botão estiver pressionado; senão a roda fecharia ao abrir e reabriria
ao fechar, piscando.
"""
from __future__ import annotations

from ..engine.ops import ACTIONS, CONVERT, TOOLS

POLL_MS = 30               # leitura dos modificadores durante o arraste
IDLE_POLL_MS = 80          # sem botão pressionado
RELEASE_GRACE_MS = 150     # soltar Shift por menos que isso não fecha
END_HIDE_DELAY_MS = 400    # dá tempo do serviço processar o drop
PROBE_MS = 800             # sem arquivos no arraste até aqui: desiste

SHOW, HIDE = "show", "hide"


def mode_for(shift: bool, alt: bool, ctrl: bool) -> str | None:
    if not shift:
        return None
    if alt:
        return TOOLS
    if ctrl:
        return ACTIONS
    return CONVERT


class DragWatch:
    def __init__(self) -> None:
        self.dragging = False
        self.shown: str | None = None
        self.anchor: tuple[int, int] | None = None
        self.shown_at = 0.0
        self.released_at = 0.0
        self.ended_at = 0.0
        self.given_up = False

    def step(self, button: bool, image: bool, mode: str | None,
             pointer: tuple[int, int], now: float):
        """Um passo do laço (`now` em ms). Devolve (SHOW, modo, âncora),
        (HIDE,) ou None."""
        dragging = button and (self.dragging or image)
        if not dragging:
            if self.dragging:                     # o arraste terminou
                self.dragging = False
                self.ended_at = now
            if self.shown and now - self.ended_at >= END_HIDE_DELAY_MS:
                return self._hide()
            return None
        if not self.dragging:                     # começou um arraste
            self.dragging = True
            self.given_up = False
            self.released_at = 0.0
        if self.given_up:
            return None
        if mode:
            self.released_at = 0.0
            if self.anchor is None:
                self.anchor = pointer             # a roda não segue o ponteiro
            if mode != self.shown:
                if not self.shown:
                    self.shown_at = now
                self.shown = mode
                return SHOW, mode, self.anchor
        elif self.shown:
            if not self.released_at:
                self.released_at = now
            elif now - self.released_at > RELEASE_GRACE_MS:
                return self._hide()
        return None

    def probe(self, has_files: bool, now: float):
        """A roda está aberta e o arraste não trouxe arquivos (texto, link):
        esconde e ignora o resto deste arraste."""
        if self.shown and not has_files and now - self.shown_at >= PROBE_MS:
            self.given_up = True
            return self._hide()
        return None

    def _hide(self):
        self.shown = None
        self.anchor = None
        self.released_at = 0.0
        return (HIDE,)
