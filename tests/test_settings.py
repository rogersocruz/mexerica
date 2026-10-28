"""Configurações: arquivo, itens da roda, pasta de saída e estilos."""
import json

import pytest

from mexerica import settings
from mexerica import theme as TH
from mexerica.engine import BY_ID, CONVERT, TOOLS, options_for, run
from mexerica.engine import formats as F
from mexerica.engine.ops import Op


def test_defaults_without_file(isolated_settings):
    assert not isolated_settings.exists()
    assert settings.get() == settings.DEFAULTS


def test_bad_file_falls_back_and_keeps_good_keys(isolated_settings):
    isolated_settings.write_text("{ isso não é json", encoding="utf-8")
    assert settings.load() == settings.DEFAULTS
    isolated_settings.write_text(json.dumps(
        {"style": "uva", "dim": "muito", "desconhecida": 1}), encoding="utf-8")
    data = settings.load()
    assert data["style"] == "uva"                      # chave boa entra
    assert data["dim"] == settings.DEFAULTS["dim"]     # tipo errado: padrão
    assert "desconhecida" not in data


def test_update_persists(isolated_settings):
    settings.update(style="menta", wheel_size="large")
    saved = json.loads(isolated_settings.read_text(encoding="utf-8"))
    assert saved["style"] == "menta" and settings.wheel_scale() == 1.2
    settings.reset("style")
    assert settings.get()["style"] == "mexerica"


def test_wheel_items_hidden_and_presets(tmp_path):
    png = tmp_path / "foto.png"
    jpg, preset = BY_ID["to-jpg"], BY_ID["img-1mb"]
    assert settings.shows(jpg) and not settings.shows(preset)
    settings.set_shown(jpg, False)
    settings.set_shown(preset, True)                   # preset fora da roda
    assert settings.get()["hidden"] == ["to-jpg"]
    assert settings.get()["extra"] == ["img-1mb"]
    assert not settings.shows(jpg) and settings.shows(preset)
    # a roda segue as escolhas; sem `shown`, os padrões
    ids = [o.id for o in options_for([png], TOOLS, settings.shows)]
    if BY_ID["img-1mb"].is_available():
        assert "img-1mb" in ids
    assert "img-1mb" not in [o.id for o in options_for([png], TOOLS)]
    assert "to-jpg" not in [o.id for o in options_for([png], CONVERT,
                                                      settings.shows)]
    settings.reset("hidden", "extra")
    assert settings.shows(jpg) and not settings.shows(preset)


def _write_op() -> Op:
    """Operação sem programa externo: grava um texto na saída."""
    def build(ctx):
        return [lambda c: c.out.write_text("ok", encoding="utf-8")]
    return Op("escreve", "Escreve", CONVERT, frozenset({F.TEXT}), build,
              ext="out")


def test_output_folder(tmp_path):
    src = tmp_path / "nota.txt"
    src.write_text("oi", encoding="utf-8")
    beside = run(_write_op(), [src]).outputs[0]
    assert beside.parent == tmp_path
    elsewhere = tmp_path / "saída"
    elsewhere.mkdir()
    settings.update(output="folder", output_folder=str(elsewhere))
    out = run(_write_op(), [src]).outputs[0]
    assert out.parent == elsewhere and out.name == "nota.out"
    # pasta que sumiu: volta para o lado do original
    settings.update(output_folder=str(tmp_path / "não existe"))
    assert run(_write_op(), [src]).outputs[0].parent == tmp_path


@pytest.mark.parametrize("style", list(TH.STYLES))
def test_every_style_applies(style):
    TH.apply(style, 0.8, animations=False)
    try:
        assert TH.STYLE == style and TH.ENTER_MS == 1
        assert len(TH.HOVER_TOP) == 4 and len(TH.SECTOR_TOP) == 4
        assert TH.STYLES[style]["accent"] in TH.CSS
        assert "alpha(%s, 0.8)" % TH.STYLES[style]["top"] in TH.CSS
    finally:
        TH.apply()
    assert TH.ENTER_MS == TH.MOTION["ENTER_MS"]
