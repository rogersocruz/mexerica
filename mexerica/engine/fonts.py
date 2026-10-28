"""Fontes: TTF, OTF, WOFF e WOFF2, pelo fontTools (opcional; o WOFF2 também
precisa do brotli).

WOFF e WOFF2 são só embalagens: por dentro há uma fonte TrueType (contornos
"glyf") ou OpenType/CFF. Trocar a embalagem não muda nada no desenho. Já
OTF -> TTF converte as curvas cúbicas em quadráticas (cu2qu, erro de até
1 unidade); o caminho contrário não existe aqui.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

CU2QU_MAX_ERR = 1.0      # unidades da fonte


def available() -> bool:
    return importlib.util.find_spec("fontTools") is not None


def woff2_ok() -> bool:
    return available() and importlib.util.find_spec("brotli") is not None


def convert(src: Path, out: Path, fmt: str) -> None:
    from fontTools.ttLib import TTFont
    font = TTFont(str(src))
    if fmt == "ttf" and "CFF " in font:
        cff_to_glyf(font)
    elif fmt == "otf" and "glyf" in font:
        raise RuntimeError("Esta fonte tem contornos TrueType: escolha TTF")
    font.flavor = fmt if fmt in ("woff", "woff2") else None
    font.save(str(out))


def cff_to_glyf(font) -> None:
    """Troca os contornos CFF (cúbicos) por glyf (quadráticos), no lugar."""
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.ttLib import newTable

    order = font.getGlyphOrder()
    glyph_set = font.getGlyphSet()
    glyphs = {}
    for name in order:
        pen = TTGlyphPen(glyph_set)
        # o CFF gira os contornos ao contrário do TrueType
        glyph_set[name].draw(Cu2QuPen(pen, CU2QU_MAX_ERR,
                                      reverse_direction=True))
        glyphs[name] = pen.glyph()

    font["loca"] = newTable("loca")
    glyf = font["glyf"] = newTable("glyf")
    glyf.glyphOrder = order
    glyf.glyphs = glyphs
    del font["CFF "]
    if "VORG" in font:
        del font["VORG"]

    maxp = font["maxp"]
    maxp.tableVersion = 0x00010000
    for field in ("maxZones", "maxTwilightPoints", "maxStorage",
                  "maxFunctionDefs", "maxInstructionDefs",
                  "maxStackElements", "maxSizeOfInstructions",
                  "maxComponentElements"):
        setattr(maxp, field, 1 if field == "maxZones" else 0)
    head = font["head"]
    head.indexToLocFormat = 0
    head.glyphDataFormat = 0
    post = font["post"]
    post.formatType = 2.0
    post.extraNames = []
    post.mapping = {}
    post.glyphOrder = order
    font.sfntVersion = "\x00\x01\x00\x00"


__all__ = ["available", "woff2_ok", "convert", "cff_to_glyf"]
