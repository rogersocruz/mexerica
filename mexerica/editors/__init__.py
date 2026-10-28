"""Janelas abertas pela roda de ferramentas (Shift+Alt).

Todas abrem na hora: a janela aparece primeiro e o que é lento (prévia,
duração, miniaturas, forma de onda) carrega numa thread. A ação primária
fecha a janela e entrega o trabalho ao mesmo runner das rodas (nunca
sobrescreve, notificação de progresso). Visual: theme.py.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..engine.ops import Op
from .addbg import AddBgWindow
from .crop import CropWindow
from .image import ImageEditor, ImageSizeWindow
from .media import TrimWindow, VideoSizeWindow
from .pdf import PdfPagesWindow

log = logging.getLogger("mexerica")

_SINGLE = {"img-edit": ImageEditor, "img-crop": CropWindow,
           "img-addbg": AddBgWindow, "vid-trim": TrimWindow,
           "aud-trim": TrimWindow, "pdf-pages": PdfPagesWindow}
_BATCH = {"img-size": ImageSizeWindow, "vid-size": VideoSizeWindow}


def open_editor(app, op: Op, paths: list[Path]):
    if op.id in _SINGLE:
        win = _SINGLE[op.id](app, op, paths[0])
    elif op.id in _BATCH:
        win = _BATCH[op.id](app, op, paths)
    else:
        log.warning("sem janela para %s", op.id)
        return None
    win.present()
    return win


__all__ = ["open_editor"]
