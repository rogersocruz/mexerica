"""Testes do motor rodando os programas reais (ffmpeg, ImageMagick...).

Cada teste é pulado se o programa que ele precisa não estiver instalado,
então a suíte roda em qualquer máquina.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mexerica.engine import BY_ID, CONVERT, TOOLS, ACTIONS, options_for, run
from mexerica.engine import tools as T
from mexerica.engine.formats import kind_of, full_ext, stem
from mexerica.engine.runner import unique_path


def need(*progs):
    missing = [p for p in progs if not T.has(p)]
    return pytest.mark.skipif(bool(missing), reason=f"ausente: {missing}")


def sh(*args):
    subprocess.run(args, check=True, capture_output=True)


@pytest.fixture
def d(tmp_path) -> Path:
    return tmp_path


@pytest.fixture
def png(d):
    if not T.has("magick"):
        pytest.skip("sem ImageMagick")
    p = d / "foto.png"
    sh(*T.cmd("magick"), "-size", "320x200", "gradient:orange-red", str(p))
    return p


@pytest.fixture
def mp4(d):
    if not T.has("ffmpeg"):
        pytest.skip("sem ffmpeg")
    p = d / "clip.mp4"
    sh(*T.cmd("ffmpeg"), "-loglevel", "error", "-f", "lavfi", "-i",
       "testsrc=d=2:s=320x240", "-f", "lavfi", "-i", "sine=d=2", "-shortest",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(p))
    return p


@pytest.fixture
def wav(d):
    if not T.has("ffmpeg"):
        pytest.skip("sem ffmpeg")
    p = d / "som.wav"
    sh(*T.cmd("ffmpeg"), "-loglevel", "error", "-f", "lavfi", "-i", "sine=d=2",
       str(p))
    return p


@pytest.fixture
def pdf(d):
    if not T.has("gs"):
        pytest.skip("sem ghostscript")
    p = d / "doc.pdf"
    sh(*T.cmd("gs"), "-q", "-sDEVICE=pdfwrite", "-o", str(p), "-c",
       "/Helvetica findfont 24 scalefont setfont 72 700 moveto (Ola) show "
       "showpage 72 700 moveto (Pagina 2) show showpage")
    return p


# ---------------------------------------------------------------- formatos

def test_kinds(d):
    assert kind_of(Path("a.JPG")) == "image"
    assert kind_of(Path("a.heic")) == "image"
    assert kind_of(Path("a.svg")) == "vector"
    assert kind_of(Path("b.mkv")) == "video"
    assert kind_of(Path("c.flac")) == "audio"
    assert kind_of(Path("x.tar.gz")) == "archive"
    assert kind_of(Path("x.docx")) == "doc-text"
    assert kind_of(Path("x.xlsx")) == "doc-sheet"
    assert kind_of(Path("x.epub")) == "ebook"
    assert kind_of(Path("x.srt")) == "subtitle"
    assert kind_of(d) == "folder"
    assert full_ext(Path("a.tar.gz")) == "tar.gz"
    assert stem(Path("backup.tar.gz")) == "backup"


def test_unique_path(d):
    p = d / "a.png"
    assert unique_path(p) == p
    p.touch()
    assert unique_path(p).name == "a (2).png"
    (d / "a (2).png").touch()
    assert unique_path(p).name == "a (3).png"
    t = d / "b.tar.gz"
    t.touch()
    assert unique_path(t).name == "b (2).tar.gz"


# ---------------------------------------------------------------- opções

def test_options_image_excludes_same_format(png):
    ids = [o.id for o in options_for([png], CONVERT)]
    assert "to-jpg" in ids and "to-png" not in ids


def test_options_video_audio_targets_are_trimmed(mp4):
    ids = [o.id for o in options_for([mp4], CONVERT)]
    assert "to-mp3-audio" in ids
    assert "to-flac-audio" not in ids  # não polui a roda de vídeo
    assert "to-mp4" not in ids


def test_options_multi_only_ops(png, d):
    other = d / "b.png"
    shutil.copy(png, other)
    one = [o.id for o in options_for([png], TOOLS)]
    two = [o.id for o in options_for([png, other], TOOLS)]
    assert "img-collage" not in one and "img-collage" in two
    assert "img-pdf" not in one


def test_mixed_kinds_intersection(png, mp4):
    assert options_for([png, mp4], CONVERT) == []
    ids = [o.id for o in options_for([png, mp4], TOOLS)]
    assert "img-compress" not in ids
    assert ("strip-meta" in ids) == T.has("exiftool")
    assert any(o.id == "act-copy-path"
               for o in options_for([png, mp4], ACTIONS))


# ---------------------------------------------------------------- execução

def _one(res):
    assert res.ok, res.errors
    assert len(res.outputs) == 1
    return res.outputs[0]


def test_png_to_jpg_never_overwrites(png):
    out1 = _one(run(BY_ID["to-jpg"], [png]))
    out2 = _one(run(BY_ID["to-jpg"], [png]))
    assert out1.name == "foto.jpg" and out2.name == "foto (2).jpg"
    assert out1.stat().st_size > 0
    # nenhum diretório temporário esquecido
    assert not list(png.parent.glob(".mexerica-*"))


@need("magick")
def test_image_tools(png):
    for op in ("img-compress", "img-half", "img-rotate", "img-gray",
               "to-webp", "img-1mb"):
        out = _one(run(BY_ID[op], [png]))
        assert out.exists() and out.stat().st_size > 0, op


@need("qrencode", "zbarimg")
def test_read_qr(d):
    qr = d / "qr.png"
    sh("qrencode", "-o", str(qr), "https://github.com/rogersocruz/mexerica")
    res = run(BY_ID["img-qr"], [qr])
    assert res.ok and res.texts == ["https://github.com/rogersocruz/mexerica"]


@need("ffmpeg")
def test_video_convert_and_tools(mp4):
    for op in ("to-webm", "to-mkv", "to-gif-video", "to-mp3-audio",
               "vid-mute", "vid-compress"):
        out = _one(run(BY_ID[op], [mp4]))
        assert out.stat().st_size > 0, op


@need("ffmpeg", "ffprobe")
def test_video_target_size_and_snapshot(mp4):
    out = _one(run(BY_ID["vid-10mb"], [mp4]))
    assert out.stat().st_size < 10 * 1024 * 1024
    snap = _one(run(BY_ID["vid-snap"], [mp4]))
    assert snap.suffix == ".jpg"


@need("ffmpeg")
def test_audio(wav, d):
    for op in ("to-mp3-audio", "to-flac-audio", "to-opus-audio",
               "aud-normalize", "aud-mono"):
        _one(run(BY_ID[op], [wav]))
    w2 = d / "som2.wav"
    shutil.copy(wav, w2)
    joined = _one(run(BY_ID["aud-join"], [wav, w2]))
    assert joined.name == "som Merged.wav"


@need("qpdf", "pdftoppm", "pdftotext", "gs")
def test_pdf(pdf, d):
    pages = _one(run(BY_ID["pdf-to-png"], [pdf]))
    assert pages.is_dir() and len(list(pages.iterdir())) == 2
    txt = _one(run(BY_ID["pdf-to-txt"], [pdf]))
    assert "Ola" in txt.read_text()
    split = _one(run(BY_ID["pdf-split"], [pdf]))
    assert sorted(p.name for p in split.iterdir()) == ["pagina-1.pdf",
                                                       "pagina-2.pdf"]
    merged = _one(run(BY_ID["pdf-merge"], [pdf, split / "pagina-1.pdf"]))
    assert merged.stat().st_size > 0
    _one(run(BY_ID["pdf-compress"], [pdf]))
    _one(run(BY_ID["pdf-rotate"], [pdf]))


@need("qpdf", "pdftoppm")
def test_single_page_dir_collapses_to_file(pdf, d):
    one = _one(run(BY_ID["pdf-split"], [pdf]))
    single = one / "pagina-1.pdf"
    png_out = _one(run(BY_ID["pdf-to-png"], [single]))
    assert png_out.is_file() and png_out.name == "pagina-1.png"


@need("exiftool", "qpdf")
def test_strip_and_show_meta(png, pdf):
    sh(*T.cmd("exiftool"), "-q", "-overwrite_original", "-Artist=Fulano", str(png))
    shown = run(BY_ID["show-meta"], [png])
    assert "Fulano" in shown.texts[0]
    clean = _one(run(BY_ID["strip-meta"], [png]))
    after = run(BY_ID["show-meta"], [clean])
    assert "Fulano" not in after.texts[0]
    _one(run(BY_ID["strip-meta"], [pdf]))


@need("bsdtar")
def test_archives(d):
    png = d / "foto.png"
    png.write_bytes(b"qualquer coisa")
    folder = d / "pasta"
    folder.mkdir()
    shutil.copy(png, folder / "a.png")
    z = _one(run(BY_ID["pack-zip"], [folder]))
    assert z.name == "pasta.zip"
    seven = _one(run(BY_ID["pack-7z"], [z]))           # zip -> 7z via @
    assert seven.name == "pasta.7z"
    ext = _one(run(BY_ID["extract"], [seven]))
    assert (ext / "pasta" / "a.png").exists()
    allzip = _one(run(BY_ID["act-zip-all"], [png, folder]))
    assert allzip.suffix == ".zip"


@need("soffice")
def test_office(d):
    doc = d / "carta.txt"
    doc.write_text("Olá, mundo\n")
    out = _one(run(BY_ID["to-pdf-text"], [doc]))
    assert out.read_bytes()[:4] == b"%PDF"


@need("pandoc")
def test_markdown(d):
    md = d / "nota.md"
    md.write_text("# Título\n\nTexto *ênfase*.\n")
    html = _one(run(BY_ID["to-html-text"], [md]))
    assert "<h1" in html.read_text()
    _one(run(BY_ID["to-docx-text"], [md]))


def test_failure_reports_and_cleans(d):
    bad = d / "quebrado.png"
    bad.write_bytes(b"isso nao e png")
    res = run(BY_ID["to-jpg"], [bad])
    assert not res.ok and res.errors[0][0] == bad
    assert not list(d.glob(".mexerica-*"))
    assert not (d / "quebrado.jpg").exists()


@need("magick")
def test_svg(d):
    svg = d / "logo.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" '
                   'height="40"><circle cx="20" cy="20" r="18" '
                   'fill="orange"/></svg>')
    ids = [o.id for o in options_for([svg], CONVERT)]
    assert "to-png" in ids
    for op in ("to-png", "to-jpg"):
        out = _one(run(BY_ID[op], [svg]))
        assert out.stat().st_size > 0


# ------------------------------------------------- janelas (engine/edits.py)

def test_editors_top_of_tools_wheel(png, mp4):
    ids = [o.id for o in options_for([png], TOOLS)]
    assert ids[:5] == ["img-edit", "img-crop", "img-addbg", "img-rmbg",
                       "img-size"]
    # presets antigos saem da roda, mas continuam na CLI
    assert "img-1mb" not in ids and "img-1mb" in BY_ID
    two = [o.id for o in options_for([png, png], TOOLS)]
    assert "img-edit" not in two and "img-size" in two
    assert [o.id for o in options_for([mp4], TOOLS)][:2] == \
        ["vid-trim", "vid-size"]


@need("magick")
def test_image_edit_crop_after_rotate(png):
    from mexerica.engine import edits as E
    # 320x200 girada vira 200x320; metade de cima = 200x160
    edit = E.ImageEdit(rotate=90, crop=(0, 0, 1, 0.5), saturation=-100)
    out = _one(run(E.image_edit_op(BY_ID["img-edit"], edit, " Edited"),
                   [png]))
    assert out.name == "foto Edited.png"
    assert E.image_size(out) == (200, 160)
    small = E.ImageEdit(max_side=100, ext="jpg", target_kb=20)
    out = _one(run(E.image_edit_op(BY_ID["img-size"], small, " Resized"),
                   [png]))
    assert out.suffix == ".jpg" and max(E.image_size(out)) == 100


@need("ffmpeg", "ffprobe")
def test_trim_exact_and_remove(mp4):
    from mexerica.engine import edits as E
    out = _one(run(E.trim_op(BY_ID["vid-trim"], 0.5, 1.5, fast=False),
                   [mp4]))
    assert abs(E.duration(out) - 1.0) < 0.15
    out = _one(run(E.trim_op(BY_ID["vid-trim"], 0.5, 1.5, fast=False,
                             remove=True), [mp4]))
    assert out.name == "clip Cut.mp4"
    assert abs(E.duration(out) - 1.0) < 0.2
    assert E.keyframe_before(mp4, 1.5) == 0.0     # GOP longo: só o quadro 0


@need("qpdf")
def test_pdf_pages(pdf):
    from mexerica.engine import edits as E
    assert E._ranges([1, 2, 3, 5, 7, 8]) == "1-3,5,7-8"
    out = _one(run(E.pdf_pages_op(BY_ID["pdf-pages"], "extract", [2], 2),
                   [pdf]))
    assert out.name == "doc Page 2.pdf" and E.page_count(out) == 1
    with pytest.raises(ValueError):
        E.pdf_pages_op(BY_ID["pdf-pages"], "delete", [1, 2], 2)


def test_suffixes_chain(png):
    """Sufixos em inglês, com espaço, encadeando como no Tangerine."""
    crop = run(BY_ID["img-compress"], [png])
    first = _one(crop)
    assert first.name == "foto Compressed.png"
    second = _one(run(BY_ID["img-rotate"], [first]))
    assert second.name == "foto Compressed Rotated.png"
    # conversão pura: só troca a extensão
    assert _one(run(BY_ID["to-jpg"], [second])).name == \
        "foto Compressed Rotated.jpg"


# ------------------------------------------------------------- Xournal++

@need("qpdf", "pdfinfo", "pdftotext")
def test_xopp_roundtrip(pdf, d):
    import gzip
    xo = _one(run(BY_ID["pdf-to-xopp"], [pdf]))
    assert xo.name == "doc.xopp"
    xml = gzip.decompress(xo.read_bytes()).decode()
    assert xml.count("<page ") == 2 and str(pdf) in xml
    # anota a página 2 e exporta: fundo do PDF por baixo + anotação
    xml = xml.replace('<background type="pdf" pageno="2ll"/>\n<layer/>',
                      '<background type="pdf" pageno="2ll"/>\n<layer>'
                      '<text font="Sans" size="14" x="72" y="300" '
                      'color="#000000ff">Nota manuscrita</text></layer>')
    xo.write_bytes(gzip.compress(xml.encode()))
    out = _one(run(BY_ID["xopp-to-pdf"], [xo]))
    text = subprocess.run(T.cmd("pdftotext") + [str(out), "-"],
                          capture_output=True, text=True).stdout
    assert "Ola" in text and "Pagina 2" in text and "Nota manuscrita" in text


def test_xopp_solid_pages(d):
    import gzip
    pytest.importorskip("cairo")
    from mexerica.engine import xopp
    x = d / "notas.xopp"
    x.write_bytes(gzip.compress(
        b'<xournal fileversion="4"><page width="300" height="200">'
        b'<background type="solid" color="#ffffffff" style="graph"/>'
        b'<layer><stroke tool="pen" color="#ff0000ff" width="2 1 3">'
        b'10 10 50 50 90 10</stroke></layer></page></xournal>'))
    out = d / "notas.pdf"
    xopp.render_annotations(xopp.read(x), out)
    assert out.read_bytes().startswith(b"%PDF")


@need("magick")
def test_crop_square_ratio(png):
    """Proporção 1:1 no recorte gera uma imagem quadrada."""
    from mexerica import cropmath as CM
    from mexerica.engine import edits as E
    w, h = E.image_size(png)                         # 320 x 200
    rect = CM.largest_centered(1.0, w, h)
    out = _one(run(E.image_edit_op(BY_ID["img-crop"],
                                   E.ImageEdit(crop=tuple(rect)),
                                   " Cropped"), [png]))
    assert out.name == "foto Cropped.png"
    ow, oh = E.image_size(out)
    assert ow == oh == 200
    # arrastar um canto mantendo 1:1 continua quadrado
    k = CM.norm_ratio(1.0, w, h)
    r = CM.resized("se", [0.1, 0.1, 0.3, 0.3 * w / h], 0.2, 0.05, k)
    assert abs(r[2] * w - r[3] * h) < 1e-6


@need("magick")
def test_add_background(png):
    from mexerica.engine import background as B
    from mexerica.engine import edits as E
    style = B.BgStyle(padding=40, corners=30, shadow=50, ratio=1.0)
    out = _one(run(E.add_background_op(BY_ID["img-addbg"], style), [png]))
    assert out.name == "foto With Background.png"
    assert E.image_size(out) == (400, 400)           # 320+80, quadrado


@need("magick")
def test_remove_background(d):
    if T.has("rembg"):
        pytest.skip("com rembg o resultado depende do modelo")
    src = d / "logo.png"
    sh(*T.cmd("magick"), "-size", "200x120", "xc:#f0f0f0", "-fill", "#ff5a1f",
       "-draw", "circle 100,60 100,20", str(src))
    out = _one(run(BY_ID["img-rmbg"], [src]))
    assert out.name == "logo Without Background.png"
    px = subprocess.run(T.cmd("magick") + [str(out), "-format",
                        "%[fx:p{2,2}.a] %[fx:p{100,60}.a]", "info:"],
                        capture_output=True, text=True).stdout.split()
    assert float(px[0]) == 0 and float(px[1]) == 1
