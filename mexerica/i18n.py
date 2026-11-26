"""Idioma da interface: português (o texto do código) ou inglês.

Todo texto que o usuário vê passa por `_()`: o argumento é o português e,
com o inglês ativo, sai a tradução de `i18n_en.EN` (sem tradução, fica o
português). Textos com valores usam `.format()` depois do `_()`:

    _("{n} páginas").format(n=3)

`N_()` só marca um texto para tradução (listas no nível do módulo); quem
mostra chama `_()` na hora.

O idioma vem de Configurações > Aparência > Idioma: "system" (padrão),
"pt" ou "en". Em "system", sistema em português (qualquer país) abre em
português e qualquer outro idioma abre em inglês. Puro Python, sem GTK.
"""
from __future__ import annotations

import os
import sys

LANGUAGES = ("system", "pt", "en")
_lang: str | None = None


def system_language() -> str:
    """'pt' se o sistema está em português, senão 'en'."""
    if sys.platform == "win32":
        try:
            import ctypes
            lang = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "pt" if lang & 0x3FF == 0x16 else "en"   # LANG_PORTUGUESE
        except (AttributeError, OSError):
            return "pt"
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        first = value.split(":")[0].strip()
        if first and first not in ("C", "POSIX", "C.UTF-8"):
            return "pt" if first.lower().startswith("pt") else "en"
    return "pt"


def language() -> str:
    """O idioma em uso: 'pt' ou 'en'."""
    global _lang
    if _lang is None:
        choice = "system"
        try:
            from . import settings
            choice = settings.get().get("language", "system")
        except Exception:  # noqa: BLE001 - configurações ilegíveis
            pass
        _lang = system_language() if choice not in ("pt", "en") else choice
    return _lang


def reset() -> None:
    """Relê a escolha (depois de mudar nas Configurações)."""
    global _lang
    _lang = None


def _(text: str) -> str:
    if not text or language() == "pt":
        return text
    from .i18n_en import EN
    return EN.get(text, text)


def N_(text: str) -> str:
    return text


def plural(n: int, one: str, many: str) -> str:
    """_('1 página') / _('{n} páginas'), já com o número."""
    return (_(one) if n == 1 else _(many)).format(n=n)


__all__ = ["_", "N_", "plural", "language", "system_language", "reset",
           "LANGUAGES"]
