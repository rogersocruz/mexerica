"""O que muda entre os desktops: GNOME (Linux) e Windows.

A roda, as janelas de edição e o motor são os mesmos. Muda quem percebe o
arraste com Shift, quem põe as janelas da Mexerica acima das outras e
como falar com o sistema (clipboard, gerenciador de arquivos, terminal e
notificações):

  GNOME    a extensão do Shell percebe o arraste e chama o serviço por
           D-Bus (gnome.py)
  COSMIC   EXPERIMENTAL: o serviço lê mouse e teclado do kernel
           (/dev/input) e a roda é uma superfície do wlr-layer-shell
           (cosmic.py, evinput.py); mesma regra do drag.py
  Windows  o próprio serviço observa mouse e teclado e cuida das janelas
           pela API Win32 (windows.py, win32.py); a regra de quando abrir
           e fechar a roda é a mesma da extensão (drag.py)

Todo backend tem: start, stop, show_overlay, wheel_center, overlay_dim,
dialog_parent, drag_source, file_icon, display_name, autostart,
set_autostart, set_clipboard, reveal, open_uri, open_terminal, notify,
withdraw e status.
"""
from __future__ import annotations

import glob
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
    _subprocess_defaults()


def _subprocess_defaults() -> None:
    """Dois padrões para todo subprocesso no Windows:
    - sem janela: o serviço roda no pythonw.exe, sem console, e cada ffmpeg
      ou magick abriria uma janela preta (o terminal pede
      CREATE_NEW_CONSOLE);
    - saída de texto que não é UTF-8 (programa que escreve em ANSI) vira "?"
      em vez de sumir: a thread que lê a saída morre calada e o stdout
      chegaria None."""
    class Popen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
            if kwargs.get("text") or kwargs.get("universal_newlines") \
                    or kwargs.get("encoding"):
                kwargs.setdefault("errors", "replace")
            super().__init__(*args, **kwargs)
    subprocess.Popen = Popen


def is_cosmic() -> bool:
    """Sessão do COSMIC (ou MEXERICA_DESKTOP=cosmic, para testar o backend
    em outro compositor com wlr-layer-shell)."""
    forced = os.environ.get("MEXERICA_DESKTOP", "").lower()
    if forced:
        return forced == "cosmic"
    return "cosmic" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower()


def layer_shell_library() -> str | None:
    """Caminho do libgtk4-layer-shell.so (Arch, Debian/Ubuntu/Pop, Fedora)."""
    for pattern in ("/usr/lib/libgtk4-layer-shell.so*",
                    "/usr/lib64/libgtk4-layer-shell.so*",
                    "/usr/lib/*-linux-gnu/libgtk4-layer-shell.so*",
                    "/usr/local/lib/libgtk4-layer-shell.so*",
                    "/usr/local/lib/*-linux-gnu/libgtk4-layer-shell.so*"):
        found = sorted(glob.glob(pattern), key=len)
        if found:
            return found[0]
    return None


def preload_layer_shell(argv: list[str]) -> None:
    """O gtk4-layer-shell precisa ser carregado antes do libwayland-client,
    o que um programa Python só consegue com LD_PRELOAD. No COSMIC, o
    processo do serviço se reinicia uma vez com a biblioteca pré-carregada.
    Não mexe em nada nos outros desktops."""
    if WINDOWS or not is_cosmic() or os.environ.get("MEXERICA_PRELOADED"):
        return
    lib = layer_shell_library()
    if not lib:
        return
    env = dict(os.environ, MEXERICA_PRELOADED="1")
    pre = env.get("LD_PRELOAD", "")
    if lib not in pre.split(":"):
        env["LD_PRELOAD"] = f"{lib}:{pre}" if pre else lib
    os.execve(sys.executable, [sys.executable, "-m", "mexerica", *argv], env)


def backend(app):
    if WINDOWS:
        from .windows import WindowsDesktop
        return WindowsDesktop(app)
    if is_cosmic():
        from .cosmic import CosmicDesktop
        return CosmicDesktop(app)
    from .gnome import GnomeDesktop
    return GnomeDesktop(app)
