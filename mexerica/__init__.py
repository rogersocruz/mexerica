"""Mexerica — conversor de arquivos por Shift + arrastar (GNOME e Windows)."""
import os
import sys
from pathlib import Path

__version__ = "0.1.0"
APP_ID = "io.github.rogersocruz.Mexerica"


def cache_dir() -> Path:
    """Log, perfil do LibreOffice e outros descartáveis."""
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        return base / "Mexerica" / "cache"
    return Path.home() / ".cache" / "mexerica"
