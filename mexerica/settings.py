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
import time
from pathlib import Path

log = logging.getLogger("mexerica")

DEFAULTS: dict = {
    "language": "system",      # system (idioma do sistema) | pt | en
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
    # qualidade das conversões de imagem (o Editar… e os presets têm a sua)
    "webp_quality": 85,
    "webp_lossless": False,
    "avif_quality": 60,
    "heic_quality": 70,
    "jxl_quality": 85,
    "png_compression": 7,      # 0..9, sem perda: só tamanho x tempo
    # vidro atrás da roda: system (borrão do Windows/GNOME), custom (a
    # própria Mexerica captura e borra a tela, em memória) ou off
    "blur": "system",
    "blur_radius": 18,         # px do borrão custom (e do GNOME)
    # Windows: a roda de ações com Ctrl + botão direito sobre arquivos
    "right_click_wheel": False,
    "notify_start": True,      # notificação quando um trabalho começa
    # versão da Microsoft Store: a StartupTask do pacote sempre sobe o
    # serviço, que sai na hora se isto estiver desligado
    "autostart": True,
    "hotkeys_asked": False,    # o aviso dos atalhos de teclado já apareceu
    # Gerar QR code > Personalizar: a última escolha (edits.QrStyle)
    "qr_fg": "#000000",
    "qr_bg": "#FFFFFF",
    "qr_transparent": False,
    "qr_size": 600,
    "qr_margin": 4,
    "qr_level": "M",
    "qr_fmt": "png",
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
            if key in DEFAULTS:
                value = _coerce(value, DEFAULTS[key])
                if value is not None:
                    data[key] = value
    return data


def _coerce(value, default):
    """O valor no tipo do padrão, ou None. Número inteiro gravado como
    float (92.0, de um slider ou de outra versão) vale como int."""
    if type(value) is type(default):
        return value
    if type(default) is int and type(value) is float and value.is_integer():
        return int(value)
    if type(default) is float and type(value) is int:
        return float(value)
    return None


def get() -> dict:
    global _cache
    if _cache is None:
        _cache = load()
    return _cache


def stage(**changes) -> dict:
    """Muda só na memória (vale na hora para este processo); flush() grava.
    Os sliders usam isto: um arraste gera dezenas de mudanças."""
    global _cache
    data = dict(get())
    data.update(changes)
    _cache = data
    return data


def update(**changes) -> dict:
    """Muda, grava (substituindo o arquivo de uma vez) e devolve tudo."""
    data = stage(**changes)
    flush()
    return data


def flush() -> bool:
    """Grava o que está na memória. No Windows o replace falha quando outro
    programa (antivírus, indexador, a extensão lendo) segura o arquivo por
    um instante: tenta de novo antes de desistir. A mudança continua valendo
    na memória mesmo se a gravação falhar, e a próxima tentativa leva tudo."""
    data = get()
    target = path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                       encoding="utf-8")
    except OSError as exc:
        log.warning("não deu para gravar as configurações: %s", exc)
        return False
    for attempt in range(5):
        try:
            os.replace(tmp, target)
            return True
        except PermissionError as exc:
            if attempt == 4:
                log.warning("configurações não gravadas (%s): arquivo "
                            "ocupado", exc)
            time.sleep(0.05 * (attempt + 1))
        except OSError as exc:
            log.warning("configurações não gravadas: %s", exc)
            break
    return False


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
