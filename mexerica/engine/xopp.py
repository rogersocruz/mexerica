"""Xournal++ (.xopp) <-> PDF sem precisar do Xournal++.

Um .xopp é XML compactado com gzip:

  <xournal fileversion="4">
    <page width="595.27" height="841.89">
      <background type="solid" color="#ffffffff" style="lined"/>
        (ou type="pdf" domain="absolute" filename="/x.pdf" pageno="1")
      <layer>
        <stroke tool="pen" color="#000000ff" width="1.41 1.2 ...">x y x y</stroke>
        <text font="Sans" size="12" x="10" y="20" color="#000000ff">oi</text>
        <image left="" top="" right="" bottom="">PNG em base64</image>
      </layer>
    </page>
  </xournal>

XOPP -> PDF: o cairo desenha fundo liso/pautado, traços, textos e imagens.
Páginas com PDF de fundo recebem a página original por baixo (qpdf
--underlay), então o fundo continua vetorial. Se o `xournalpp` estiver
instalado, ele é usado no lugar (fidelidade total).

PDF -> XOPP: um .xopp com uma página por página do PDF, usando o PDF como
fundo, pronto para anotar.
"""
from __future__ import annotations

import base64
import gzip
import io
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import quoteattr

import cairo

from . import tools as T

LINE_SPACING = 24.0      # pautado do Xournal++ (pt)
LINED_TOP = 80.0
LINED_MARGIN = 72.0
GRAPH_STEP = 14.17


def _rgba(value: str | None, default=(0, 0, 0, 1)) -> tuple[float, ...]:
    if not value or not value.startswith("#"):
        return default
    h = value[1:]
    if len(h) == 6:
        h += "ff"
    try:
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4, 6))
    except ValueError:
        return default


def read(path: Path) -> ET.Element:
    data = Path(path).read_bytes()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return ET.fromstring(data)


# --------------------------------------------------------------------------
# Desenho
# --------------------------------------------------------------------------

def _background(cr, bg: ET.Element | None, w: float, h: float) -> None:
    if bg is None or bg.get("type") != "solid":
        return                                  # pdf/imagem: fica por baixo
    cr.set_source_rgba(*_rgba(bg.get("color"), (1, 1, 1, 1)))
    cr.paint()
    style = bg.get("style", "plain")
    cr.set_line_width(0.5)
    if style in ("lined", "ruled"):
        cr.set_source_rgb(0.40, 0.69, 1.0)
        y = LINED_TOP
        while y < h:
            cr.move_to(0, y)
            cr.line_to(w, y)
            y += LINE_SPACING
        cr.stroke()
        if style == "lined":
            cr.set_source_rgb(1.0, 0.0, 0.0)
            cr.move_to(LINED_MARGIN, 0)
            cr.line_to(LINED_MARGIN, h)
            cr.stroke()
    elif style == "graph":
        cr.set_source_rgb(0.40, 0.69, 1.0)
        x = 0.0
        while x < w:
            cr.move_to(x, 0)
            cr.line_to(x, h)
            x += GRAPH_STEP
        y = 0.0
        while y < h:
            cr.move_to(0, y)
            cr.line_to(w, y)
            y += GRAPH_STEP
        cr.stroke()
    elif style == "dotted":
        cr.set_source_rgb(0.40, 0.69, 1.0)
        y = GRAPH_STEP
        while y < h:
            x = GRAPH_STEP
            while x < w:
                cr.arc(x, y, 0.7, 0, 6.2832)
                cr.fill()
                x += GRAPH_STEP
            y += GRAPH_STEP


def _stroke(cr, el: ET.Element) -> None:
    nums = [float(v) for v in (el.text or "").split()]
    pts = list(zip(nums[0::2], nums[1::2]))
    if not pts:
        return
    widths = [float(v) for v in el.get("width", "1").split()] or [1.0]
    tool = el.get("tool", "pen")
    r, g, b, a = _rgba(el.get("color"))
    if tool == "highlighter":
        a = min(a, 0.5)
    cr.set_source_rgba(r, g, b, a)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    if len(pts) == 1:
        cr.arc(pts[0][0], pts[0][1], widths[0] / 2, 0, 6.2832)
        cr.fill()
        return
    pressure = widths[1:]
    if not pressure:
        # largura constante: um caminho só (junções limpas, alfa uniforme)
        cr.set_line_width(widths[0])
        cr.move_to(*pts[0])
        for p in pts[1:]:
            cr.line_to(*p)
        cr.stroke()
        return
    # com pressão: um segmento por largura
    for i in range(len(pts) - 1):
        cr.set_line_width(pressure[min(i, len(pressure) - 1)])
        cr.move_to(*pts[i])
        cr.line_to(*pts[i + 1])
        cr.stroke()


def _text(cr, el: ET.Element) -> None:
    size = float(el.get("size", "12"))
    x, y = float(el.get("x", "0")), float(el.get("y", "0"))
    cr.set_source_rgba(*_rgba(el.get("color")))
    family = (el.get("font") or "Sans").split(",")[0]
    cr.select_font_face(family)
    cr.set_font_size(size)
    ascent = cr.font_extents()[0]
    for i, line in enumerate((el.text or "").split("\n")):
        cr.move_to(x, y + ascent + i * size * 1.2)
        cr.show_text(line)


def _image(cr, el: ET.Element) -> None:
    try:
        png = base64.b64decode(el.text or "")
        img = cairo.ImageSurface.create_from_png(io.BytesIO(png))
    except Exception:  # noqa: BLE001 - imagem quebrada: pula
        return
    left, top = float(el.get("left", 0)), float(el.get("top", 0))
    right, bottom = float(el.get("right", 0)), float(el.get("bottom", 0))
    if img.get_width() == 0 or img.get_height() == 0:
        return
    cr.save()
    cr.translate(left, top)
    cr.scale((right - left) / img.get_width(), (bottom - top) / img.get_height())
    cr.set_source_surface(img, 0, 0)
    cr.paint()
    cr.restore()


def _pages(root: ET.Element) -> list[ET.Element]:
    return root.findall("page")


def _pdf_backgrounds(root: ET.Element, src: Path) -> tuple[Path | None,
                                                           dict[int, int]]:
    """Arquivo do PDF de fundo e {página do xopp: página do PDF}."""
    pdf, mapping = None, {}
    for i, page in enumerate(_pages(root), start=1):
        bg = page.find("background")
        if bg is None or bg.get("type") != "pdf":
            continue
        if bg.get("filename"):
            name = Path(bg.get("filename"))
            pdf = name if name.is_absolute() else src.parent / name
        mapping[i] = int(bg.get("pageno", "1").rstrip("ln") or 1)
    return pdf, mapping


def render_annotations(root: ET.Element, out: Path) -> None:
    """Todas as páginas, com fundo liso desenhado e PDF de fundo omitido."""
    pages = _pages(root)
    if not pages:
        raise ValueError("arquivo .xopp sem páginas")
    first = pages[0]
    surf = cairo.PDFSurface(str(out), float(first.get("width", 595)),
                            float(first.get("height", 842)))
    cr = cairo.Context(surf)
    for page in pages:
        w, h = float(page.get("width", 595)), float(page.get("height", 842))
        surf.set_size(w, h)
        _background(cr, page.find("background"), w, h)
        for layer in page.findall("layer"):
            for el in layer:
                tag = el.tag
                if tag == "stroke":
                    _stroke(cr, el)
                elif tag == "text":
                    _text(cr, el)
                elif tag == "image":
                    _image(cr, el)
        cr.show_page()
    surf.finish()


def xopp_to_pdf(src: Path, out: Path, work: Path) -> None:
    if T.has("xournalpp"):
        subprocess.run(T.cmd("xournalpp") + [f"--create-pdf={out}", str(src)],
                       check=True, capture_output=True,
                       stdin=subprocess.DEVNULL)
        return
    root = read(src)
    annotations = work / "anotacoes.pdf"
    render_annotations(root, annotations)
    pdf, mapping = _pdf_backgrounds(root, src)
    if not mapping:
        annotations.replace(out)
        return
    if pdf is None or not pdf.exists():
        raise FileNotFoundError(
            f"PDF de fundo não encontrado: {pdf or '(sem nome no .xopp)'}")
    to = ",".join(str(i) for i in mapping)
    frm = ",".join(str(p) for p in mapping.values())
    subprocess.run(T.cmd("qpdf") + [str(annotations), "--underlay", str(pdf),
                                    f"--to={to}", f"--from={frm}", "--",
                                    str(out)],
                   check=True, capture_output=True, stdin=subprocess.DEVNULL)


# --------------------------------------------------------------------------
# PDF -> XOPP
# --------------------------------------------------------------------------

_PAGE_SIZE = re.compile(r"^Page\s+(\d+)\s+size:\s+([\d.]+)\s+x\s+([\d.]+)")
_PAGE_ROT = re.compile(r"^Page\s+(\d+)\s+rot:\s+(\d+)")


def pdf_page_sizes(pdf: Path) -> list[tuple[float, float]]:
    out = subprocess.run(T.cmd("pdfinfo") + ["-f", "1", "-l", "100000",
                                             str(pdf)],
                         capture_output=True, text=True, check=True).stdout
    sizes: dict[int, tuple[float, float]] = {}
    rots: dict[int, int] = {}
    for line in out.splitlines():
        if m := _PAGE_SIZE.match(line):
            sizes[int(m[1])] = (float(m[2]), float(m[3]))
        elif m := _PAGE_ROT.match(line):
            rots[int(m[1])] = int(m[2])
    result = []
    for n in sorted(sizes):
        w, h = sizes[n]
        result.append((h, w) if rots.get(n, 0) % 180 else (w, h))
    if not result:
        raise ValueError("não li as páginas do PDF")
    return result


def pdf_to_xopp(pdf: Path, out: Path) -> None:
    pdf = Path(pdf).resolve()
    parts = ['<?xml version="1.0" standalone="no"?>\n'
             '<xournal creator="Mexerica" fileversion="4">\n'
             "<title>Xournal++ document - see https://xournalpp.github.io/"
             "</title>\n"]
    for i, (w, h) in enumerate(pdf_page_sizes(pdf), start=1):
        if i == 1:
            bg = (f'<background type="pdf" domain="absolute" '
                  f'filename={quoteattr(str(pdf))} pageno="1ll"/>')
        else:
            bg = f'<background type="pdf" pageno="{i}ll"/>'
        parts.append(f'<page width="{w:.6f}" height="{h:.6f}">\n{bg}\n'
                     f"<layer/>\n</page>\n")
    parts.append("</xournal>\n")
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        fh.write("".join(parts))
