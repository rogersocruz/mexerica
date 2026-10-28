"""Dados estruturados (JSON, YAML, TOML, XML, CSV): puro Python."""
import csv
import io
import json
import tomllib
from pathlib import Path

import pytest

from mexerica.engine import BY_ID, CONVERT, options_for, run
from mexerica.engine import data as D

SAMPLE = {
    "nome": "Mexerica",
    "versão": 1.5,
    "ativo": True,
    "tags": ["arquivo", "roda"],
    "autor": {"nome": "Roger", "site": None},
    "itens": [{"id": 1, "fmt": "jpg"}, {"id": 2, "fmt": "png"}],
}

needs_yaml = pytest.mark.skipif(not D.has_yaml(), reason="sem PyYAML")


def write(path: Path, obj, fmt: str) -> Path:
    D.dump(obj, path, fmt)
    return path


@pytest.mark.parametrize("fmt", ["json", pytest.param("yaml", marks=needs_yaml)])
def test_lossless_roundtrip(tmp_path, fmt):
    p = write(tmp_path / f"a.{fmt}", SAMPLE, fmt)
    assert D.load(p) == SAMPLE


def test_toml_drops_nulls_and_keeps_the_rest(tmp_path):
    p = write(tmp_path / "a.toml", SAMPLE, "toml")
    back = tomllib.loads(p.read_text(encoding="utf-8"))   # TOML válido
    expected = dict(SAMPLE, autor={"nome": "Roger"})       # TOML não tem nulo
    assert back == expected


def test_toml_wraps_a_list_and_quotes_odd_keys(tmp_path):
    p = write(tmp_path / "a.toml", [{"a b": 1}, {"c": [1, 2]}], "toml")
    assert tomllib.loads(p.read_text(encoding="utf-8")) == {
        "items": [{"a b": 1}, {"c": [1, 2]}]}


def test_xml_attributes_repeated_elements_and_text(tmp_path):
    src = tmp_path / "a.xml"
    src.write_text('<?xml version="1.0"?>\n<lista dono="eu">'
                   '<item id="1">um</item><item id="2">dois</item>'
                   '<vazio/></lista>', encoding="utf-8")
    data = D.load(src)
    assert data == {"lista": {"@dono": "eu", "vazio": None, "item": [
        {"@id": "1", "#text": "um"}, {"@id": "2", "#text": "dois"}]}}
    again = write(tmp_path / "b.xml", data, "xml")
    assert D.load(again) == data                            # ida e volta


def test_json_to_xml_has_one_root_and_valid_names(tmp_path):
    p = write(tmp_path / "a.xml", {"1 chave": "x", "ok": [1, 2]}, "xml")
    text = p.read_text(encoding="utf-8")
    assert text.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<root>')
    assert "<_1_chave>x</_1_chave>" in text
    assert text.count("<ok>") == 2                          # lista = repetido


def test_csv_reads_semicolons_and_flattens_on_write(tmp_path):
    src = tmp_path / "a.csv"
    src.write_text("nome;idade\nAna;30\nBia;25\n", encoding="utf-8")
    assert D.load(src) == [{"nome": "Ana", "idade": "30"},
                           {"nome": "Bia", "idade": "25"}]
    p = write(tmp_path / "b.csv", {"dados": [{"a": 1, "b": {"c": 2}},
                                             {"a": 3, "d": [4]}]}, "csv")
    raw = p.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")                  # BOM: Excel
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    assert rows == [{"a": "1", "b.c": "2", "d": ""},
                    {"a": "3", "b.c": "", "d": "[4]"}]


def test_csv_needs_records(tmp_path):
    with pytest.raises(RuntimeError, match="lista de registros"):
        D.dump({"a": {"b": 1}, "c": {"d": 2}}, tmp_path / "x.csv", "csv")


def test_json_lines_become_a_list(tmp_path):
    src = tmp_path / "log.jsonl"
    src.write_text('{"a": 1}\n\n{"a": 2}\n', encoding="utf-8")
    assert D.load(src) == [{"a": 1}, {"a": 2}]


def test_wheel_offers_data_targets(tmp_path):
    ids = {op.id for op in options_for([tmp_path / "a.json"], CONVERT)}
    assert {"to-toml-data", "to-xml-data", "to-csv-data"} <= ids
    assert "to-json-data" not in ids                        # já é JSON
    assert ("to-yaml-data" in ids) == D.has_yaml()
    # CSV: planilha e dado; XLSX não é dado
    assert "to-json-data" in {op.id for op in
                              options_for([tmp_path / "a.csv"], CONVERT)}
    assert "to-json-data" not in {op.id for op in
                                  options_for([tmp_path / "a.xlsx"], CONVERT)}


def test_run_writes_beside_the_original(tmp_path):
    src = tmp_path / "config.toml"
    src.write_text('titulo = "oi"\n[banco]\nporta = 5432\n', encoding="utf-8")
    res = run(BY_ID["to-json-data"], [src])
    assert res.ok and res.outputs == [tmp_path / "config.json"]
    assert json.loads(res.outputs[0].read_text(encoding="utf-8")) == {
        "titulo": "oi", "banco": {"porta": 5432}}
