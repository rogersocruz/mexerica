"""Cada teste com configurações e histórico próprios, longe dos do usuário
(uma pasta de saída escolhida nas Configurações desviaria os arquivos dos
testes)."""
import pytest

from mexerica import history, settings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path_factory, monkeypatch):
    path = tmp_path_factory.mktemp("config") / "settings.json"
    monkeypatch.setattr(settings, "path", lambda: path)
    monkeypatch.setattr(settings, "_cache", None)
    return path


@pytest.fixture(autouse=True)
def isolated_history(tmp_path_factory, monkeypatch):
    path = tmp_path_factory.mktemp("cache") / "history.json"
    monkeypatch.setattr(history, "path", lambda: path)
    return path
