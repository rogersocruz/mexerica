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


def test_numbers_saved_as_float_still_count(isolated_settings):
    isolated_settings.write_text(json.dumps(
        {"dim": 40.0, "window_opacity": 80.5, "animations": 1}),
        encoding="utf-8")
    data = settings.load()
    assert data["dim"] == 40 and type(data["dim"]) is int
    assert data["window_opacity"] == settings.DEFAULTS["window_opacity"]
    assert data["animations"] is True                  # 1 não vira bool


def test_stage_is_live_and_flush_persists(isolated_settings):
    settings.stage(dim=50)
    assert settings.get()["dim"] == 50 and not isolated_settings.exists()
    assert settings.flush()
    assert json.loads(isolated_settings.read_text("utf-8"))["dim"] == 50


def test_busy_file_keeps_the_change(isolated_settings, monkeypatch):
    """Windows: o replace falha com o arquivo ocupado. A mudança continua
    valendo e a próxima gravação leva tudo."""
    import os
    real = os.replace
    calls = []

    def busy(a, b):
        calls.append(1)
        raise PermissionError("ocupado")
    monkeypatch.setattr(settings.os, "replace", busy)
    monkeypatch.setattr(settings.time, "sleep", lambda s: None)
    settings.update(style="uva")
    assert settings.get()["style"] == "uva" and len(calls) == 5
    monkeypatch.setattr(settings.os, "replace", real)
    settings.update(dim=10)
    saved = json.loads(isolated_settings.read_text("utf-8"))
    assert saved["style"] == "uva" and saved["dim"] == 10


@pytest.mark.parametrize("ext,args", [
    ("jpg", ["-quality", "92"]), ("webp", ["-quality", "85"]),
    ("avif", ["-quality", "60"]), ("heic", ["-quality", "70"]),
    ("jxl", ["-quality", "85"]),
    ("png", ["-define", "png:compression-level=7"]), ("gif", [])])
def test_quality_per_format(ext, args):
    from mexerica.engine.ops import quality_args
    assert quality_args(ext) == args


def test_quality_follows_settings():
    from mexerica.engine.ops import quality_args
    settings.update(avif_quality=33, webp_lossless=True)
    assert quality_args("avif") == ["-quality", "33"]
    assert "webp:lossless=true" in quality_args("webp")
