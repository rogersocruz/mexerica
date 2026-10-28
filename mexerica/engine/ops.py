"""Registro de operações que aparecem nas rodas.

Três grupos, um por roda:
  convert  (Shift)          -> mudar o formato
  tools    (Shift + Alt)    -> processar mantendo o tipo (comprimir, girar...)
  actions  (Shift + Ctrl)   -> ações de arquivo (copiar caminho, terminal...)

Cada operação declara os tipos de entrada que aceita, os programas de que
precisa e um `build(ctx)` que devolve a lista de passos. Um passo é um
argv (list[str]) executado com subprocess, ou um callable Python.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .. import cache_dir
from . import formats as F
from . import tools as T

CONVERT, TOOLS, ACTIONS = "convert", "tools", "actions"

# Como o resultado é produzido
EACH = "each"      # um resultado por arquivo de entrada
ALL = "all"        # todos os arquivos viram um resultado (juntar PDFs...)
ACTION = "action"  # tratada pelo app (precisa de GUI/clipboard)
EDITOR = "editor"  # abre uma janela que coleta parâmetros (engine/edits.py)

# Tipo do resultado
FILE, DIR, TEXT = "file", "dir", "text"


@dataclass
class Ctx:
    """Contexto de execução de um passo."""
    src: Path                 # arquivo de entrada (em ALL, o primeiro)
    srcs: list[Path]          # todos os arquivos de entrada
    work: Path                # diretório temporário (no mesmo disco do destino)
    out: Path                 # caminho temporário de saída (arquivo ou pasta)
    text: list[str] = field(default_factory=list)  # saída textual (QR, metadados)


Step = list[str] | Callable[[Ctx], None]


@dataclass(frozen=True)
class Op:
    id: str
    label: str
    group: str
    kinds: frozenset[str]
    build: Callable[[Ctx], list[Step]] | None = None
    ext: str | None = None            # extensão da saída; None = mesma da entrada
    suffix: str = ""                  # sufixo no nome ("-comprimido")
    mode: str = EACH
    result: str = FILE
    needs: tuple[str, ...] = ()
    min_files: int = 1
    skip_exts: frozenset[str] = frozenset()   # não oferecer se a entrada já é isso
    available: Callable[[], bool] | None = None
    hint: str = ""                    # descrição curta (tooltip/CLI)
    max_files: int = 0                # 0 = sem limite
    in_wheel: bool = True             # False: só pela CLI (preset antigo)

    def is_available(self) -> bool:
        if not T.has(*self.needs):
            return False
        return self.available() if self.available else True

    def output_name(self, src: Path) -> str:
        ext = self.ext if self.ext is not None else F.full_ext(src)
        base = F.stem(src) + self.suffix
        if self.result == DIR:
            return base
        return f"{base}.{ext}" if ext else base


# --------------------------------------------------------------------------
# Helpers de construção de comandos
# --------------------------------------------------------------------------

def _ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        T.cmd("ffprobe") + ["-v", "error", "-show_entries", "format=duration",
                            "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def _ff(*args: str) -> list[str]:
    return T.cmd("ffmpeg") + ["-hide_banner", "-nostdin", "-y", *args]


def _magick(ctx: Ctx, *ops: str, frame0: bool = True) -> list[Step]:
    src = f"{ctx.src}[0]" if frame0 else str(ctx.src)
    return [T.cmd("magick") + [src, "-auto-orient", *ops, str(ctx.out)]]


def _ext_set(*exts: str) -> frozenset[str]:
    return frozenset(exts)


_SAME = {
    "jpg": _ext_set("jpg", "jpeg", "jpe", "jfif"),
    "tiff": _ext_set("tif", "tiff"),
    "heic": _ext_set("heic", "heif"),
    "html": _ext_set("html", "htm"),
    "md": _ext_set("md", "markdown"),
    "aiff": _ext_set("aif", "aiff"),
    "ogg": _ext_set("ogg", "oga"),
    "tar.gz": _ext_set("tar.gz", "tgz"),
}


def _same(ext: str) -> frozenset[str]:
    return _SAME.get(ext, _ext_set(ext))


# --------------------------------------------------------------------------
# CONVERTER — imagens
# --------------------------------------------------------------------------

def _img_to(ext: str) -> Callable[[Ctx], list[Step]]:
    def build(ctx: Ctx) -> list[Step]:
        src_ext = F.full_ext(ctx.src)
        animated = src_ext in ("gif", "webp") and ext in ("gif", "webp")
        extra: list[str] = []
        if F.kind_of(ctx.src) == F.VECTOR:
            return _svg_to(ctx, ext)
        if ext in ("jpg", "bmp"):
            extra = ["-background", "white", "-alpha", "remove", "-alpha", "off"]
        if ext == "jpg":
            extra += ["-quality", "92"]
        if ext == "ico":
            extra = ["-resize", "256x256>", "-define",
                     "icon:auto-resize=256,128,64,48,32,16"]
        return _magick(ctx, *extra, frame0=not animated)
    return build


def _svg_to(ctx: Ctx, ext: str) -> list[Step]:
    """SVG: o librsvg (rsvg-convert, já vem com o GNOME) renderiza melhor
    que o delegate do ImageMagick, que nem sempre está configurado."""
    if not T.has("rsvg-convert"):
        return [T.cmd("magick") + ["-density", "192", "-background", "none",
                                   str(ctx.src), str(ctx.out)]]
    rsvg = T.cmd("rsvg-convert")
    if ext in ("png", "pdf"):
        return [rsvg + ["-f", ext, "-z", "2" if ext == "png" else "1",
                        "-o", str(ctx.out), str(ctx.src)]]
    mid = ctx.work / "render.png"
    rest = ["-background", "white", "-alpha", "remove", "-alpha", "off"] \
        if ext in ("jpg", "bmp") else []
    return [rsvg + ["-f", "png", "-z", "2", "-o", str(mid), str(ctx.src)],
            T.cmd("magick") + [str(mid), *rest, str(ctx.out)]]


def _magick_can(fmt: str) -> Callable[[], bool]:
    return lambda: fmt in T.magick_writable()


_IMG_TARGETS = ["jpg", "png", "webp", "heic", "avif", "tiff", "bmp", "gif",
                "ico", "pdf"]

IMAGE_CONVERT = [
    Op(f"to-{e}", e.upper(), CONVERT, frozenset(F.IMAGES), _img_to(e), ext=e,
       needs=("magick",), skip_exts=_same(e),
       available=_magick_can("jpeg" if e == "jpg" else e))
    for e in _IMG_TARGETS
]

# --------------------------------------------------------------------------
# CONVERTER — vídeo e áudio
# --------------------------------------------------------------------------

_X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-pix_fmt", "yuv420p"]


def _video_to(ext: str) -> Callable[[Ctx], list[Step]]:
    def build(ctx: Ctx) -> list[Step]:
        i = ["-i", str(ctx.src)]
        o = str(ctx.out)
        if ext in ("mp4", "mov"):
            return [_ff(*i, *_X264, "-c:a", "aac", "-b:a", "160k",
                        "-movflags", "+faststart", o)]
        if ext == "mkv":
            # remux: rápido e sem perda; MKV aceita praticamente tudo
            return [_ff(*i, "-map", "0", "-c", "copy", o)]
        if ext == "webm":
            return [_ff(*i, "-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0",
                        "-row-mt", "1", "-deadline", "good", "-cpu-used", "4",
                        "-c:a", "libopus", "-b:a", "128k", o)]
        if ext == "avi":
            return [_ff(*i, "-c:v", "mpeg4", "-q:v", "3",
                        "-c:a", "libmp3lame", "-q:a", "3", o)]
        if ext == "gif":
            vf = ("fps=12,scale='min(480,iw)':-2:flags=lanczos,split[a][b];"
                  "[a]palettegen[p];[b][p]paletteuse")
            return [_ff(*i, "-vf", vf, "-loop", "0", o)]
        raise ValueError(ext)
    return build


_AUDIO_CODEC = {
    "mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    "m4a": ["-c:a", "aac", "-b:a", "192k"],
    "wav": ["-c:a", "pcm_s16le"],
    "flac": ["-c:a", "flac"],
    "ogg": ["-c:a", "libvorbis", "-q:a", "5"],
    "opus": ["-c:a", "libopus", "-b:a", "128k"],
    "aiff": ["-c:a", "pcm_s16be"],
}


def _audio_codec(ext: str) -> list[str]:
    if ext == "ogg" and not T.has_encoder("libvorbis"):
        return ["-c:a", "libopus", "-b:a", "128k"]
    return _AUDIO_CODEC[ext]


def _audio_to(ext: str) -> Callable[[Ctx], list[Step]]:
    def build(ctx: Ctx) -> list[Step]:
        return [_ff("-i", str(ctx.src), "-map", "0:a:0", "-vn",
                    "-map_metadata", "0", *_audio_codec(ext), str(ctx.out))]
    return build


def _enc(name: str) -> Callable[[], bool]:
    return lambda: T.has_encoder(name)


VIDEO_CONVERT = [
    Op("to-mp4", "MP4", CONVERT, frozenset({F.VIDEO}), _video_to("mp4"),
       ext="mp4", needs=("ffmpeg",), skip_exts=_same("mp4"),
       available=_enc("libx264")),
    Op("to-mov", "MOV", CONVERT, frozenset({F.VIDEO}), _video_to("mov"),
       ext="mov", needs=("ffmpeg",), skip_exts=_same("mov"),
       available=_enc("libx264")),
    Op("to-mkv", "MKV", CONVERT, frozenset({F.VIDEO}), _video_to("mkv"),
       ext="mkv", needs=("ffmpeg",), skip_exts=_same("mkv")),
    Op("to-webm", "WEBM", CONVERT, frozenset({F.VIDEO}), _video_to("webm"),
       ext="webm", needs=("ffmpeg",), skip_exts=_same("webm"),
       available=_enc("libvpx-vp9")),
    Op("to-avi", "AVI", CONVERT, frozenset({F.VIDEO}), _video_to("avi"),
       ext="avi", needs=("ffmpeg",), skip_exts=_same("avi")),
    Op("to-gif-video", "GIF", CONVERT, frozenset({F.VIDEO}), _video_to("gif"),
       ext="gif", needs=("ffmpeg",)),
] + [
    Op(f"to-{e}-audio", e.upper(), CONVERT, frozenset(F.MEDIA), _audio_to(e),
       ext=e, needs=("ffmpeg",), skip_exts=_same(e))
    for e in ("mp3", "m4a", "wav", "flac", "ogg", "opus", "aiff")
]


SUBTITLE_CONVERT = [
    Op(f"to-{e}-sub", e.upper(), CONVERT, frozenset({F.SUBTITLE}),
       (lambda c: [_ff("-i", str(c.src), str(c.out))]), ext=e,
       needs=("ffmpeg",), skip_exts=_same(e))
    for e in ("srt", "vtt", "ass")
]

# --------------------------------------------------------------------------
# CONVERTER — documentos (LibreOffice, pandoc, poppler)
# --------------------------------------------------------------------------


def _soffice(ctx: Ctx, src: Path, ext: str, filt: str | None = None,
             infilter: str | None = None) -> list[Step]:
    """LibreOffice headless com perfil próprio (não briga com uma janela do
    LibreOffice aberta) e saída num diretório temporário."""
    outdir = ctx.work / "lo"
    profile = (cache_dir() / "lo-profile").as_uri()
    target = f"{ext}:{filt}" if filt else ext
    argv = T.cmd("soffice") + [f"-env:UserInstallation={profile}",
                               "--headless", "--norestore"]
    if infilter:
        argv.append(f"--infilter={infilter}")
    argv += ["--convert-to", target, "--outdir", str(outdir), str(src)]

    def collect(c: Ctx) -> None:
        produced = outdir / f"{src.stem}.{ext}"
        if not produced.exists():
            raise RuntimeError("LibreOffice não gerou a saída "
                               f"({produced.name})")
        shutil.move(str(produced), c.out)
    return [argv, collect]


def _doc_to(ext: str) -> Callable[[Ctx], list[Step]]:
    filters = {"txt": "Text (encoded):UTF8", "csv": "Text - txt - csv (StarCalc):44,34,76"}

    def build(ctx: Ctx) -> list[Step]:
        if ext == "epub":
            return _pandoc_to(ctx, "epub")
        return _soffice(ctx, ctx.src, ext, filters.get(ext))
    return build


def _pandoc_to(ctx: Ctx, ext: str) -> list[Step]:
    src_ext = F.full_ext(ctx.src)
    readers = {"md": "markdown", "markdown": "markdown", "txt": "markdown",
               "html": "html", "htm": "html", "epub": "epub", "docx": "docx",
               "odt": "odt"}
    writer = {"txt": "plain", "md": "gfm", "html": "html", "epub": "epub",
              "docx": "docx", "odt": "odt"}[ext]
    argv = T.cmd("pandoc") + ["-f", readers.get(src_ext, "markdown"),
                              "-t", writer, "-o", str(ctx.out), str(ctx.src)]
    if ext in ("html", "epub"):
        argv.insert(-1, "--standalone")
        argv.insert(-1, f"--metadata=title:{F.stem(ctx.src)}")
    return [argv]


def _text_to(ext: str) -> Callable[[Ctx], list[Step]]:
    def build(ctx: Ctx) -> list[Step]:
        src_ext = F.full_ext(ctx.src)
        if ext == "pdf":
            # pandoc -> docx (sem LaTeX) e LibreOffice -> pdf
            if src_ext in ("txt",):
                return _soffice(ctx, ctx.src, "pdf")
            mid = ctx.work / f"{F.stem(ctx.src)}.docx"
            first = Ctx(ctx.src, ctx.srcs, ctx.work, mid)
            return _pandoc_to(first, "docx") + _soffice(ctx, mid, "pdf")
        return _pandoc_to(ctx, ext)
    return build


def _pdf_pages(fmt: str) -> Callable[[Ctx], list[Step]]:
    def build(ctx: Ctx) -> list[Step]:
        ctx.out.mkdir(parents=True, exist_ok=True)
        flag = "-png" if fmt == "png" else "-jpeg"
        return [T.cmd("pdftoppm") + [flag, "-r", "150", str(ctx.src),
                                     str(ctx.out / "pagina")]]
    return build


def _pdf_to_text(ctx: Ctx) -> list[Step]:
    return [T.cmd("pdftotext") + ["-layout", str(ctx.src), str(ctx.out)]]


def _pdf_to_docx(ctx: Ctx) -> list[Step]:
    return _soffice(ctx, ctx.src, "docx", "MS Word 2007 XML",
                    infilter="writer_pdf_import")


def _ebook_to(ext: str) -> Callable[[Ctx], list[Step]]:
    def build(ctx: Ctx) -> list[Step]:
        if ext == "pdf":
            mid = ctx.work / f"{F.stem(ctx.src)}.docx"
            first = Ctx(ctx.src, ctx.srcs, ctx.work, mid)
            return _pandoc_to(first, "docx") + _soffice(ctx, mid, "pdf")
        return _pandoc_to(ctx, ext)
    return build


DOC_CONVERT = (
    [Op(f"to-{e}-doc", e.upper(), CONVERT, frozenset({F.DOC_TEXT}),
        _doc_to(e), ext=e, needs=("soffice",), skip_exts=_same(e))
     for e in ("pdf", "docx", "odt", "rtf", "txt")]
    + [Op("to-epub-doc", "EPUB", CONVERT, frozenset({F.DOC_TEXT}),
          _doc_to("epub"), ext="epub", needs=("pandoc",),
          hint="Somente DOCX/ODT")]
    + [Op(f"to-{e}-slides", e.upper(), CONVERT, frozenset({F.DOC_SLIDES}),
          _doc_to(e), ext=e, needs=("soffice",), skip_exts=_same(e))
       for e in ("pdf", "pptx", "odp")]
    + [Op(f"to-{e}-sheet", e.upper(), CONVERT, frozenset({F.DOC_SHEET}),
          _doc_to(e), ext=e, needs=("soffice",), skip_exts=_same(e))
       for e in ("pdf", "xlsx", "ods", "csv")]
    + [Op("to-pdf-text", "PDF", CONVERT, frozenset({F.TEXT}), _text_to("pdf"),
          ext="pdf", needs=("soffice", "pandoc"))]
    + [Op(f"to-{e}-text", e.upper(), CONVERT, frozenset({F.TEXT}),
          _text_to(e), ext=e, needs=("pandoc",), skip_exts=_same(e))
       for e in ("docx", "odt", "html", "epub", "md", "txt")]
    + [Op(f"to-{e}-ebook", e.upper(), CONVERT, frozenset({F.EBOOK}),
          _ebook_to(e), ext=e, needs=("pandoc",)
          + (("soffice",) if e == "pdf" else ()))
       for e in ("pdf", "docx", "txt", "html", "md")]
    + [
        Op("pdf-to-png", "PNG", CONVERT, frozenset({F.PDF}), _pdf_pages("png"),
           result=DIR, suffix=" Pages", needs=("pdftoppm",),
           hint="Uma imagem por página"),
        Op("pdf-to-jpg", "JPG", CONVERT, frozenset({F.PDF}), _pdf_pages("jpg"),
           result=DIR, suffix=" Pages", needs=("pdftoppm",),
           hint="Uma imagem por página"),
        Op("pdf-to-txt", "TXT", CONVERT, frozenset({F.PDF}), _pdf_to_text,
           ext="txt", needs=("pdftotext",)),
        Op("pdf-to-docx", "DOCX", CONVERT, frozenset({F.PDF}), _pdf_to_docx,
           ext="docx", needs=("soffice",), hint="Experimental"),
    ]
)

# --------------------------------------------------------------------------
# CONVERTER — arquivos compactados e pastas (bsdtar/libarchive)
# --------------------------------------------------------------------------


def _extract(ctx: Ctx) -> list[Step]:
    ctx.out.mkdir(parents=True, exist_ok=True)
    return [T.cmd("bsdtar") + ["-xf", str(ctx.src), "-C", str(ctx.out)]]


def _pack(fmt: str) -> Callable[[Ctx], list[Step]]:
    """Empacota um arquivo/pasta (ou re-empacota um compactado via @)."""
    flags = {"zip": ["--format", "zip"], "7z": ["--format", "7zip"],
             "tar.gz": ["-z", "--format", "pax"]}[fmt]

    def build(ctx: Ctx) -> list[Step]:
        if F.kind_of(ctx.src) == F.ARCHIVE:
            members = ["@" + str(ctx.src)]
            argv = T.cmd("bsdtar") + ["-c", *flags, "-f", str(ctx.out),
                                      *members]
        else:
            argv = T.cmd("bsdtar") + ["-c", *flags, "-f", str(ctx.out),
                                      "-C", str(ctx.src.parent),
                                      ctx.src.name]
        return [argv]
    return build


ARCHIVE_CONVERT = [
    Op("extract", "Extrair", CONVERT, frozenset({F.ARCHIVE}), _extract,
       result=DIR, needs=("bsdtar",)),
] + [
    Op(f"pack-{f}", f.upper(), CONVERT,
       frozenset({F.ARCHIVE, F.FOLDER, F.OTHER}), _pack(f), ext=f,
       needs=("bsdtar",), skip_exts=_same(f))
    for f in ("zip", "7z", "tar.gz")
]

# --------------------------------------------------------------------------
# CONVERTER — Xournal++
# --------------------------------------------------------------------------

def _xopp_to_pdf(ctx: Ctx) -> list[Step]:
    from . import xopp
    return [lambda c: xopp.xopp_to_pdf(c.src, c.out, c.work)]


def _pdf_to_xopp(ctx: Ctx) -> list[Step]:
    from . import xopp
    return [lambda c: xopp.pdf_to_xopp(c.src, c.out)]


XOPP_CONVERT = [
    Op("xopp-to-pdf", "PDF", CONVERT, frozenset({F.XOPP}), _xopp_to_pdf,
       ext="pdf", needs=("qpdf",), hint="Exporta o caderno"),
    Op("pdf-to-xopp", "XOPP", CONVERT, frozenset({F.PDF}), _pdf_to_xopp,
       ext="xopp", needs=("pdfinfo",), hint="Abre o PDF para anotar"),
]

# --------------------------------------------------------------------------
# FERRAMENTAS
# --------------------------------------------------------------------------


def _img_tool(*ops: str) -> Callable[[Ctx], list[Step]]:
    return lambda ctx: _magick(ctx, *ops, frame0=False)


def _strip(ctx: Ctx) -> list[Step]:
    kind = F.kind_of(ctx.src)
    if kind in F.MEDIA:
        return [_ff("-i", str(ctx.src), "-map", "0", "-map_metadata", "-1",
                    "-c", "copy", str(ctx.out))]
    if kind == F.PDF:
        mid = ctx.work / "sem-meta.pdf"
        # exiftool só "esconde" (incremental update); qpdf reescreve o arquivo
        return [T.cmd("exiftool") + ["-q", "-all:all=", "-o", str(mid),
                                     str(ctx.src)],
                T.cmd("qpdf") + ["--linearize", str(mid), str(ctx.out)]]
    return [T.cmd("exiftool") + ["-q", "-all=", "-o", str(ctx.out),
                                 str(ctx.src)]]


def _strip_available() -> bool:
    return T.has("exiftool")


def _show_meta(ctx: Ctx) -> list[Step]:
    def run(c: Ctx) -> None:
        out = subprocess.run(T.cmd("exiftool") + ["-G1", "-s", str(c.src)],
                             capture_output=True, text=True).stdout
        c.text.append(f"── {c.src.name} ──\n{out.strip()}")
    return [run]


def _read_qr(ctx: Ctx) -> list[Step]:
    def run(c: Ctx) -> None:
        proc = subprocess.run(T.cmd("zbarimg") + ["--raw", "-q", str(c.src)],
                              capture_output=True, text=True)
        if proc.returncode not in (0, 4) and not proc.stdout:
            raise RuntimeError(proc.stderr.strip() or "falha ao ler código")
        found = proc.stdout.strip()
        if not found:
            raise RuntimeError("Nenhum QR code encontrado")
        c.text.append(found)
    return [run]


def _video_compress(ctx: Ctx) -> list[Step]:
    return [_ff("-i", str(ctx.src), "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "28", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-b:a", "128k", "-movflags", "+faststart", str(ctx.out))]


def _video_target_size(mb: int) -> Callable[[Ctx], list[Step]]:
    def build(ctx: Ctx) -> list[Step]:
        def run(c: Ctx) -> None:
            dur = max(_ffprobe_duration(c.src), 0.1)
            audio_k = 96
            total_k = mb * 8192 * 0.93 / dur          # margem de 7% p/ container
            video_k = max(int(total_k - audio_k), 60)
            subprocess.run(_ff("-i", str(c.src), "-c:v", "libx264",
                               "-preset", "veryfast", "-b:v", f"{video_k}k",
                               "-maxrate", f"{video_k}k",
                               "-bufsize", f"{video_k * 2}k",
                               "-pix_fmt", "yuv420p", "-c:a", "aac",
                               "-b:a", f"{audio_k}k",
                               "-movflags", "+faststart", str(c.out)),
                           check=True, capture_output=True)
        return [run]
    return build


def _video_snapshot(ctx: Ctx) -> list[Step]:
    def run(c: Ctx) -> None:
        mid = _ffprobe_duration(c.src) / 2
        subprocess.run(_ff("-ss", f"{mid:.3f}", "-i", str(c.src),
                           "-frames:v", "1", "-q:v", "2", str(c.out)),
                       check=True, capture_output=True)
    return [run]


def _concat(ctx: Ctx, video: bool) -> list[Step]:
    lst = ctx.work / "lista.txt"
    lines = []
    for p in ctx.srcs:
        safe = str(p).replace("'", r"'\''")
        lines.append(f"file '{safe}'")
    lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    codec = (_X264 + ["-c:a", "aac", "-b:a", "160k"]) if video \
        else _audio_codec(F.full_ext(ctx.out))
    return [_ff("-f", "concat", "-safe", "0", "-i", str(lst), *codec,
                str(ctx.out))]


def _audio_same(*af: str) -> Callable[[Ctx], list[Step]]:
    def build(ctx: Ctx) -> list[Step]:
        ext = F.full_ext(ctx.out)
        codec = _audio_codec(ext) if ext in _AUDIO_CODEC else []
        return [_ff("-i", str(ctx.src), "-map", "0:a:0", "-vn", *af, *codec,
                    str(ctx.out))]
    return build


_IMG1 = frozenset({F.IMAGE})

RMBG_FUZZ = "12%"        # tolerância de cor do fundo liso


def _remove_bg(ctx: Ctx) -> list[Step]:
    """Fundo transparente. Com `rembg` (IA) funciona em qualquer foto; sem
    ele, preenche a partir dos 4 cantos com tolerância de cor (fundos
    lisos: logos, produtos, prints, documentos) e suaviza a borda."""
    if T.has("rembg"):
        return [T.cmd("rembg") + ["i", str(ctx.src), str(ctx.out)]]

    def run(c: Ctx) -> None:
        from .edits import image_size
        w, h = image_size(c.src)
        fills = []
        for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            fills += ["-draw", f"color {x},{y} floodfill"]
        subprocess.run(
            T.cmd("magick") + [
                f"{c.src}[0]", "-auto-orient", "-alpha", "set",
                "-fuzz", RMBG_FUZZ, "-fill", "none", *fills,
                "-channel", "A", "-blur", "0x0.7", "-level", "40%,100%",
                "+channel", str(c.out)],
            check=True, capture_output=True, stdin=subprocess.DEVNULL)
    return [run]


TOOL_OPS = [
    # janelas primeiro: ficam no topo da roda
    Op("img-edit", "Editar…", TOOLS, _IMG1, mode=EDITOR, max_files=1,
       needs=("magick",), hint="Recortar, girar, cor, tamanho"),
    Op("img-crop", "Recortar…", TOOLS, _IMG1, mode=EDITOR, max_files=1,
       needs=("magick",), hint="Recorte com proporção"),
    Op("img-addbg", "Fundo…", TOOLS, _IMG1, mode=EDITOR, max_files=1,
       needs=("magick",), hint="Fundo, cantos e sombra"),
    Op("img-rmbg", "Remover fundo", TOOLS, _IMG1, _remove_bg, ext="png",
       suffix=" Without Background", needs=("magick",),
       hint="Fundo transparente (PNG)"),
    Op("img-size", "Tamanho…", TOOLS, _IMG1, mode=EDITOR,
       needs=("magick",), hint="Dimensões, qualidade e peso"),
    Op("vid-trim", "Cortar…", TOOLS, frozenset({F.VIDEO}), mode=EDITOR,
       max_files=1, needs=("ffmpeg", "ffprobe"), hint="Escolher o trecho"),
    Op("vid-size", "Tamanho…", TOOLS, frozenset({F.VIDEO}), mode=EDITOR,
       needs=("ffmpeg", "ffprobe"), hint="Caber em X MB, resolução"),
    Op("aud-trim", "Cortar…", TOOLS, frozenset({F.AUDIO}), mode=EDITOR,
       max_files=1, needs=("ffmpeg", "ffprobe"), hint="Escolher o trecho"),
    Op("pdf-pages", "Páginas…", TOOLS, frozenset({F.PDF}), mode=EDITOR,
       max_files=1, needs=("qpdf", "pdftoppm"),
       hint="Extrair, apagar ou girar páginas"),
    # imagens
    Op("img-compress", "Comprimir", TOOLS, frozenset({F.IMAGE}),
       _img_tool("-strip", "-quality", "75"), suffix=" Compressed",
       needs=("magick",), hint="Qualidade 75, sem metadados"),
    Op("img-1mb", "≤ 1 MB", TOOLS, frozenset({F.IMAGE}),
       lambda c: _magick(c, "-strip", "-background", "white", "-alpha",
                         "remove", "-define", "jpeg:extent=1000KB"),
       ext="jpg", suffix=" 1MB", needs=("magick",), hint="JPG de até 1 MB",
       in_wheel=False),
    Op("img-half", "50%", TOOLS, frozenset({F.IMAGE}),
       _img_tool("-resize", "50%"), suffix=" Half", needs=("magick",),
       hint="Reduz pela metade", in_wheel=False),
    Op("img-rotate", "Girar 90°", TOOLS, frozenset({F.IMAGE}),
       _img_tool("-rotate", "90"), suffix=" Rotated", needs=("magick",)),
    Op("img-flip", "Espelhar", TOOLS, frozenset({F.IMAGE}),
       _img_tool("-flop"), suffix=" Flipped", needs=("magick",),
       in_wheel=False),
    Op("img-gray", "P&B", TOOLS, frozenset({F.IMAGE}),
       _img_tool("-colorspace", "Gray"), suffix=" Grayscale", needs=("magick",),
       in_wheel=False),
    Op("img-qr", "Ler QR", TOOLS, frozenset({F.IMAGE}), _read_qr,
       result=TEXT, needs=("zbarimg",), hint="Copia o conteúdo"),
    Op("img-pdf", "Juntar PDF", TOOLS, frozenset({F.IMAGE}),
       lambda c: [T.cmd("magick") + [*map(str, c.srcs), "-auto-orient",
                                     str(c.out)]],
       ext="pdf", suffix=" Merged", mode=ALL, needs=("magick",),
       available=_magick_can("pdf"), hint="Todas as imagens num PDF"),
    Op("img-collage", "Colagem", TOOLS, frozenset({F.IMAGE}),
       lambda c: [T.cmd("montage") + [*map(str, c.srcs), "-auto-orient",
                                      "-geometry", "600x600+6+6",
                                      "-background", "white", str(c.out)]],
       ext="jpg", suffix=" Collage", mode=ALL, min_files=2,
       needs=("montage",)),
    # vídeo
    Op("vid-compress", "Comprimir", TOOLS, frozenset({F.VIDEO}),
       _video_compress, ext="mp4", suffix=" Compressed", needs=("ffmpeg",),
       hint="H.264 CRF 28"),
    Op("vid-25mb", "≤ 25 MB", TOOLS, frozenset({F.VIDEO}),
       _video_target_size(25), ext="mp4", suffix=" 25MB",
       needs=("ffmpeg", "ffprobe"), in_wheel=False),
    Op("vid-10mb", "≤ 10 MB", TOOLS, frozenset({F.VIDEO}),
       _video_target_size(10), ext="mp4", suffix=" 10MB",
       needs=("ffmpeg", "ffprobe"), in_wheel=False),
    Op("vid-mute", "Sem áudio", TOOLS, frozenset({F.VIDEO}),
       lambda c: [_ff("-i", str(c.src), "-map", "0:v", "-c", "copy", "-an",
                      str(c.out))],
       suffix=" Muted", needs=("ffmpeg",)),
    Op("vid-2x", "2× vel.", TOOLS, frozenset({F.VIDEO}),
       lambda c: [_ff("-i", str(c.src), "-vf", "setpts=0.5*PTS",
                      "-af", "atempo=2.0", *_X264, "-c:a", "aac",
                      str(c.out))],
       ext="mp4", suffix=" 2x Speed", needs=("ffmpeg",)),
    Op("vid-rotate", "Girar 90°", TOOLS, frozenset({F.VIDEO}),
       lambda c: [_ff("-i", str(c.src), "-vf", "transpose=1", *_X264,
                      "-c:a", "copy", str(c.out))],
       ext="mp4", suffix=" Rotated", needs=("ffmpeg",)),
    Op("vid-snap", "Snapshot", TOOLS, frozenset({F.VIDEO}), _video_snapshot,
       ext="jpg", suffix=" Snapshot", needs=("ffmpeg", "ffprobe"),
       hint="Quadro do meio do vídeo"),
    Op("vid-join", "Juntar", TOOLS, frozenset({F.VIDEO}),
       lambda c: _concat(c, video=True), ext="mp4", suffix=" Merged",
       mode=ALL, min_files=2, needs=("ffmpeg",),
       hint="Mesma resolução recomendada"),
    # áudio
    Op("aud-normalize", "Normalizar", TOOLS, frozenset({F.AUDIO}),
       _audio_same("-af", "loudnorm=I=-16:TP=-1.5:LRA=11"),
       suffix=" Normalized", needs=("ffmpeg",), hint="EBU R128, -16 LUFS"),
    Op("aud-compress", "Comprimir", TOOLS, frozenset({F.AUDIO}),
       lambda c: [_ff("-i", str(c.src), "-map", "0:a:0", "-vn",
                      "-c:a", "libmp3lame", "-b:a", "128k", str(c.out))],
       ext="mp3", suffix=" Compressed", needs=("ffmpeg",),
       hint="MP3 128 kbps"),
    Op("aud-mono", "Mono", TOOLS, frozenset({F.AUDIO}),
       _audio_same("-ac", "1"), suffix=" Mono", needs=("ffmpeg",)),
    Op("aud-silence", "Tirar silêncio", TOOLS, frozenset({F.AUDIO}),
       _audio_same("-af", "silenceremove=start_periods=1:start_threshold="
                   "-50dB:stop_periods=-1:stop_threshold=-50dB:"
                   "stop_duration=0.6"),
       suffix=" Without Silence", needs=("ffmpeg",)),
    Op("aud-join", "Juntar", TOOLS, frozenset({F.AUDIO}),
       lambda c: _concat(c, video=False), suffix=" Merged", mode=ALL,
       min_files=2, needs=("ffmpeg",)),
    # PDF
    Op("pdf-compress", "Comprimir", TOOLS, frozenset({F.PDF}),
       lambda c: [T.cmd("gs") + ["-sDEVICE=pdfwrite",
                                 "-dPDFSETTINGS=/ebook",
                                 "-dCompatibilityLevel=1.5", "-dNOPAUSE",
                                 "-dBATCH", "-dQUIET",
                                 f"-sOutputFile={c.out}", str(c.src)]],
       suffix=" Compressed", needs=("gs",), hint="Ghostscript /ebook"),
    Op("pdf-split", "Dividir", TOOLS, frozenset({F.PDF}),
       lambda c: (c.out.mkdir(parents=True, exist_ok=True),
                  [T.cmd("qpdf") + ["--split-pages", str(c.src),
                                    str(c.out / "pagina-%d.pdf")]])[1],
       result=DIR, suffix=" Pages", needs=("qpdf",),
       hint="Um PDF por página"),
    Op("pdf-rotate", "Girar 90°", TOOLS, frozenset({F.PDF}),
       lambda c: [T.cmd("qpdf") + [str(c.src), str(c.out), "--rotate=+90"]],
       suffix=" Rotated", needs=("qpdf",)),
    Op("pdf-images", "Extrair imagens", TOOLS, frozenset({F.PDF}),
       lambda c: (c.out.mkdir(parents=True, exist_ok=True),
                  [T.cmd("pdfimages") + ["-all", str(c.src),
                                         str(c.out / "img")]])[1],
       result=DIR, suffix=" Images", needs=("pdfimages",)),
    Op("pdf-merge", "Juntar", TOOLS, frozenset({F.PDF}),
       lambda c: [T.cmd("qpdf") + ["--empty", "--pages",
                                   *map(str, c.srcs), "--", str(c.out)]],
       suffix=" Merged", mode=ALL, min_files=2, needs=("qpdf",)),
    # genéricas
    Op("strip-meta", "Sem metadados", TOOLS,
       frozenset({F.IMAGE, F.PDF, F.VIDEO, F.AUDIO}), _strip,
       suffix=" Without Metadata", needs=("exiftool",),
       hint="Remove EXIF/GPS/autor"),
    Op("show-meta", "Metadados", TOOLS, frozenset(F.FILES), _show_meta,
       result=TEXT, needs=("exiftool",), hint="Ler metadados"),
]

# --------------------------------------------------------------------------
# AÇÕES (executadas pelo app; aqui só a declaração)
# --------------------------------------------------------------------------

ACTION_OPS = [
    Op("act-copy-path", "Copiar caminho", ACTIONS, frozenset(F.ANY),
       mode=ACTION),
    Op("act-terminal", "Terminal", ACTIONS, frozenset(F.ANY), mode=ACTION,
       hint="Abre um terminal na pasta"),
    Op("act-copy-to", "Copiar para…", ACTIONS, frozenset(F.ANY), mode=ACTION),
    Op("act-move-to", "Mover para…", ACTIONS, frozenset(F.ANY), mode=ACTION),
    Op("act-float", "Flutuar", ACTIONS, frozenset(F.ANY), mode=ACTION,
       hint="Janela flutuante para arrastar depois"),
    Op("act-zip-all", "ZIP", ACTIONS, frozenset(F.ANY), _pack("zip"),
       ext="zip", mode=ALL, needs=("bsdtar",), hint="Tudo num ZIP"),
]

ALL_OPS: list[Op] = (IMAGE_CONVERT + VIDEO_CONVERT + SUBTITLE_CONVERT
                     + DOC_CONVERT + ARCHIVE_CONVERT + XOPP_CONVERT
                     + TOOL_OPS + ACTION_OPS)
BY_ID = {op.id: op for op in ALL_OPS}
assert len(BY_ID) == len(ALL_OPS), "ids de operação duplicados"

# Vídeo na roda de conversão: só os alvos de áudio mais úteis
_VIDEO_AUDIO_OK = {"to-mp3-audio", "to-m4a-audio", "to-wav-audio"}


def options_for(paths: list[Path], group: str) -> list[Op]:
    """Operações oferecidas para esse conjunto de arquivos numa roda."""
    paths = [Path(p) for p in paths]
    if not paths:
        return []
    kinds = {F.kind_of(p) for p in paths}
    exts = {F.full_ext(p) for p in paths}
    out = []
    for op in ALL_OPS:
        if op.group != group:
            continue
        if not kinds <= op.kinds:
            continue
        if not op.in_wheel:
            continue
        if op.mode == ALL and len(paths) < max(op.min_files, 1):
            continue
        if op.max_files and len(paths) > op.max_files:
            continue
        if exts and exts <= op.skip_exts:
            continue
        if F.VIDEO in kinds and op.id.endswith("-audio") \
                and op.id not in _VIDEO_AUDIO_OK:
            continue
        if op.id == "to-epub-doc" and not exts <= {"docx", "odt"}:
            continue
        if op.id == "img-pdf" and len(paths) < 2:
            continue  # imagem única -> PDF já está na roda de conversão
        if not op.is_available():
            continue
        out.append(op)
    return out
