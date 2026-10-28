"""Conversões recentes (página Início)."""
import datetime as dt
from pathlib import Path

from mexerica import history


def test_newest_first_and_limited(isolated_history):
    for i in range(history.LIMIT + 5):
        history.add("to-jpg", "JPG", [Path(f"f{i}.png")], [Path(f"f{i}.jpg")])
    entries = history.load()
    assert len(entries) == history.LIMIT
    assert entries[0]["outputs"] == [str(Path(f"f{history.LIMIT + 4}.jpg"))]
    history.add("to-png", "PNG", [Path("x.jpg")], [])       # sem saída: nada
    assert len(history.load()) == history.LIMIT
    history.clear()
    assert history.load() == []


def test_bad_file_is_an_empty_history(isolated_history):
    isolated_history.write_text("{ quebrado", encoding="utf-8")
    assert history.load() == []
    isolated_history.write_text('[{"outputs": []}, 3, {"outputs": ["a"]}]',
                                encoding="utf-8")
    assert history.load() == [{"outputs": ["a"]}]
    history.add("to-jpg", "JPG", [Path("b.png")], [Path("b.jpg")])
    assert len(history.load()) == 2                         # e segue gravando


def test_when_text():
    now = dt.datetime(2026, 10, 28, 15, 0)

    def ago(**kw):
        return history.when_text(
            {"time": (now - dt.timedelta(**kw)).isoformat()}, now)
    assert ago(seconds=20) == "agora"
    assert ago(minutes=5) == "há 5 min"
    assert ago(hours=3) == "há 3 h"
    assert ago(hours=20) == "ontem"
    assert ago(days=9) == "19/10/2026"
    assert history.when_text({}) == ""
