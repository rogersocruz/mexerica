"""Documentos do Office: quem converte cada coisa (engine/office.py).

A escolha é testada sem rodar nada. As conversões de verdade rodam com o
que houver na máquina: Microsoft Office (Windows), pandoc + typst.
"""
import re
import subprocess
import zipfile

import pytest

from mexerica.engine import BY_ID, CONVERT, options_for, run
from mexerica.engine import office
from mexerica.engine import tools as T

TEXT, SHEET, SLIDES = office.TEXT, office.SHEET, office.SLIDES
MS, LO, PANDOC = office.MS, office.LO, office.PANDOC


@pytest.fixture
def only(monkeypatch):
    """Finge que só existem estes conversores: only(MS, PANDOC...)."""
    def setup(*backends, typst=True):
        monkeypatch.setattr(office, "_has", lambda b, _f: b in backends)
        real = T.has
        monkeypatch.setattr(T, "has", lambda *n: n == ("typst",) and typst
                            or n != ("typst",) and real(*n))
    return setup


def test_microsoft_office_comes_first(only):
    only(MS, LO, PANDOC)
    assert office.route(TEXT, "docx", "pdf") == MS
    assert office.route(SHEET, "csv", "xlsx") == MS
    assert office.route(SLIDES, "odp", "pptx") == MS
    assert office.route(TEXT, "pdf", "docx") == MS      # o Word abre PDF
    # Pages, Keynote e Numbers só o LibreOffice abre
    assert office.route(TEXT, "pages", "pdf") == LO
    assert office.route(SLIDES, "key", "pdf") == LO


def test_without_any_office_pandoc_keeps_the_content(only):
    only(PANDOC)
    assert office.route(TEXT, "docx", "pdf") == PANDOC
    assert office.route(TEXT, "rtf", "odt") == PANDOC
    assert office.route(SHEET, "xlsx", "pdf") == PANDOC
    assert office.route(SLIDES, "pptx", "pdf") == PANDOC
    assert office.route(SHEET, "ods", "pdf") is None    # o pandoc não lê ODS
    assert office.route(SHEET, "xlsx", "csv") is None   # nem escreve CSV
    only(PANDOC, typst=False)
    assert office.route(TEXT, "docx", "pdf") is None    # PDF precisa do typst
    assert office.route(TEXT, "docx", "odt") == PANDOC


def test_wheel_only_offers_what_someone_converts(only, tmp_path):
    only(PANDOC)
    ids = lambda name: [o.id for o in options_for([tmp_path / name], CONVERT)]
    assert "to-pdf-sheet" in ids("conta.xlsx")
    assert "to-csv-sheet" not in ids("conta.xlsx")
    assert ids("conta.ods") == []
    assert ids("livro.pages") == []
    only(LO)
    assert "to-pdf-doc" in ids("livro.pages")
    only()
    assert ids("carta.docx") == ["to-epub-doc"] or not T.has("pandoc")


def _text(path):
    if path.suffix == ".pdf":
        return subprocess.run(T.cmd("pdftotext") + [str(path), "-"],
                              capture_output=True, text=True).stdout
    # o Word parte palavras em vários <w:t>: junta os textos dos nós
    with zipfile.ZipFile(path) as z:
        xml = " ".join(z.read(n).decode("utf-8", "replace")
                       for n in z.namelist() if n.endswith(".xml"))
    return "".join(re.findall(r">([^<]*)<", xml))


@pytest.fixture
def docs(tmp_path):
    if not T.has("pandoc"):
        pytest.skip("sem pandoc para criar os documentos")
    md = tmp_path / "relatório.md"
    md.write_text("# Relatório\n\nAção e maçã.\n\n| Furo | NSPT |\n|---|---|\n"
                  "| SP-01 | 18 |\n", encoding="utf-8")
    for ext in ("docx", "pptx"):
        subprocess.run(T.cmd("pandoc") + [str(md), "-o",
                                          str(tmp_path / f"relatório.{ext}")],
                       check=True)
    (tmp_path / "orçamento.csv").write_text(
        "Item,Preço\nRelatório técnico,800\n", encoding="utf-8")
    return tmp_path


def _convert(op_id, src):
    res = run(BY_ID[op_id], [src])
    assert res.ok, res.errors
    return res.outputs[0]


@pytest.mark.skipif(not (T.has("pandoc") and T.has("typst")),
                    reason="sem pandoc + typst")
def test_pandoc_typst_without_office(only, docs):
    only(PANDOC)
    assert "Ação" in _text(_convert("to-pdf-doc", docs / "relatório.docx"))
    assert "Relatório técnico" in _text(_convert("to-pdf-sheet",
                                                 docs / "orçamento.csv"))
    assert "SP-01" in _text(_convert("to-pdf-slides", docs / "relatório.pptx"))


@pytest.mark.skipif(not office.ms_office(TEXT), reason="sem Microsoft Office")
def test_microsoft_office(docs, only):
    """Word, Excel e PowerPoint de verdade (uns segundos cada)."""
    only(MS)
    pdf = _convert("to-pdf-doc", docs / "relatório.docx")
    assert "Ação" in _text(pdf)
    assert "Ação" in _text(_convert("pdf-to-docx", pdf))         # PDF do Word
    xlsx = _convert("to-xlsx-sheet", docs / "orçamento.csv")       # acentos do CSV
    assert "Relatório técnico" in _text(xlsx)
    assert "SP-01" in _text(_convert("to-pdf-slides", docs / "relatório.pptx"))
