"""Descoberta dos programas externos (ffmpeg, ImageMagick, qpdf...).

Tudo é opcional: uma operação só aparece na roda se os programas que ela
usa estiverem instalados. Os resultados ficam em cache durante a vida do
processo (o helper roda como serviço, então a sondagem acontece uma vez).
"""
from __future__ import annotations

import functools
import glob
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .. import cache_dir

WINDOWS = sys.platform == "win32"


# Programas que a Mexerica usa e para quê (doctor e Configurações > Sobre)
PROGRAMS: list[tuple[str, str]] = [
    ("ffmpeg", "vídeo e áudio"), ("ffprobe", "duração/tamanho alvo"),
    ("magick", "imagens (ImageMagick)"), ("montage", "colagem"),
    ("soffice", "documentos (LibreOffice, opcional)"),
    ("pandoc", "Markdown/EPUB e documentos sem Office"),
    ("typst", "PDF pelo pandoc, sem Office"),
    ("pdftoppm", "PDF → imagens (poppler)"), ("pdftotext", "PDF → texto"),
    ("pdfimages", "extrair imagens de PDF"), ("qpdf", "juntar/dividir PDF"),
    ("gs", "comprimir PDF (Ghostscript)"),
    ("exiftool", "metadados"), ("zbarimg", "ler QR code (zbar)"),
    ("bsdtar", "ZIP/7Z/TAR/RAR (libarchive)"),
    ("ffplay", "ouvir o trecho no Cortar…"),
    ("rembg", "remover fundo de fotos com IA (opcional)"),
    ("ebook-convert", "e-books MOBI, AZW3 e FB2 (calibre, opcional)"),
]
if not WINDOWS:
    PROGRAMS.append(("wl-copy", "clipboard sem a extensão (wl-clipboard)"))

# Módulos Python opcionais (dados e fontes): pacotes do MSYS2 ou da distro
MODULES: list[tuple[str, str]] = [
    ("yaml", "YAML (PyYAML)"), ("fontTools", "fontes TTF, OTF e WOFF"),
    ("brotli", "fontes WOFF2"),
]


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


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
            "Xournal++\\bin", "Calibre2")]
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


def magick_writable() -> frozenset[str]:
    """Formatos que o ImageMagick instalado consegue ESCREVER (ex.: HEIC
    depende do libheif, AVIF/JXL de delegates próprios)."""
    return _magick_formats()[1]


def magick_readable() -> frozenset[str]:
    """Formatos que ele consegue LER (RAW de câmera, JPEG 2000, EXR...)."""
    return _magick_formats()[0]


@functools.lru_cache(maxsize=None)
def _magick_formats() -> tuple[frozenset[str], frozenset[str]]:
    """(lê, escreve), pelo `-list format`. Ele carrega todos os módulos do
    ImageMagick: no Windows leva uns 10 s. O resultado fica em disco e só é
    refeito quando o magick ou a pasta dele mudam (instalar o libheif, por
    exemplo)."""
    base = resolve("magick")
    if base is None:
        return frozenset(), frozenset()
    try:
        exe = Path(base[0])
        sig = f"{exe}|{exe.stat().st_mtime_ns}|{exe.parent.stat().st_mtime_ns}"
    except OSError:
        sig = None
    cache = cache_dir() / "magick-formats-v2.txt"
    try:
        lines = cache.read_text(encoding="utf-8").splitlines()
        if sig and lines and lines[0] == sig:
            return _split_modes(line.split(" ", 1) for line in lines[1:])
    except OSError:
        pass
    try:
        out = subprocess.run(base + ["-list", "format"], capture_output=True,
                             text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return MAGICK_BASIC, MAGICK_BASIC
    found = []
    for line in out.splitlines():
        parts = line.split()
        # Linha típica: "   HEIC* HEIC      rw+   High Efficiency ..."
        if len(parts) >= 3 and len(parts[2]) == 3 and parts[2][0] in "r-" \
                and parts[2][1] in "w-":
            found.append((parts[2][:2], parts[0].rstrip("*").lower()))
    if not found:
        return MAGICK_BASIC, MAGICK_BASIC
    if sig:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text("\n".join([sig] + [f"{m} {n}" for m, n in found]),
                             encoding="utf-8")
        except OSError:
            pass
    return _split_modes(found)


def _split_modes(pairs) -> tuple[frozenset[str], frozenset[str]]:
    reads, writes = set(), set()
    for mode, name in pairs:
        if mode[0] == "r":
            reads.add(name)
        if mode[1] == "w":
            writes.add(name)
    return frozenset(reads), frozenset(writes)


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
    _magick_formats()
    ffmpeg_encoders()
