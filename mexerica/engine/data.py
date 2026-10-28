"""Dados estruturados: JSON, JSON Lines, YAML, TOML, XML e CSV, uns nos
outros.

Puro Python: o YAML usa o PyYAML (opcional) e o resto vem da stdlib (o
TOML é lido pelo tomllib e escrito aqui). Tudo passa por uma árvore comum
de dict/list/escalares:

  XML   <a x="1"><b>oi</b><b>tchau</b></a>  ->  {"a": {"@x": "1",
        "b": ["oi", "tchau"]}}  (atributos com @, texto misto em #text)
  CSV   uma lista de objetos; o que for aninhado vira "pai.filho"
  TOML  não tem nulo nem lista solta: nulos somem e uma lista vira
        {"items": [...]}
"""
from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import io
import json
import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

from . import formats as F

WRITES = ("json", "yaml", "toml", "xml", "csv")


def has_yaml() -> bool:
    return importlib.util.find_spec("yaml") is not None


def reads(ext: str) -> bool:
    if ext in ("yaml", "yml"):
        return has_yaml()
    return ext in ("json", "jsonl", "ndjson", "toml", "xml", "csv")


def writes(fmt: str) -> bool:
    return has_yaml() if fmt == "yaml" else fmt in WRITES


# --------------------------------------------------------------------------
# Leitura
# --------------------------------------------------------------------------

def load(path: Path):
    ext = F.full_ext(path)
    if ext == "toml":
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    text = _read_text(path)
    if ext == "json":
        return json.loads(text)
    if ext in ("jsonl", "ndjson"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if ext in ("yaml", "yml"):
        import yaml
        docs = [d for d in yaml.safe_load_all(text) if d is not None]
        return docs[0] if len(docs) == 1 else docs
    if ext == "xml":
        root = ET.fromstring(text)
        return {_tag(root.tag): _from_xml(root)}
    if ext == "csv":
        return _from_csv(text)
    raise ValueError(f"não sei ler .{ext}")


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def _tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]          # sem o namespace {uri}


def _from_xml(el: ET.Element):
    node: dict = {f"@{_tag(k)}": v for k, v in el.attrib.items()}
    for child in el:
        key, value = _tag(child.tag), _from_xml(child)
        if key not in node:
            node[key] = value
        elif isinstance(node[key], list):
            node[key].append(value)
        else:
            node[key] = [node[key], value]
    text = (el.text or "").strip()
    if text and not node:
        return text
    if text:
        node["#text"] = text
    return node or None


def _from_csv(text: str) -> list[dict]:
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    return [dict(row) for row in csv.DictReader(io.StringIO(text), dialect=dialect)]


# --------------------------------------------------------------------------
# Escrita
# --------------------------------------------------------------------------

def dump(obj, path: Path, fmt: str) -> None:
    obj = _plain(obj)
    if fmt == "json":
        text = json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n"
    elif fmt == "yaml":
        import yaml
        text = yaml.safe_dump(obj, allow_unicode=True, sort_keys=False,
                              default_flow_style=False)
    elif fmt == "toml":
        text = to_toml(obj)
    elif fmt == "xml":
        text = to_xml(obj)
    elif fmt == "csv":
        # com BOM: o Excel abre os acentos certos
        path.write_text(to_csv(obj), encoding="utf-8-sig", newline="")
        return
    else:
        raise ValueError(f"não sei escrever {fmt}")
    path.write_text(text, encoding="utf-8")


def convert(src: Path, out: Path, fmt: str) -> None:
    dump(load(src), out, fmt)


def _plain(obj):
    """Chaves sempre texto, tuplas e conjuntos viram listas (o YAML aceita
    chave numérica e conjuntos; os outros formatos não)."""
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [_plain(v) for v in obj]
    return obj


def _scalar_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dt.date, dt.time)):
        return value.isoformat()
    return str(value)


# -- TOML --------------------------------------------------------------------

_BARE = re.compile(r"^[A-Za-z0-9_-]+$")


def to_toml(obj) -> str:
    if not isinstance(obj, dict):
        obj = {"items": obj}
    lines: list[str] = []
    _toml_table(obj, [], lines, header=None)
    return "\n".join(lines).lstrip("\n") + "\n"


def _key(k: str) -> str:
    return k if _BARE.match(k) else json.dumps(k, ensure_ascii=False)


def _is_table_array(v) -> bool:
    return isinstance(v, list) and bool(v) and all(isinstance(i, dict) for i in v)


def _toml_table(table: dict, path: list[str], lines: list[str],
                header: str | None) -> None:
    if header is not None:
        lines += ["", header]
    for k, v in table.items():
        if v is None or isinstance(v, dict) or _is_table_array(v):
            continue
        lines.append(f"{_key(k)} = {_toml_value(v)}")
    for k, v in table.items():
        sub = path + [_key(k)]
        if isinstance(v, dict):
            _toml_table(v, sub, lines, f"[{'.'.join(sub)}]")
        elif _is_table_array(v):
            for item in v:
                _toml_table(item, sub, lines, f"[[{'.'.join(sub)}]]")


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v:
            return "nan"
        if v in (float("inf"), float("-inf")):
            return "inf" if v > 0 else "-inf"
        return repr(v)
    if isinstance(v, (dt.datetime, dt.date, dt.time)):
        return v.isoformat()
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(i) for i in v if i is not None) + "]"
    if isinstance(v, dict):
        inner = ", ".join(f"{_key(k)} = {_toml_value(x)}"
                          for k, x in v.items() if x is not None)
        return "{" + inner + "}"
    return json.dumps(str(v), ensure_ascii=False)


# -- XML ---------------------------------------------------------------------

_XML_BAD = re.compile(r"[^\w.\-]")


def _xml_name(key: str) -> str:
    name = _XML_BAD.sub("_", key) or "item"
    if not (name[0].isalpha() or name[0] == "_") or name.lower().startswith("xml"):
        name = "_" + name
    return name


def to_xml(obj) -> str:
    if isinstance(obj, dict) and len(obj) == 1:
        (key, value), = obj.items()
        if not key.startswith(("@", "#")) and not isinstance(value, list):
            tag, obj = key, value
        else:
            tag = "root"
    else:
        tag = "root"
    if isinstance(obj, list):
        root = ET.Element(_xml_name(tag))
        for item in obj:
            _xml_build(root, "item", item)
    else:
        holder = ET.Element("x")
        _xml_build(holder, tag, obj)
        root = holder[0]
    ET.indent(root)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            + ET.tostring(root, encoding="unicode") + "\n")


def _xml_build(parent: ET.Element, key: str, value) -> None:
    if isinstance(value, list):
        for item in value:                       # lista = elemento repetido
            _xml_build(parent, key, item)
        return
    el = ET.SubElement(parent, _xml_name(key))
    if isinstance(value, dict):
        for k, v in value.items():
            if k.startswith("@"):
                el.set(_xml_name(k[1:]), _scalar_text(v))
            elif k == "#text":
                el.text = _scalar_text(v)
            else:
                _xml_build(el, k, v)
    else:
        el.text = _scalar_text(value)


# -- CSV ---------------------------------------------------------------------

def to_csv(obj) -> str:
    rows = _rows(obj)
    if rows is None:
        raise RuntimeError("Para CSV, o arquivo precisa ser uma lista de "
                           "registros (ou ter uma lista assim dentro)")
    flat = [_flatten(r) if isinstance(r, dict) else {"value": r} for r in rows]
    header: list[str] = []
    for row in flat:
        header += [k for k in row if k not in header]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=header, lineterminator="\r\n")
    writer.writeheader()
    for row in flat:
        writer.writerow(row)
    return out.getvalue()


def _rows(obj):
    """A lista de registros: o próprio arquivo, ou a única lista de objetos
    dentro dele ({"data": [...]}, como muita API devolve)."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        lists = [v for v in obj.values() if isinstance(v, list)]
        if len(lists) == 1:
            return lists[0]
        if all(not isinstance(v, (dict, list)) for v in obj.values()):
            return [obj]                          # um registro só
        if len(obj) == 1:
            return _rows(next(iter(obj.values())))
    return None


def _flatten(row: dict, prefix: str = "") -> dict:
    out: dict = {}
    for k, v in row.items():
        name = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, name + "."))
        elif isinstance(v, list):
            out[name] = json.dumps(v, ensure_ascii=False, default=str)
        else:
            out[name] = _scalar_text(v)
    return out
