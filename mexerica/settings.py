"""Configurações do usuário: estilo, itens das rodas e comportamento.

Ficam num JSON (Linux: ~/.config/mexerica/settings.json; Windows:
%APPDATA%\\Mexerica\\settings.json). A janela de Configurações grava e o
serviço aplica na hora; o motor e a CLI leem o mesmo arquivo, e a extensão
do GNOME lê o "dim". Puro Python, sem GTK.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger("mexerica")

DEFAULTS: dict = {
    "style": "mexerica",       # paleta (theme.STYLES)
    "wheel_size": "medium",    # small | medium | large
    "window_opacity": 92,      # % das janelas de vidro
    "dim": 28,                 # % que a tela atrás da roda escurece
    "animations": True,
    "hidden": [],              # operações que o usuário tirou da roda
    "extra": [],               # presets fora da roda que o usuário pôs
    "output": "beside",        # beside (ao lado do original) | folder
    "output_folder": "",
    "jpeg_quality": 92,
    "notify_start": True,      # notificação quando um trabalho começa
}
WHEEL_SCALE = {"small": 0.85, "medium": 1.0, "large": 1.2}

_cache: dict | None = None


def path() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData/Roaming")
        return Path(base) / "Mexerica" / "settings.json"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "mexerica" / "settings.json"


def load() -> dict:
    """Padrões + o que estiver no arquivo (chave desconhecida ou de tipo
    errado é ignorada: um arquivo editado à mão não derruba nada)."""
    data = dict(DEFAULTS)
    try:
        saved = json.loads(path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return data
    except (OSError, ValueError) as exc:
        log.warning("configurações ilegíveis (%s); usando os padrões", exc)
        return data
    if isinstance(saved, dict):
        for key, value in saved.items():
            if key in DEFAULTS and type(value) is type(DEFAULTS[key]):
                data[key] = value
    return data


def get() -> dict:
    global _cache
    if _cache is None:
        _cache = load()
    return _cache


def update(**changes) -> dict:
    """Muda, grava (substituindo o arquivo de uma vez) e devolve tudo."""
    data = dict(get())
    data.update(changes)
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    os.replace(tmp, target)
    global _cache
    _cache = data
    return data


def reset(*keys: str) -> dict:
    return update(**{k: DEFAULTS[k] for k in keys or DEFAULTS})


def shows(op) -> bool:
    """A operação aparece na roda? Presets fora da roda só se o usuário ligou."""
    data = get()
    if op.id in data["hidden"]:
        return False
    return op.in_wheel or op.id in data["extra"]


def set_shown(op, shown: bool) -> None:
    hidden = [i for i in get()["hidden"] if i != op.id]
    extra = [i for i in get()["extra"] if i != op.id]
    if shown and not op.in_wheel:
        extra.append(op.id)
    elif not shown and op.in_wheel:
        hidden.append(op.id)
    update(hidden=sorted(hidden), extra=sorted(extra))


def output_dir() -> Path | None:
    """Pasta fixa de saída, se o usuário escolheu uma que existe."""
    data = get()
    if data["output"] != "folder" or not data["output_folder"]:
        return None
    folder = Path(data["output_folder"])
    return folder if folder.is_dir() else None


def wheel_scale() -> float:
    return WHEEL_SCALE.get(get()["wheel_size"], 1.0)
