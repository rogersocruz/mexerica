"""Operações parametrizadas pelas janelas de edição (Recortar…, Cortar…).

As janelas só coletam parâmetros; aqui eles viram passos para o mesmo
runner das rodas (nunca sobrescreve, escreve em temporário antes). Puro
Python, sem GTK, para dar para testar.
"""
from __future__ import annotations

import dataclasses
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import formats as F
from . import tools as T
from .ops import (ALL, EACH, Ctx, Op, Step, _AUDIO_CODEC, _X264, _audio_codec,
                  _ff, _ffprobe_duration)


def derive(base: Op, build, **changes) -> Op:
    """Op concreta, executável pelo runner, a partir da Op da roda."""
    changes.setdefault("mode", EACH)
    changes.setdefault("label", base.label.rstrip("…"))
    return dataclasses.replace(base, build=build, **changes)


# --------------------------------------------------------------------------
# Imagem
# --------------------------------------------------------------------------

@dataclass
class ImageEdit:
    rotate: int = 0                 # 0/90/180/270, sentido horário
    flip_h: bool = False
    flip_v: bool = False
    # recorte normalizado (x, y, w, h) na imagem já girada/espelhada
    crop: tuple[float, float, float, float] | None = None
    brightness: int = 0             # -100..100
    contrast: int = 0               # -100..100
    saturation: int = 0             # -100..100 (-100 = P&B)
    scale: int = 100                # %
    max_side: int = 0               # 0 = sem limite
    quality: int = 90
    ext: str | None = None          # None = mesmo formato
    target_kb: int = 0              # só JPG

    def crop_px(self, w: int, h: int) -> tuple[int, int, int, int] | None:
        if not self.crop:
            return None
        if self.rotate in (90, 270):
            w, h = h, w
        x, y, cw, ch = self.crop
        px, py = round(x * w), round(y * h)
        pw = max(1, min(round(cw * w), w - px))
        ph = max(1, min(round(ch * h), h - py))
        if (px, py, pw, ph) == (0, 0, w, h):
            return None
        return px, py, pw, ph

    def args(self, w: int, h: int, out_ext: str) -> list[str]:
        """Argumentos do magick entre a entrada e a saída. `w`, `h` são as
        dimensões da imagem já com -auto-orient."""
        a: list[str] = []
        if self.rotate % 360:
            a += ["-rotate", str(self.rotate % 360)]
        if self.flip_h:
            a.append("-flop")
        if self.flip_v:
            a.append("-flip")
        c = self.crop_px(w, h)
        if c:
            a += ["-crop", f"{c[2]}x{c[3]}+{c[0]}+{c[1]}", "+repage"]
        if self.brightness or self.contrast:
            a += ["-brightness-contrast", f"{self.brightness}x{self.contrast}"]
        if self.saturation <= -100:
            a += ["-colorspace", "Gray"]
        elif self.saturation:
            a += ["-modulate", f"100,{100 + self.saturation}"]
        if self.scale and self.scale != 100:
            a += ["-resize", f"{self.scale}%"]
        if self.max_side:
            a += ["-resize", f"{self.max_side}x{self.max_side}>"]
        if out_ext in ("jpg", "jpeg", "bmp"):
            a += ["-background", "white", "-alpha", "remove", "-alpha", "off"]
        if out_ext in ("jpg", "jpeg", "webp", "avif", "heic", "jxl"):
            a += ["-quality", str(self.quality)]
        if out_ext in ("jpg", "jpeg") and self.target_kb:
            a += ["-define", f"jpeg:extent={self.target_kb}KB"]
        if self.ext is not None or self.max_side or self.scale != 100:
            a.append("-strip")   # reexportando: sem EXIF velho (orientação!)
        return a


_SWAPS_AXES = {"LeftTop", "RightTop", "RightBottom", "LeftBottom"}


def image_size(path: Path) -> tuple[int, int]:
    """Dimensões depois de -auto-orient (como o usuário vê a foto). Usa
    -ping: lê só o cabeçalho, sem decodificar a imagem."""
    out = subprocess.run(
        T.cmd("magick") + ["-ping", f"{path}[0]", "-format",
                           "%w %h %[orientation]", "info:"],
        capture_output=True, text=True, check=True).stdout.split()
    w, h = int(out[0]), int(out[1])
    return (h, w) if len(out) > 2 and out[2] in _SWAPS_AXES else (w, h)


def image_edit_op(base: Op, edit: ImageEdit, suffix: str) -> Op:
    def build(ctx: Ctx) -> list[Step]:
        def run(c: Ctx) -> None:
            w, h = image_size(c.src)
            ext = F.full_ext(c.out)
            argv = T.cmd("magick") + [f"{c.src}[0]", "-auto-orient",
                                      *edit.args(w, h, ext), str(c.out)]
            proc = subprocess.run(argv, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip()[-400:] or "magick falhou")
        return [run]
    ext = None if edit.ext is None else ("jpg" if edit.ext == "jpeg"
                                         else edit.ext)
    return derive(base, build, ext=ext, suffix=suffix)


def add_background_op(base: Op, style) -> Op:
    """Imagem sobre fundo (engine/background.py). Sempre PNG: os cantos
    arredondados e a sombra precisam de transparência na prévia, e o
    resultado costuma ir para apresentações e posts."""
    from .background import render_file

    def build(ctx: Ctx) -> list[Step]:
        return [lambda c: render_file(c.src, c.out, style, c.work)]
    return derive(base, build, ext="png", suffix=" With Background")


# --------------------------------------------------------------------------
# Vídeo / áudio
# --------------------------------------------------------------------------

def duration(path: Path) -> float:
    return _ffprobe_duration(path)


def keyframe_before(path: Path, t: float) -> float:
    """Onde um corte sem recodificar que pede `t` realmente começa: o
    quadro-chave de vídeo em `t` ou antes. Lê só quadros-chave (rápido)."""
    lo = max(t - 30.0, 0.0)
    out = subprocess.run(
        T.cmd("ffprobe") + ["-v", "error", "-select_streams", "v:0",
                            "-skip_frame", "nokey", "-show_entries",
                            "frame=pts_time", "-of", "csv=p=0",
                            "-read_intervals", f"{lo:.3f}%{t + 0.001:.3f}",
                            str(path)],
        capture_output=True, text=True).stdout
    times = []
    for line in out.split():
        try:
            times.append(float(line.strip(",")))
        except ValueError:
            pass
    before = [x for x in times if x <= t + 1e-3]
    return max(before) if before else 0.0


def _ts(t: float) -> str:
    return f"{max(t, 0.0):.3f}"


def trim_op(base: Op, start: float, end: float, fast: bool,
            remove: bool = False) -> Op:
    """Corta [start, end]. `remove=True` tira o trecho e junta o resto.
    `fast` copia os fluxos (instantâneo; o início cai no quadro-chave
    anterior); sem ele recodifica e o corte é exato."""
    def build(ctx: Ctx) -> list[Step]:
        video = F.kind_of(ctx.src) == F.VIDEO
        ext = F.full_ext(ctx.out)
        if video:
            enc = _X264 + ["-c:a", "aac", "-b:a", "160k"]
        else:
            enc = _audio_codec(ext) if ext in _AUDIO_CODEC else []
        codec = ["-c", "copy"] if fast else enc
        maps = ["-map", "0:v:0?", "-map", "0:a?"] if video \
            else ["-map", "0:a:0", "-vn"]
        if not remove:
            return [_ff("-ss", _ts(start), "-i", str(ctx.src),
                        "-t", _ts(end - start), *maps, *codec,
                        "-avoid_negative_ts", "make_zero", str(ctx.out))]
        # tirar o meio: corta as duas pontas e concatena
        a, b = ctx.work / f"a.{ext}", ctx.work / f"b.{ext}"
        parts, steps = [], []
        if start > 0.05:
            steps.append(_ff("-i", str(ctx.src), "-t", _ts(start), *maps,
                             *codec, str(a)))
            parts.append(a)
        steps.append(_ff("-ss", _ts(end), "-i", str(ctx.src), *maps, *codec,
                         "-avoid_negative_ts", "make_zero", str(b)))
        parts.append(b)
        lst = ctx.work / "lista.txt"
        lst.write_text("".join(f"file '{p.name}'\n" for p in parts),
                       encoding="utf-8")
        steps.append(_ff("-f", "concat", "-safe", "0", "-i", str(lst),
                         "-c", "copy", str(ctx.out)))
        return steps
    return derive(base, build, suffix=" Cut" if remove else " Trimmed")


def video_size_op(base: Op, target_mb: float, height: int, mute: bool) -> Op:
    """Recodifica para caber em `target_mb` (0 = só qualidade CRF 26),
    opcionalmente reduzindo para `height` linhas."""
    def build(ctx: Ctx) -> list[Step]:
        def run(c: Ctx) -> None:
            vf = ["-vf", f"scale=-2:'min({height},ih)'"] if height else []
            audio = ["-an"] if mute else ["-c:a", "aac", "-b:a", "96k"]
            if target_mb:
                dur = max(_ffprobe_duration(c.src), 0.1)
                total_k = target_mb * 8192 * 0.93 / dur
                video_k = max(int(total_k - (0 if mute else 96)), 60)
                rate = ["-b:v", f"{video_k}k", "-maxrate", f"{video_k}k",
                        "-bufsize", f"{video_k * 2}k"]
            else:
                rate = ["-crf", "26"]
            argv = _ff("-i", str(c.src), *vf, "-c:v", "libx264",
                       "-preset", "veryfast", *rate, "-pix_fmt", "yuv420p",
                       *audio, "-movflags", "+faststart", str(c.out))
            proc = subprocess.run(argv, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip()[-400:] or "ffmpeg falhou")
        return [run]
    tag = f" {target_mb:g}MB" if target_mb else " Compressed"
    return derive(base, build, ext="mp4", suffix=tag)


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

def page_count(path: Path) -> int:
    out = subprocess.run(T.cmd("qpdf") + ["--show-npages", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return int(out.strip())


def _ranges(pages: list[int]) -> str:
    """[1,2,3,5] -> '1-3,5'"""
    out, pages = [], sorted(set(pages))
    i = 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1:
            j += 1
        out.append(str(pages[i]) if i == j else f"{pages[i]}-{pages[j]}")
        i = j + 1
    return ",".join(out)


def pdf_pages_op(base: Op, action: str, pages: list[int], total: int) -> Op:
    """action: 'extract' (só as escolhidas), 'delete' (sem as escolhidas),
    'rotate' (gira as escolhidas 90°, mantém o resto)."""
    if not pages:
        raise ValueError("nenhuma página escolhida")
    keep = pages if action == "extract" else \
        [p for p in range(1, total + 1) if p not in set(pages)] \
        if action == "delete" else list(range(1, total + 1))
    if not keep:
        raise ValueError("isso apagaria todas as páginas")

    def build(ctx: Ctx) -> list[Step]:
        q = T.cmd("qpdf")
        if action == "rotate":
            return [q + [str(ctx.src), str(ctx.out),
                         f"--rotate=+90:{_ranges(pages)}"]]
        return [q + ["--empty", "--pages", str(ctx.src), _ranges(keep), "--",
                     str(ctx.out)]]
    label = "Page" if len(pages) == 1 else "Pages"
    suffix = {"extract": f" {label} " + _ranges(pages).replace(",", " "),
              "delete": " Edited",
              "rotate": " Rotated"}[action]
    return derive(base, build, suffix=suffix)


__all__ = ["ImageEdit", "image_edit_op", "image_size", "trim_op",
           "add_background_op",
           "keyframe_before",
           "video_size_op", "pdf_pages_op", "page_count", "duration",
           "derive", "ALL", "EACH"]
