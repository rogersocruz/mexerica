"""O que muda entre os desktops: GNOME (Linux) e Windows.

A roda, as janelas de edição e o motor são os mesmos. Muda quem percebe o
arraste com Shift, quem põe as janelas da Mexerica acima das outras e
como falar com o sistema (clipboard, gerenciador de arquivos, terminal e
notificações):

  GNOME    a extensão do Shell percebe o arraste e chama o serviço por
           D-Bus (gnome.py)
  Windows  o próprio serviço observa mouse e teclado e cuida das janelas
           pela API Win32 (windows.py, win32.py); a regra de quando abrir
           e fechar a roda é a mesma da extensão (drag.py)

Todo backend tem: start, show_overlay, wheel_center, overlay_dim,
dialog_parent, set_clipboard, reveal, open_uri, open_terminal, notify,
withdraw e status.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

WINDOWS = sys.platform == "win32"


def setup_process() -> None:
    """Ajustes do processo antes do primeiro subprocesso (só no Windows)."""
    if not WINDOWS:
        return
    # No MSYS2, ffmpeg, magick, qpdf... ficam ao lado do python.exe, e é
    # dali que eles carregam as próprias DLLs e delegates (gs, rsvg).
    bindir = str(Path(sys.executable).parent)
    path = os.environ.get("PATH", "")
    if bindir.lower() not in path.lower().split(os.pathsep):
        os.environ["PATH"] = bindir + os.pathsep + path
    _no_console_windows()


def _no_console_windows() -> None:
    """O serviço roda no pythonw.exe, sem console: cada ffmpeg ou magick
    abriria uma janela preta. Todo subprocesso nasce sem janela, a não ser
    que peça outra coisa (o terminal pede CREATE_NEW_CONSOLE)."""
    class Popen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
            super().__init__(*args, **kwargs)
    subprocess.Popen = Popen


def backend(app):
    if WINDOWS:
        from .windows import WindowsDesktop
        return WindowsDesktop(app)
    from .gnome import GnomeDesktop
    return GnomeDesktop(app)
