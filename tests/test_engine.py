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
    sh("ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
       "testsrc=d=2:s=320x240", "-f", "lavfi", "-i", "sine=d=2", "-shortest",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(p))
    return p


@pytest.fixture
def wav(d):
    if not T.has("ffmpeg"):
        pytest.skip("sem ffmpeg")
    p = d / "som.wav"
    sh("ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=d=2", str(p))
    return p


@pytest.fixture
def pdf(d):
    if not T.has("gs"):
        pytest.skip("sem ghostscript")
    p = d / "doc.pdf"
    sh("gs", "-q", "-sDEVICE=pdfwrite", "-o", str(p), "-c",
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
    assert "strip-meta" in ids and "img-compress" not in ids
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
    assert joined.name == "som-juntado.wav"


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
    sh("exiftool", "-q", "-overwrite_original", "-Artist=Fulano", str(png))
    shown = run(BY_ID["show-meta"], [png])
    assert "Fulano" in shown.texts[0]
    clean = _one(run(BY_ID["strip-meta"], [png]))
    after = run(BY_ID["show-meta"], [clean])
    assert "Fulano" not in after.texts[0]
    _one(run(BY_ID["strip-meta"], [pdf]))


@need("bsdtar")
def test_archives(png, d):
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
