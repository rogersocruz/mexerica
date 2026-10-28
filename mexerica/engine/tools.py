"""Descoberta dos programas externos (ffmpeg, ImageMagick, qpdf...).

Tudo é opcional: uma operação só aparece na roda se os programas que ela
usa estiverem instalados. Os resultados ficam em cache durante a vida do
processo (o helper roda como serviço, então a sondagem acontece uma vez).
"""
from __future__ import annotations

import functools
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .. import cache_dir

WINDOWS = sys.platform == "win32"


@functools.lru_cache(maxsize=None)
def _search_path() -> str | None:
    """No Windows, além do PATH: a pasta do python.exe (no MSYS2 é onde
    ficam ffmpeg, magick, qpdf...) e onde os instaladores costumam pôr o
    que não entra no PATH (LibreOffice, Ghostscript, Xournal++...)."""
    if not WINDOWS:
        return None
    dirs = [os.environ.get("PATH", ""), str(Path(sys.executable).parent)]
    for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if not base:
            continue
        # (o winget instala alguns por usuário, em LOCALAPPDATA\Programs)
        dirs += [os.path.join(base, sub) for sub in (
            "LibreOffice\\program", "Pandoc", "ExifTool", "Programs\\ExifTool",
            "Xournal++\\bin")]
        dirs += sorted(glob.glob(os.path.join(base, "gs", "gs*", "bin")),
                       reverse=True)
        dirs += sorted(glob.glob(os.path.join(base, "ImageMagick*")),
                       reverse=True)
        dirs += glob.glob(os.path.join(base, "qpdf*", "bin"))
    return os.pathsep.join(dirs)


@functools.lru_cache(maxsize=None)
def which(name: str) -> str | None:
    return shutil.which(name, path=_search_path())


def has(*names: str) -> bool:
    return all(resolve(n) is not None for n in names)


@functools.lru_cache(maxsize=None)
def resolve(name: str) -> list[str] | None:
    """Comando base (argv) para um nome lógico, ou None se indisponível.

    Nomes lógicos cobrem diferenças entre distros/versões/sistemas:
      magick   -> `magick` (ImageMagick 7, Arch) ou `convert` (IM 6)
      montage  -> `magick montage` ou `montage`
      soffice  -> `soffice` ou `libreoffice`
      gs       -> `gs` ou `gswin64c` (Ghostscript no Windows)
      bsdtar   -> `bsdtar` ou o `tar.exe` do Windows, que é o mesmo bsdtar
    No Windows, `convert` é o conversor de disco FAT -> NTFS do sistema,
    então ele nunca vale como ImageMagick.
    """
    if name == "magick":
        if which("magick"):
            return [which("magick")]
        if not WINDOWS and which("convert"):
            return [which("convert")]
        return None
    if name == "montage":
        if which("magick"):
            return [which("magick"), "montage"]
        if not WINDOWS and which("montage"):
            return [which("montage")]
        return None
    if name == "soffice":
        for cand in ("soffice", "libreoffice"):
            if which(cand):
                return [which(cand)]
        return None
    if name == "gs":
        for cand in ("gs", "gswin64c", "gswin32c"):
            if which(cand):
                return [which(cand)]
        return None
    if name == "bsdtar":
        if which("bsdtar"):
            return [which("bsdtar")]
        if WINDOWS:     # o Git for Windows põe um GNU tar antes no PATH
            system = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                  "System32", "tar.exe")
            for tar in (which("tar"), system):
                if tar and _is_bsdtar(tar):
                    return [tar]
        return None
    path = which(name)
    return [path] if path else None


def _is_bsdtar(path: str) -> bool:
    try:
        out = subprocess.run([path, "--version"], capture_output=True,
                             text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return "bsdtar" in out


def cmd(name: str) -> list[str]:
    base = resolve(name)
    if base is None:
        raise FileNotFoundError(f"programa não encontrado: {name}")
    return list(base)


# Se a listagem falhar, a roda ainda oferece o que todo ImageMagick escreve.
MAGICK_BASIC = frozenset({"jpeg", "png", "gif", "bmp", "tiff", "ico"})


@functools.lru_cache(maxsize=None)
def magick_writable() -> frozenset[str]:
    """Formatos que o ImageMagick instalado consegue ESCREVER (ex.: HEIC
    depende do libheif, AVIF/JXL de delegates próprios).

    `-list format` carrega todos os módulos do ImageMagick: no Windows leva
    uns 10 s. O resultado fica em disco e só é refeito quando o magick ou a
    pasta dele mudam (instalar o libheif, por exemplo)."""
    base = resolve("magick")
    if base is None:
        return frozenset()
    try:
        exe = Path(base[0])
        sig = f"{exe}|{exe.stat().st_mtime_ns}|{exe.parent.stat().st_mtime_ns}"
    except OSError:
        sig = None
    cache = cache_dir() / "magick-formats.txt"
    try:
        lines = cache.read_text(encoding="utf-8").splitlines()
        if sig and lines and lines[0] == sig:
            return frozenset(lines[1:])
    except OSError:
        pass
    try:
        out = subprocess.run(base + ["-list", "format"], capture_output=True,
                             text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return MAGICK_BASIC
    fmts = set()
    for line in out.splitlines():
        parts = line.split()
        # Linha típica: "   HEIC* HEIC      rw+   High Efficiency ..."
        if len(parts) >= 3 and len(parts[2]) >= 2 and parts[2][1] == "w":
            fmts.add(parts[0].rstrip("*").lower())
    if not fmts:
        return MAGICK_BASIC
    if sig:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text("\n".join([sig, *sorted(fmts)]),
                             encoding="utf-8")
        except OSError:
            pass
    return frozenset(fmts)


@functools.lru_cache(maxsize=None)
def ffmpeg_encoders() -> frozenset[str]:
    if not which("ffmpeg"):
        return frozenset()
    try:
        out = subprocess.run(cmd("ffmpeg") + ["-hide_banner", "-encoders"],
                             capture_output=True, text=True,
                             timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 6 and parts[0][0] in "VAS":
            names.add(parts[1])
    return frozenset(names)


def has_encoder(name: str) -> bool:
    return name in ffmpeg_encoders()


def warm_up() -> None:
    """Faz as sondagens lentas antes da primeira roda (o serviço chama numa
    thread ao iniciar)."""
    magick_writable()
    ffmpeg_encoders()
