"""Conversões recentes, para a página Início: o que entrou, o que saiu e
quando.

Um JSON no cache (Linux: ~/.cache/mexerica/history.json; Windows:
%LOCALAPPDATA%\\Mexerica\\cache\\history.json), com as últimas LIMIT, a
mais nova primeiro. Só caminhos e o nome da operação; os arquivos não são
copiados. Puro Python, sem GTK.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
from pathlib import Path

from . import cache_dir

log = logging.getLogger("mexerica")

LIMIT = 40


def path() -> Path:
    return cache_dir() / "history.json"


def load() -> list[dict]:
    """As entradas, a mais nova primeiro (arquivo ruim = histórico vazio)."""
    try:
        data = json.loads(path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        log.warning("histórico ilegível (%s); começando outro", exc)
        return []
    return [e for e in data if isinstance(e, dict) and e.get("outputs")] \
        if isinstance(data, list) else []


def add(op_id: str, label: str, inputs: list[Path], outputs: list[Path],
        when: dt.datetime | None = None) -> None:
    if not outputs:
        return
    entry = {"time": (when or dt.datetime.now()).isoformat(timespec="seconds"),
             "op": op_id, "label": label,
             "inputs": [str(p) for p in inputs],
             "outputs": [str(p) for p in outputs]}
    _save([entry, *load()][:LIMIT])


def clear() -> None:
    _save([])


def _save(entries: list[dict]) -> None:
    target = path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, indent=1, ensure_ascii=False),
                       encoding="utf-8")
        os.replace(tmp, target)
    except OSError as exc:            # sem histórico, o resto segue
        log.warning("não gravou o histórico: %s", exc)


def when_text(entry: dict, now: dt.datetime | None = None) -> str:
    """"agora", "há 5 min", "há 3 h", "ontem" ou a data."""
    try:
        then = dt.datetime.fromisoformat(entry["time"])
    except (KeyError, ValueError):
        return ""
    now = now or dt.datetime.now()
    secs = (now - then).total_seconds()
    if secs < 60:
        return "agora"
    if secs < 3600:
        return f"há {int(secs // 60)} min"
    if then.date() == now.date():
        return f"há {int(secs // 3600)} h"
    if (now.date() - then.date()).days == 1:
        return "ontem"
    return then.strftime("%d/%m/%Y")
