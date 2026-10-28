"""Fontes pelo fontTools: as fontes de teste são montadas aqui mesmo."""
from pathlib import Path

import pytest

from mexerica.engine import BY_ID, CONVERT, options_for, run
from mexerica.engine import fonts as FT

if not FT.available():
    pytest.skip("sem fontTools", allow_module_level=True)

from fontTools.fontBuilder import FontBuilder  # noqa: E402
from fontTools.pens.t2CharStringPen import T2CharStringPen  # noqa: E402
from fontTools.pens.ttGlyphPen import TTGlyphPen  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

GLYPHS = [".notdef", "A"]


def build(path: Path, cff: bool) -> Path:
    """Uma fonte de dois glifos: TrueType (quadrado) ou CFF (uma curva)."""
    fb = FontBuilder(1000, isTTF=not cff)
    fb.setupGlyphOrder(GLYPHS)
    fb.setupCharacterMap({ord("A"): "A"})
    if cff:
        strings = {}
        for name in GLYPHS:
            pen = T2CharStringPen(600, None)
            pen.moveTo((100, 0))
            pen.curveTo((100, 500), (500, 500), (500, 0))
            pen.closePath()
            strings[name] = pen.getCharString()
        fb.setupCFF("Teste-Regular", {"FullName": "Teste"}, strings, {})
    else:
        glyphs = {}
        for name in GLYPHS:
            pen = TTGlyphPen(None)
            pen.moveTo((100, 0))
            pen.lineTo((100, 700))
            pen.lineTo((500, 700))
            pen.lineTo((500, 0))
            pen.closePath()
            glyphs[name] = pen.glyph()
        fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (600, 100) for n in GLYPHS})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Teste", "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=800, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.save(str(path))
    return path


def contours(font: TTFont, name: str = "A") -> int:
    from fontTools.pens.recordingPen import RecordingPen
    pen = RecordingPen()
    font.getGlyphSet()[name].draw(pen)
    return sum(1 for op, _ in pen.value if op == "closePath")


def test_wheel_offers_by_container(tmp_path):
    def ids(name):
        return [op.id for op in options_for([tmp_path / name], CONVERT)]
    expected = ["to-woff-font"] + (["to-woff2-font"] if FT.woff2_ok() else [])
    assert ids("a.ttf") == expected
    assert "to-ttf-font" in ids("a.otf") and "to-otf-font" not in ids("a.otf")
    assert {"to-ttf-font", "to-otf-font"} <= set(ids("a.woff"))


@pytest.mark.skipif(not FT.woff2_ok(), reason="sem brotli")
def test_ttf_to_woff2_and_back(tmp_path):
    ttf = build(tmp_path / "fonte.ttf", cff=False)
    res = run(BY_ID["to-woff2-font"], [ttf])
    assert res.ok and res.outputs == [tmp_path / "fonte.woff2"]
    woff2 = TTFont(str(res.outputs[0]))
    assert woff2.flavor == "woff2" and woff2.getGlyphOrder() == GLYPHS
    back = run(BY_ID["to-ttf-font"], res.outputs).outputs[0]
    assert back.name == "fonte (2).ttf"                    # não sobrescreve
    font = TTFont(str(back))
    assert font.flavor is None and "glyf" in font and contours(font) == 1


def test_otf_to_ttf_converts_the_curves(tmp_path):
    otf = build(tmp_path / "fonte.otf", cff=True)
    out = run(BY_ID["to-ttf-font"], [otf]).outputs[0]
    font = TTFont(str(out))
    assert "glyf" in font and "CFF " not in font
    assert font.sfntVersion == "\x00\x01\x00\x00"
    assert font.getGlyphOrder() == GLYPHS and contours(font) == 1
    assert font["glyf"]["A"].numberOfContours == 1


def test_woff_unwraps_to_otf_only_with_cff_inside(tmp_path):
    otf_woff = run(BY_ID["to-woff-font"],
                   [build(tmp_path / "cff.otf", cff=True)]).outputs[0]
    out = run(BY_ID["to-otf-font"], [otf_woff]).outputs[0]
    assert "CFF " in TTFont(str(out)) and out.suffix == ".otf"
    ttf_woff = run(BY_ID["to-woff-font"],
                   [build(tmp_path / "tt.ttf", cff=False)]).outputs[0]
    res = run(BY_ID["to-otf-font"], [ttf_woff])
    assert not res.outputs and "escolha TTF" in res.errors[0][1]
