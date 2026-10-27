"""Detecção do "tipo" de cada arquivo (imagem, vídeo, áudio...).

A detecção é por extensão, com fallback no `mimetypes` da stdlib. É
determinística e rápida (roda enquanto o usuário ainda está arrastando).
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

IMAGE = "image"
VECTOR = "vector"          # SVG: entra como imagem, mas não é alvo de saída comum
VIDEO = "video"
AUDIO = "audio"
PDF = "pdf"
DOC_TEXT = "doc-text"      # docx, odt, rtf, pages...
DOC_SLIDES = "doc-slides"  # pptx, odp, key...
DOC_SHEET = "doc-sheet"    # xlsx, ods, csv...
TEXT = "text"              # txt, md, html
EBOOK = "ebook"            # epub
SUBTITLE = "subtitle"      # srt, vtt, ass
ARCHIVE = "archive"        # zip, tar.*, 7z, rar
FOLDER = "folder"
OTHER = "other"

# Agrupamentos úteis para declarar operações
IMAGES = {IMAGE, VECTOR}
DOCUMENTS = {DOC_TEXT, DOC_SLIDES, DOC_SHEET}
MEDIA = {VIDEO, AUDIO}
FILES = {IMAGE, VECTOR, VIDEO, AUDIO, PDF, DOC_TEXT, DOC_SLIDES, DOC_SHEET,
         TEXT, EBOOK, SUBTITLE, ARCHIVE, OTHER}
ANY = FILES | {FOLDER}

_EXT = {
    IMAGE: "jpg jpeg jpe jfif png webp heic heif avif tif tiff bmp gif ico jxl",
    VECTOR: "svg svgz",
    VIDEO: "mp4 m4v mov mkv webm avi wmv flv 3gp mpg mpeg ts mts m2ts ogv",
    AUDIO: "mp3 m4a aac wav flac ogg oga opus aif aiff wma alac amr",
    PDF: "pdf",
    DOC_TEXT: "doc docx odt rtf pages wpd",
    DOC_SLIDES: "ppt pptx odp key",
    DOC_SHEET: "xls xlsx ods csv numbers",
    TEXT: "txt md markdown html htm",
    EBOOK: "epub",
    SUBTITLE: "srt vtt ass ssa",
    ARCHIVE: "zip tar gz tgz bz2 tbz2 xz txz zst 7z rar",
}
EXT_TO_KIND = {e: k for k, exts in _EXT.items() for e in exts.split()}

# Extensões compostas que precisam ser vistas inteiras (arquivo.tar.gz)
_COMPOUND = (".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst")


def full_ext(path: Path) -> str:
    """Extensão em minúsculas, sem ponto, respeitando .tar.gz e afins."""
    name = path.name.lower()
    for comp in _COMPOUND:
        if name.endswith(comp):
            return comp[1:]
    return path.suffix.lower().lstrip(".")


def stem(path: Path) -> str:
    """Nome sem extensão (tira .tar.gz inteiro)."""
    ext = full_ext(path)
    if ext and path.name.lower().endswith("." + ext):
        return path.name[: -(len(ext) + 1)]
    return path.stem


def kind_of(path: Path) -> str:
    path = Path(path)
    if path.is_dir():
        return FOLDER
    ext = full_ext(path)
    if ext.startswith("tar."):
        return ARCHIVE
    if ext in EXT_TO_KIND:
        return EXT_TO_KIND[ext]
    mime, _ = mimetypes.guess_type(path.name)
    if mime:
        top = mime.split("/")[0]
        if top == "image":
            return IMAGE
        if top == "video":
            return VIDEO
        if top == "audio":
            return AUDIO
        if top == "text":
            return TEXT
    return OTHER
