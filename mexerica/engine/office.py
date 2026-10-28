"""Documentos do Office (DOCX, XLSX, PPTX, ODT...) sem exigir o LibreOffice.

Quem converte, na ordem em que é procurado:
  1. Microsoft Office (Windows): Word, Excel e PowerPoint por automação
     COM, sem janela (office.ps1). Abre os formatos da Microsoft com
     fidelidade total, e o Word transforma PDF em DOCX editável.
  2. LibreOffice (`soffice --headless`), se estiver instalado. É o único
     que abre Pages, Keynote, Numbers e WordPerfect.
  3. Nenhum dos dois: o pandoc lê DOCX, ODT, RTF, XLSX, CSV e PPTX e
     escreve DOCX, ODT, RTF, TXT e PPTX; o PDF sai pelo typst. Fica o
     conteúdo (texto, tabelas, imagens), sem o layout de página, de slide
     ou de planilha.
Uma opção só aparece na roda se alguém aqui converter cada entrada para a
saída dela (`writes` para Op.available, `reads` para Op.accepts).
"""
from __future__ import annotations

import functools
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from .. import cache_dir
from . import formats as F
from . import tools as T

if TYPE_CHECKING:
    from .ops import Ctx, Step

log = logging.getLogger("mexerica")

TEXT, SHEET, SLIDES = "text", "sheet", "slides"
MS, LO, PANDOC = "msoffice", "soffice", "pandoc"
ORDER = (MS, LO, PANDOC)

SCRIPT = Path(__file__).with_name("office.ps1")
MS_TIMEOUT = 300          # s: um Office travado não segura o job para sempre
_MS_APP = {TEXT: ("word", "Word.Application"),
           SHEET: ("excel", "Excel.Application"),
           SLIDES: ("powerpoint", "PowerPoint.Application")}

_OUT = {TEXT: {"pdf", "docx", "odt", "rtf", "txt"},
        SHEET: {"pdf", "xlsx", "ods", "csv"},
        SLIDES: {"pdf", "pptx", "odp"}}
READS = {
    MS: {TEXT: {"doc", "docx", "odt", "rtf", "txt", "pdf"},
         SHEET: {"xls", "xlsx", "ods", "csv"},
         SLIDES: {"ppt", "pptx", "odp"}},
    LO: {TEXT: {"doc", "docx", "odt", "rtf", "txt", "pdf", "pages", "wpd"},
         SHEET: {"xls", "xlsx", "ods", "csv", "numbers"},
         SLIDES: {"ppt", "pptx", "odp", "key"}},
    PANDOC: {TEXT: {"docx", "odt", "rtf"},
             SHEET: {"xlsx", "csv"},
             SLIDES: {"pptx"}},
}
WRITES = {
    MS: _OUT,
    LO: _OUT,
    PANDOC: {TEXT: {"pdf", "docx", "odt", "rtf", "txt"},
             SHEET: {"pdf"},
             SLIDES: {"pdf", "pptx"}},
}

# --------------------------------------------------------------------------
# Quem converte
# --------------------------------------------------------------------------


@functools.lru_cache(maxsize=None)
def _powershell() -> str | None:
    found = T.which("powershell")
    if found:
        return found
    path = Path(os.environ.get("SystemRoot", r"C:\Windows"), "System32",
                "WindowsPowerShell", "v1.0", "powershell.exe")
    return str(path) if path.exists() else None


@functools.lru_cache(maxsize=None)
def ms_office(family: str) -> bool:
    """Word, Excel ou PowerPoint registrado para automação (só no Windows)."""
    if not T.WINDOWS or _powershell() is None:
        return False
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                             _MS_APP[family][1] + r"\CLSID")
    except OSError:
        return False
    winreg.CloseKey(key)
    return True


def _has(backend: str, family: str) -> bool:
    if backend == MS:
        return ms_office(family)
    if backend == LO:
        return T.has("soffice")
    return T.has("pandoc")


def route(family: str, src_ext: str, out_ext: str) -> str | None:
    """Quem converte `src_ext` em `out_ext` aqui (None: ninguém)."""
    for backend in ORDER:
        if src_ext not in READS[backend][family] or \
                out_ext not in WRITES[backend][family]:
            continue
        if backend == PANDOC and out_ext == "pdf" and not T.has("typst"):
            continue
        if _has(backend, family):
            return backend
    return None


def writes(family: str, ext: str) -> Callable[[], bool]:
    """Op.available: alguém aqui escreve `ext` a partir dessa família?"""
    inputs = set().union(*(READS[b][family] for b in ORDER))
    return lambda: any(route(family, s, ext) for s in inputs)


def reads(family: str, ext: str) -> Callable[[frozenset[str]], bool]:
    """Op.accepts: cada entrada tem quem a converta em `ext`?"""
    return lambda exts: all(route(family, x, ext) for x in exts)


def _text_pdf_plan(src_ext: str) -> str | None:
    """Markdown, HTML, TXT e EPUB para PDF: TXT direto pelo Office; os outros
    viram DOCX no pandoc e o Office faz o PDF (como sempre foi); sem
    Office, o pandoc faz o PDF pelo typst."""
    if src_ext == "txt" and route(TEXT, "txt", "pdf") in (MS, LO):
        return "office"
    if not T.has("pandoc"):
        return None
    if route(TEXT, "docx", "pdf") in (MS, LO):
        return "docx"
    return PANDOC if T.has("typst") else None


def text_pdf_available() -> bool:
    return any(_text_pdf_plan(x) for x in ("txt", "md"))


def text_pdf_reads(exts: frozenset[str]) -> bool:
    return all(_text_pdf_plan(x) for x in exts)


def any_office() -> bool:
    """Há quem faça PDF de um DOCX (para a janela de status e o doctor)."""
    return route(TEXT, "docx", "pdf") is not None

# --------------------------------------------------------------------------
# Passos
# --------------------------------------------------------------------------


def convert(ctx: Ctx, family: str, src: Path, ext: str) -> list[Step]:
    """Passos que convertem `src` em `ext`, gravando em ctx.out."""
    src_ext = F.full_ext(src)
    backend = route(family, src_ext, ext)
    if backend == MS:
        return [_ms(family, src, ext)]
    if backend == LO:
        return _soffice(ctx, src, ext)
    if backend == PANDOC:
        return [pandoc(src, ctx.out, ext)]
    raise RuntimeError(f"nenhum programa daqui converte .{src_ext} em .{ext}")


def text_to_pdf(ctx: Ctx) -> list[Step]:
    plan = _text_pdf_plan(F.full_ext(ctx.src))
    if plan == "office":
        return convert(ctx, TEXT, ctx.src, "pdf")
    if plan == "docx":
        mid = ctx.work / f"{F.stem(ctx.src)}.docx"
        return [pandoc(ctx.src, mid, "docx")] + convert(ctx, TEXT, mid, "pdf")
    return [pandoc(ctx.src, ctx.out, "pdf")]


def _ms(family: str, src: Path, ext: str) -> Step:
    app = _MS_APP[family][0]

    def run(c: Ctx) -> None:
        argv = [_powershell(), "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), app,
                str(Path(src).resolve()), str(Path(c.out).resolve()), ext]
        log.info("$ %s", " ".join(argv))
        try:
            proc = subprocess.run(argv, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",
                                  stdin=subprocess.DEVNULL,
                                  timeout=MS_TIMEOUT)
        except subprocess.TimeoutExpired as exc:
            _kill_spawned(exc.stdout)
            raise RuntimeError(f"o {app} não respondeu em {MS_TIMEOUT} s") \
                from None
        if proc.returncode != 0 or not Path(c.out).exists():
            raise RuntimeError(proc.stderr.strip()[-400:]
                               or f"o {app} não converteu")
    return run


def _kill_spawned(stdout) -> None:
    """Encerra o Office que o office.ps1 abriu e travou (ele avisa "pid N"
    logo ao abrir). O que a pessoa já tinha aberto não entra na lista."""
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", "replace")
    for line in (stdout or "").splitlines():
        if line.startswith("pid ") and line[4:].strip().isdigit():
            try:
                os.kill(int(line[4:]), 9)
                log.warning("Office travado encerrado (pid %s)", line[4:])
            except OSError:
                pass


_LO_FILTERS = {"txt": "Text (encoded):UTF8",
               "csv": "Text - txt - csv (StarCalc):44,34,76"}


def _soffice(ctx: Ctx, src: Path, ext: str) -> list[Step]:
    """LibreOffice headless com perfil próprio (não briga com uma janela do
    LibreOffice aberta) e saída num diretório temporário."""
    filt, infilter = _LO_FILTERS.get(ext), None
    if F.full_ext(src) == "pdf":
        filt, infilter = "MS Word 2007 XML", "writer_pdf_import"
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


_READERS = {"md": "markdown", "markdown": "markdown", "txt": "markdown",
            "html": "html", "htm": "html", "epub": "epub", "docx": "docx",
            "odt": "odt", "rtf": "rtf", "xlsx": "xlsx", "csv": "csv",
            "pptx": "pptx"}
_WRITERS = {"txt": "plain", "md": "gfm", "html": "html", "epub": "epub",
            "docx": "docx", "odt": "odt", "rtf": "rtf", "pptx": "pptx",
            "pdf": "typst"}


def pandoc(src: Path, out: Path, ext: str) -> list[str]:
    argv = T.cmd("pandoc") + ["-f", _READERS.get(F.full_ext(src), "markdown"),
                              "-t", _WRITERS[ext], "-o", str(out), str(src)]
    if ext in ("html", "epub", "rtf"):
        argv.insert(-1, "--standalone")              # RTF sem isso sai pela metade
    if ext in ("html", "epub"):
        argv.insert(-1, f"--metadata=title:{F.stem(src)}")
    if ext == "pdf":
        argv.insert(-1, f"--pdf-engine={T.which('typst')}")
    return argv
