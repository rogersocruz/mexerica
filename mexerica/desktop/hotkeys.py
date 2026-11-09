"""Atalhos do Windows que trocam o teclado com Alt+Shift e Ctrl+Shift.

São as teclas das rodas de ferramentas (Shift+Alt) e de ações
(Shift+Ctrl): com mais de um teclado instalado, cada roda aberta trocaria
o teclado junto. O mesmo que o windows-hotkeys.ps1 faz na instalação por
script, para a versão da Microsoft Store (que não roda script nenhum ao
instalar): só muda com o usuário pedindo, em Configurações ou no aviso da
primeira vez. Os valores originais ficam no mesmo JSON do script, então
um desfaz o que o outro fez.
"""
from __future__ import annotations

import ctypes
import json
import logging
import os
import winreg
from pathlib import Path

log = logging.getLogger("mexerica")

KEY = r"Keyboard Layout\Toggle"
NAMES = ("Hotkey", "Language Hotkey", "Layout Hotkey")
OFF = "3"
# ausente = padrão do Windows: idioma com Alt+Shift (1), layout com Ctrl+Shift (2)
CONFLICTING = (None, "1", "2")
SPI_SETLANGTOGGLE = 0x5B
SPIF_SENDCHANGE = 2


def _backup() -> Path:
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData/Local")
    return Path(local, "Mexerica", "layout-hotkeys.json")


def _read() -> dict[str, str | None]:
    values: dict[str, str | None] = dict.fromkeys(NAMES)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as key:
            for name in NAMES:
                try:
                    values[name] = str(winreg.QueryValueEx(key, name)[0])
                except FileNotFoundError:
                    pass
    except FileNotFoundError:
        pass
    return values


def _apply() -> None:
    # o Windows relê os atalhos do registro na hora
    ctypes.windll.user32.SystemParametersInfoW(SPI_SETLANGTOGGLE, 0, None,
                                               SPIF_SENDCHANGE)


def conflicting() -> bool:
    """Algum atalho de troca de teclado ainda usa Alt+Shift ou Ctrl+Shift?"""
    return any(v in CONFLICTING for v in _read().values())


SETTINGS_URI = "ms-settings:keyboard"     # Teclado avançado
STEPS = ("Teclado avançado > Teclas de atalho do idioma de entrada > "
         "Alterar sequência de teclas: \"Não atribuído\" nas duas")


def open_windows_settings() -> None:
    """Versão da Store: o pacote não pede unvirtualizedResources, então o
    que ela gravasse no HKCU (ela ou um filho, como o reg.exe) ficaria na
    bolha do pacote e o Windows não veria. As Configurações do Windows
    abrem fora do pacote (ativação por protocolo) e a pessoa troca lá."""
    os.startfile(SETTINGS_URI)


def disable() -> None:
    current = _read()
    names = [n for n, v in current.items() if v in CONFLICTING]
    if not names:
        return
    backup = _backup()
    if not backup.exists():
        # guarda só o original: desligar de novo não perde o que havia antes
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(json.dumps(current, indent=2), encoding="utf-8")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY) as key:
        for name in names:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, OFF)
    _apply()
    log.info("atalhos de troca de teclado desligados: %s", ", ".join(names))


def restore() -> None:
    """Devolve os valores guardados; sem cópia, volta ao padrão do Windows."""
    backup = _backup()
    try:
        # (o do PowerShell 5.1 vem com BOM)
        saved = json.loads(backup.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        saved = {}
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY) as key:
        for name in NAMES:
            value = saved.get(name)
            if value is None:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
    backup.unlink(missing_ok=True)
    _apply()
    log.info("atalhos de troca de teclado restaurados")
