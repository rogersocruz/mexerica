"""Operações parametrizadas pelas janelas de edição (Recortar…, Cortar…).

As janelas só coletam parâmetros; aqui eles viram passos para o mesmo
runner das rodas (nunca sobrescreve, escreve em temporário antes). Puro
Python, sem GTK, para dar para testar.
"""
from __future__ import annotations

import dataclasses
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..i18n import _
from . import formats as F
from . import tools as T
from .ops import (ALL, DIR, EACH, Ctx, Op, Step, _AUDIO_CODEC, _X264,
                  _audio_codec, _ff, _ffprobe_duration)


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
        raise ValueError(_("Nenhuma página escolhida."))
    keep = pages if action == "extract" else \
        [p for p in range(1, total + 1) if p not in set(pages)] \
        if action == "delete" else list(range(1, total + 1))
    if not keep:
        raise ValueError(_("Isso apagaria todas as páginas."))

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


def parse_ranges(text: str, total: int) -> list[list[int]]:
    """'1-3, 5, 8-' -> [[1,2,3], [5], [8..total]]. Cada trecho vira uma
    parte; '-4' começa na 1 e '8-' vai até o fim. Páginas fora do PDF ou
    trecho de trás para a frente dão ValueError com a explicação."""
    parts = []
    for chunk in text.replace(";", ",").split(","):
        chunk = chunk.strip().replace(" ", "").replace("–", "-")
        if not chunk:
            continue
        a, sep, b = chunk.partition("-")
        try:
            first = int(a) if a else 1
            last = (int(b) if b else total) if sep else first
        except ValueError:
            raise ValueError(_("\"{chunk}\" não é um intervalo (tente "
                               "1-3, 5, 8-)").format(chunk=chunk)) from None
        if first < 1 or last > total:
            raise ValueError(_("\"{chunk}\": o PDF tem as páginas 1 a "
                               "{total}").format(chunk=chunk, total=total))
        if first > last:
            raise ValueError(_("\"{chunk}\": começa depois de onde "
                               "termina").format(chunk=chunk))
        parts.append(list(range(first, last + 1)))
    if not parts:
        raise ValueError(_("Digite os intervalos (por exemplo 1-3, 5, "
                           "8-)."))
    return parts


def every(n: int, total: int) -> list[list[int]]:
    """Partes de n páginas (a última pode ser menor)."""
    if n < 1:
        raise ValueError("n precisa ser pelo menos 1")
    return [list(range(i, min(i + n, total + 1)))
            for i in range(1, total + 1, n)]


def cuts_to_text(cuts: set[int], total: int) -> str:
    """Páginas que começam uma parte nova -> '1-3, 4-7, 8-10'."""
    starts = sorted({1} | {c for c in cuts if 1 < c <= total})
    ends = [s - 1 for s in starts[1:]] + [total]
    return ", ".join(str(a) if a == b else f"{a}-{b}"
                     for a, b in zip(starts, ends))


def pdf_split_op(base: Op, parts: list[list[int]]) -> Op:
    """Um PDF por parte, numa pasta: 'doc 1-3.pdf', 'doc 4-7.pdf'..."""
    if not parts:
        raise ValueError("nenhuma parte")
    if len(parts) == 1:
        # um intervalo só: o PDF solto, sem pasta ("doc 3-7.pdf")
        pages = parts[0]

        def one(ctx: Ctx) -> list[Step]:
            return [T.cmd("qpdf") + ["--empty", "--pages", str(ctx.src),
                                     _ranges_ordered(pages), "--",
                                     str(ctx.out)]]
        return derive(base, one, ext="pdf",
                      suffix=" " + _ranges(pages).replace(",", " "))

    def build(ctx: Ctx) -> list[Step]:
        ctx.out.mkdir(parents=True, exist_ok=True)
        stem = F.stem(ctx.src)
        steps, names = [], set()
        for part in parts:
            name = f"{stem} {_ranges(part).replace(',', ' ')}"
            while name in names:            # o mesmo trecho duas vezes
                name += "+"
            names.add(name)
            steps.append(T.cmd("qpdf") + [
                "--empty", "--pages", str(ctx.src), _ranges_ordered(part),
                "--", str(ctx.out / f"{name}.pdf")])
        return steps
    return derive(base, build, result=DIR, suffix=" Parts")


def _ranges_ordered(pages: list[int]) -> str:
    """Como _ranges, mas sem reordenar (o qpdf respeita a ordem dada)."""
    if pages == sorted(set(pages)):
        return _ranges(pages)
    return ",".join(map(str, pages))


@dataclass(frozen=True)
class PageRef:
    """Uma página na tela do organizador: de qual arquivo (índice na lista
    de caminhos), qual página (1..n) e quanto girar (0/90/180/270,
    sentido horário, somado à rotação que ela já tem)."""
    src: int
    page: int
    rotate: int = 0


def _compact(pages: list[int]) -> str:
    """Páginas na ordem dada, com as sequências crescentes encurtadas:
    [1,2,3,7,5,6] -> '1-3,7,5-6' (o qpdf respeita a ordem)."""
    out, i = [], 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1:
            j += 1
        out.append(str(pages[i]) if i == j else f"{pages[i]}-{pages[j]}")
        i = j + 1
    return ",".join(out)


def organize_args(srcs: list[Path], pages: list[PageRef],
                  out: Path) -> list[str]:
    """Argumentos do qpdf (sem o executável) para montar `out` com
    `pages`, na ordem, e as rotações. Páginas seguidas do mesmo arquivo
    viram um trecho só ('a.pdf 1-3 b.pdf 2,1 a.pdf 5'). As rotações usam
    as posições no PDF novo."""
    if not pages:
        raise ValueError(_("Não sobrou nenhuma página."))
    args = ["--empty", "--pages"]
    i = 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1].src == pages[i].src:
            j += 1
        args += [str(srcs[pages[i].src]),
                 _compact([r.page for r in pages[i:j + 1]])]
        i = j + 1
    args.append("--")
    by_angle: dict[int, list[int]] = {}
    for pos, ref in enumerate(pages, 1):
        angle = ref.rotate % 360
        if angle:
            by_angle.setdefault(angle, []).append(pos)
    for angle in sorted(by_angle):
        args.append(f"--rotate=+{angle}:{_ranges(by_angle[angle])}")
    return args + [str(out)]


def pdf_organize_op(base: Op, pages: list[PageRef],
                    suffix: str = " Organized") -> Op:
    """Um PDF com as páginas na ordem e rotação da tela, de um ou de vários
    arquivos (Juntar: os caminhos vão na ordem dos índices de PageRef)."""
    if not pages:
        raise ValueError(_("Não sobrou nenhuma página."))

    def build(ctx: Ctx) -> list[Step]:
        return [T.cmd("qpdf") + organize_args(ctx.srcs, pages, ctx.out)]
    return derive(base, build, mode=ALL, ext="pdf", suffix=suffix)


def pdf_lock_state(path: Path) -> str:
    """'open' (sem criptografia), 'restricted' (só restrições de imprimir,
    copiar etc.: abre sem senha) ou 'password' (pede senha para abrir).
    `qpdf --requires-password` sai com 0 (pede), 2 (não criptografado) ou
    3 (criptografado sem senha de abertura)."""
    code = subprocess.run(T.cmd("qpdf") + ["--requires-password", str(path)],
                          capture_output=True).returncode
    return {0: "password", 3: "restricted"}.get(code, "open")


def needs_password(path: Path) -> bool:
    return pdf_lock_state(path) == "password"


def pdf_unlock_op(base: Op, password: str = "") -> Op:
    """Cópia sem criptografia (sem senha e sem restrições). A senha vai
    pelo stdin do qpdf: nunca na linha de comando nem no log."""
    def build(ctx: Ctx) -> list[Step]:
        def run(c: Ctx) -> None:
            proc = subprocess.run(
                T.cmd("qpdf") + ["--password-file=-", "--decrypt",
                                 str(c.src), str(c.out)],
                input=(password + "\n").encode("utf-8"),
                capture_output=True)
            # 3 = deu certo com avisos (PDF meio quebrado)
            if proc.returncode not in (0, 3):
                err = proc.stderr.decode(errors="replace")
                if "password" in err.lower():
                    raise RuntimeError(_("Senha errada.") if password else
                                       _("Este PDF pede senha."))
                raise RuntimeError(err.strip()[-400:] or "qpdf falhou")
        return [run]
    return derive(base, build, ext="pdf", suffix=" Unlocked")


def pdf_merge_op(base: Op) -> Op:
    """Juntar na ordem em que os caminhos chegarem (a da janela)."""
    def build(ctx: Ctx) -> list[Step]:
        return [T.cmd("qpdf") + ["--empty", "--pages", *map(str, ctx.srcs),
                                 "--", str(ctx.out)]]
    return derive(base, build, mode=ALL, ext="pdf", suffix=" Merged")


# --------------------------------------------------------------------------
# QR code
# --------------------------------------------------------------------------

# http(s)://, www. e mailto:; a pontuação no fim (". ) ,") não entra
_URL = re.compile(r"""(?:https?://|www\.|mailto:)[^\s<>"'`{}|\\^]+""", re.I)
_TRAIL = ".,;:!?)]}>'\""
QR_SIDE = 1024          # px do PNG (o qrencode trabalha em módulos)


def extract_links(text: str) -> list[str]:
    """Links na ordem em que aparecem, sem repetir."""
    out: list[str] = []
    for m in _URL.finditer(text):
        url = m.group(0)
        while url and url[-1] in _TRAIL:
            # parêntese que fecha um aberto dentro do link fica (Wikipedia)
            if url[-1] == ")" and url.count("(") >= url.count(")"):
                break
            url = url[:-1]
        if url.lower().startswith("www."):
            url = "https://" + url
        if len(url) > 10 and url not in out:
            out.append(url)
    return out


def links_in(path: Path) -> list[str]:
    """Links de um .url, .webloc, .txt, .md, .html..."""
    raw = path.read_bytes()[:2_000_000]
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", "replace")
    if F.full_ext(path) == "url":
        # [InternetShortcut] URL=...: só a linha URL (o resto é ícone, hash)
        for line in text.splitlines():
            if line.strip().upper().startswith("URL="):
                url = line.split("=", 1)[1].strip()
                return [url] if url else []
    return extract_links(text)


def looks_like_link(text: str) -> bool:
    text = text.strip()
    return bool(text) and "\n" not in text and \
        _URL.fullmatch(text) is not None


QR_LEVELS = "LMQH"      # correção de erros: ~7%, 15%, 25%, 30%


@dataclass
class QrStyle:
    """Aparência do QR (Gerar QR code > Personalizar). `size` é o lado
    aproximado em px; `margin`, a borda em módulos (4 é o padrão da norma);
    `level`, a correção de erros."""
    fg: str = "#000000"
    bg: str = "#FFFFFF"
    transparent: bool = False
    size: int = 600
    margin: int = 4
    level: str = "M"
    fmt: str = "png"

    KEYS = ("fg", "bg", "transparent", "size", "margin", "level", "fmt")

    @classmethod
    def from_settings(cls, cfg: dict) -> "QrStyle":
        style = cls()
        for key in cls.KEYS:
            value = cfg.get("qr_" + key)
            if value is not None and type(value) is type(getattr(style,
                                                                 key)):
                setattr(style, key, value)
        return style

    def to_settings(self) -> dict:
        return {"qr_" + k: getattr(self, k) for k in self.KEYS}

    def check(self) -> None:
        for color in (self.fg, self.bg):
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                raise ValueError(_("Cor inválida: {color}").format(
                    color=color))
        if self.level not in QR_LEVELS:
            raise ValueError(f"nível {self.level}")
        if self.fmt not in ("png", "svg"):
            raise ValueError(f"formato {self.fmt}")

    def low_contrast(self) -> bool:
        """Cores parecidas demais para um leitor de QR distinguir."""
        if self.transparent:
            return _luminance(self.fg) > 0.6     # QR claro sem fundo
        a, b = sorted((_luminance(self.fg), _luminance(self.bg)))
        return (b + 0.05) / (a + 0.05) < 3.0


def _luminance(color: str) -> float:
    rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
           for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _qr_modules(text: str, level: str) -> int:
    """Lado do QR em módulos (sem margem): um PNG de 1 px por módulo."""
    with tempfile.TemporaryDirectory(prefix="mexerica-qr-") as tmp:
        probe = Path(tmp) / "probe.png"
        proc = subprocess.run(
            T.cmd("qrencode") + ["-t", "PNG", "-l", level, "-m", "0",
                                 "-s", "1", "-o", str(probe)],
            input=text.encode("utf-8"), capture_output=True, check=False)
        if proc.returncode != 0 or not probe.exists():
            msg = proc.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(msg or "o qrencode falhou")
        return int.from_bytes(probe.read_bytes()[16:20], "big")  # IHDR


def qr_args(style: QrStyle, modules: int) -> list[str]:
    """Argumentos do qrencode para `style` num QR de `modules` módulos."""
    style.check()
    per = max(1, round(style.size / (modules + 2 * style.margin)))
    bg = style.bg.lstrip("#").upper() + ("00" if style.transparent else "")
    return ["-t", style.fmt.upper(), "-l", style.level,
            "-m", str(style.margin), "-s", str(per),
            f"--foreground={style.fg.lstrip('#').upper()}",
            f"--background={bg}"]


def qr_write(text: str, out: Path, fmt: str = "png",
             side: int = QR_SIDE, style: QrStyle | None = None) -> None:
    """Grava o QR em `out`. O conteúdo vai pelo stdin (nada de argv
    começando com '-'); a saída, num arquivo: no Windows o stdout do
    qrencode é texto e estragaria o PNG (LF vira CRLF)."""
    style = style or QrStyle(size=side, fmt=fmt)
    argv = T.cmd("qrencode") + qr_args(style, _qr_modules(text, style.level))
    argv += ["-o", str(out)]
    proc = subprocess.run(argv, input=text.encode("utf-8"),
                          capture_output=True, check=False)
    if proc.returncode != 0 or not out.exists():
        msg = proc.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(msg or "o qrencode falhou")


def qr_bytes(text: str, fmt: str = "png", side: int = QR_SIDE,
             style: QrStyle | None = None) -> bytes:
    """Para a prévia da janela."""
    style = style or QrStyle(size=side, fmt=fmt)
    with tempfile.TemporaryDirectory(prefix="mexerica-qr-") as tmp:
        out = Path(tmp) / f"qr.{style.fmt}"
        qr_write(text, out, style=style)
        return out.read_bytes()


def qr_op(base: Op, text: str, fmt: str = "png", suffix: str = " QR",
          style: QrStyle | None = None) -> Op:
    text = text.strip()
    if not text:
        raise ValueError(_("Cole um link ou um texto."))
    style = style or QrStyle(size=QR_SIDE, fmt=fmt)
    style.check()

    def build(ctx: Ctx) -> list[Step]:
        return [lambda c: qr_write(text, c.out, style=style)]
    return derive(base, build, ext=style.fmt, suffix=suffix)


def qr_name(text: str) -> str:
    """Nome sugerido para o QR de um link: 'github.com QR' (ou 'QR code'
    para um texto que não é link)."""
    m = re.match(r"(?:https?://)?(?:www\.)?([^/?#\s:]+)", text.strip(), re.I)
    return f"{m.group(1)} QR" if m and "." in m.group(1) else "QR code"


def qr_target(name: str, where: Path | None, fallback: Path) -> Path:
    """Caminho de referência para o QR chamado `name`: na pasta do item
    arrastado (a própria pasta, se for uma), ou em `fallback`. O runner
    tira dele a pasta e o nome; a extensão é de mentira (sem ela,
    'github.com' perderia o '.com')."""
    if where is None:
        folder = fallback
    else:
        folder = where if where.is_dir() else where.parent
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")[:120]
    return folder / f"{clean or 'QR code'}.url"


def qr_anchor(text: str, folder: Path) -> Path:
    """Caminho de referência para um QR sem arquivo de origem (colado):
    o nome vem do site ('github.com QR.png') e a pasta é `folder`."""
    m = re.match(r"(?:https?://)?(?:www\.)?([^/?#\s:]+)", text.strip(), re.I)
    name = m.group(1) if m and "." in m.group(1) else "QR code"
    name = re.sub(r'[<>:"/\\|?*]', "_", name)[:60]
    # a extensão é de mentira: sem ela, "github.com" perderia o ".com"
    return folder / f"{name}.url"


__all__ = ["ImageEdit", "image_edit_op", "image_size", "trim_op",
           "add_background_op",
           "keyframe_before",
           "video_size_op", "pdf_pages_op", "page_count", "duration",
           "parse_ranges", "every", "cuts_to_text", "pdf_split_op",
           "pdf_merge_op", "PageRef", "organize_args", "pdf_organize_op",
           "pdf_unlock_op", "needs_password", "pdf_lock_state", "extract_links", "links_in", "looks_like_link",
           "qr_write", "qr_bytes", "qr_op", "qr_anchor", "qr_name", "qr_target",
           "QrStyle", "qr_args", "QR_LEVELS",
           "derive", "ALL", "EACH"]
