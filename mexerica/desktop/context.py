"""Windows: "Ações da Mexerica" no menu de contexto do Explorer.

Um verbo em HKCU\\Software\\Classes\\{*,Directory,Directory\\Background}
\\shell\\MexericaWheel (no Windows 11, em "Mostrar mais opções") que roda
data/wheel.pyw: ele lê a seleção da janela do Explorer em primeiro plano e
pede ao serviço a roda de ações no ponteiro.

O menu moderno do Windows 11 (o primeiro, sem "Mostrar mais opções") só
aceita extensões IExplorerCommand num DLL com identidade de pacote; isso
fica para o pacote da Store. A versão da Store também não grava em
HKCU\\Software\\Classes (o registro do pacote é virtualizado), então lá
isto fica desligado.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from ..i18n import _

log = logging.getLogger("mexerica")

KEY = "MexericaWheel"
CLASSES = ("*", "Directory", r"Directory\Background")
LABEL = "Ações da Mexerica"          # traduzido ao registrar (i18n)
SCRIPT = Path(__file__).resolve().parent.parent / "data" / "wheel.pyw"


def available() -> bool:
    if sys.platform != "win32":
        return False
    from .win32 import packaged
    return not packaged()


def _win(path) -> str:
    return str(path).replace("/", "\\")


def _pythonw() -> str:
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return _win(w if w.exists() else exe)


def command(cls: str) -> str:
    # no fundo da pasta (Directory\Background) o alvo é %V, a própria pasta
    target = "%V" if cls.endswith("Background") else "%1"
    return f'"{_pythonw()}" -X utf8 "{_win(SCRIPT)}" "{target}"'


def _icon() -> str:
    ico = SCRIPT.with_name("icon.ico")
    return _win(ico) if ico.exists() else ""


def register() -> bool:
    if not available():
        return False
    import winreg
    try:
        for cls in CLASSES:
            path = rf"Software\Classes\{cls}\shell\{KEY}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ,
                                  _(LABEL))
                if _icon():
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, _icon())
                # vários arquivos: o Explorer chama uma vez por item; o
                # script lê a seleção toda e o serviço junta as chamadas
                winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ,
                                  "Player")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                  path + r"\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command(cls))
    except OSError as exc:
        log.warning("menu de contexto não registrado: %s", exc)
        return False
    log.info("menu de contexto \"%s\" registrado", LABEL)
    return True


def _delete_tree(root, path: str) -> None:
    import winreg
    try:
        with winreg.OpenKey(root, path) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_tree(root, path + "\\" + sub)
        winreg.DeleteKey(root, path)
    except FileNotFoundError:
        pass


def unregister() -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        for cls in CLASSES:
            _delete_tree(winreg.HKEY_CURRENT_USER,
                         rf"Software\Classes\{cls}\shell\{KEY}")
    except OSError as exc:
        log.warning("menu de contexto não removido: %s", exc)
        return False
    return True


def registered() -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            rf"Software\Classes\*\shell\{KEY}\command") as k:
            return _win(SCRIPT) in winreg.QueryValue(k, "")
    except OSError:
        return False


__all__ = ["available", "register", "unregister", "registered", "command"]
