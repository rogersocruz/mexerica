"""Descoberta dos programas externos (ffmpeg, ImageMagick, qpdf...).

Tudo é opcional: uma operação só aparece na roda se os programas que ela
usa estiverem instalados. Os resultados ficam em cache durante a vida do
processo (o helper roda como serviço, então a sondagem acontece uma vez).
"""
from __future__ import annotations

import functools
import shutil
import subprocess


@functools.lru_cache(maxsize=None)
def which(name: str) -> str | None:
    return shutil.which(name)


def has(*names: str) -> bool:
    return all(resolve(n) is not None for n in names)


@functools.lru_cache(maxsize=None)
def resolve(name: str) -> list[str] | None:
    """Comando base (argv) para um nome lógico, ou None se indisponível.

    Nomes lógicos cobrem diferenças entre distros/versões:
      magick   -> `magick` (ImageMagick 7, Arch) ou `convert` (IM 6)
      montage  -> `magick montage` ou `montage`
      soffice  -> `soffice` ou `libreoffice`
    """
    if name == "magick":
        if which("magick"):
            return ["magick"]
        if which("convert"):
            return ["convert"]
        return None
    if name == "montage":
        if which("magick"):
            return ["magick", "montage"]
        if which("montage"):
            return ["montage"]
        return None
    if name == "soffice":
        for cand in ("soffice", "libreoffice"):
            if which(cand):
                return [which(cand)]
        return None
    path = which(name)
    return [path] if path else None


def cmd(name: str) -> list[str]:
    base = resolve(name)
    if base is None:
        raise FileNotFoundError(f"programa não encontrado: {name}")
    return list(base)


@functools.lru_cache(maxsize=None)
def magick_writable() -> frozenset[str]:
    """Formatos que o ImageMagick instalado consegue ESCREVER (ex.: HEIC
    depende do libheif, AVIF/JXL de delegates próprios)."""
    base = resolve("magick")
    if base is None:
        return frozenset()
    args = base + ["-list", "format"]
    try:
        out = subprocess.run(args, capture_output=True, text=True,
                             timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    fmts = set()
    for line in out.splitlines():
        parts = line.split()
        # Linha típica: "   HEIC* HEIC      rw+   High Efficiency ..."
        if len(parts) >= 3 and len(parts[2]) >= 2 and parts[2][1] == "w":
            fmts.add(parts[0].rstrip("*").lower())
    return frozenset(fmts)


@functools.lru_cache(maxsize=None)
def ffmpeg_encoders() -> frozenset[str]:
    if not which("ffmpeg"):
        return frozenset()
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
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
