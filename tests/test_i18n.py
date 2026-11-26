"""Idioma da interface: catálogo completo, placeholders e escolha do idioma."""
import re
import sys

import pytest

from mexerica import i18n, settings
from mexerica.i18n_en import EN

sys.path.insert(0, __file__.rsplit("tests", 1)[0] + "tests")
import i18n_strings  # noqa: E402


def test_every_text_has_english():
    """Texto novo na interface precisa de tradução em i18n_en.py
    (python tests/i18n_strings.py lista o que falta)."""
    assert i18n_strings.missing() == []


@pytest.mark.parametrize("pt", sorted(EN))
def test_placeholders_match(pt):
    fields = lambda s: sorted(re.findall(r"\{[^}]*\}", s))  # noqa: E731
    assert fields(pt) == fields(EN[pt])


def test_translate_follows_the_setting(monkeypatch):
    monkeypatch.setattr(i18n, "_lang", None)
    settings.update(language="en")
    assert i18n._("Abrir o log") == "Open the log"
    assert i18n.plural(3, "1 página", "{n} páginas") == "3 pages"
    assert i18n._("texto sem tradução") == "texto sem tradução"
    settings.update(language="pt")
    i18n.reset()
    assert i18n._("Abrir o log") == "Abrir o log"
    assert i18n.plural(1, "1 página", "{n} páginas") == "1 página"


@pytest.mark.parametrize("env,lang", [
    ({"LANG": "pt_BR.UTF-8"}, "pt"), ({"LANG": "pt_PT.UTF-8"}, "pt"),
    ({"LANG": "en_US.UTF-8"}, "en"), ({"LANG": "es_ES.UTF-8"}, "en"),
    ({"LANGUAGE": "en_GB:pt_BR", "LANG": "pt_BR.UTF-8"}, "en"),
    ({"LANG": "C.UTF-8"}, "pt")])
def test_system_language_linux(monkeypatch, env, lang):
    monkeypatch.setattr(i18n.sys, "platform", "linux")
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert i18n.system_language() == lang


def test_wheel_labels_per_language(monkeypatch):
    from mexerica import theme as TH
    from mexerica.engine import BY_ID
    assert TH.wheel_label(BY_ID["pdf-order"]) == "JUNTAR"
    assert TH.wheel_label(BY_ID["to-jpg"]) == "JPG"
    monkeypatch.setattr(i18n, "_lang", "en")
    assert TH.wheel_label(BY_ID["pdf-order"]) == "MERGE"
    assert TH.wheel_label(BY_ID["img-crop"]) == "CROP"
    # sem rótulo próprio, vale a tradução do nome
    assert TH.wheel_label(BY_ID["img-1mb"]) == "≤ 1 MB"
    # os dois dicionários de rótulos cobrem as mesmas operações
    assert set(TH.LABELS) == set(TH.LABELS_PT)


def test_errors_in_english(monkeypatch):
    from mexerica.engine import edits as E
    monkeypatch.setattr(i18n, "_lang", "en")
    with pytest.raises(ValueError, match="is not a range"):
        E.parse_ranges("abc", 5)
    with pytest.raises(ValueError, match="the PDF has pages 1 to 5"):
        E.parse_ranges("9", 5)
