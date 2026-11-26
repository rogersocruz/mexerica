"""Roda por clique: o comando `mexerica wheel` (e o registro do antigo
item de menu, que a Mexerica agora só remove)."""
import sys
from pathlib import Path

import pytest

from mexerica import __main__ as M
from mexerica.desktop import context

win = pytest.mark.skipif(sys.platform != "win32", reason="só no Windows")


@win
def test_verb_command_uses_pythonw_and_script():
    cmd = context.command("*")
    assert cmd.endswith(f'"{context._win(context.SCRIPT)}" "%1"')
    assert " -X utf8 " in cmd and "/" not in cmd
    assert context.command(r"Directory\Background").endswith('"%V"')
    assert context.SCRIPT.exists()


def test_wheel_needs_files(tmp_path, capsys):
    assert M.cmd_wheel([str(tmp_path / "não existe.txt")]) == 1


@win
def test_wheel_goes_to_the_running_service(tmp_path, monkeypatch):
    from mexerica.desktop import shellview, win32
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    sent = []
    monkeypatch.setattr(win32, "FindWindowExW", lambda *_a: 1234)
    monkeypatch.setattr(win32, "send_files",
                        lambda h, lines, kind: sent.append((h, lines, kind))
                        or True)
    # o Explorer passa um item; a seleção na tela tem os dois, nesta ordem
    monkeypatch.setattr(shellview, "selection_at", lambda hwnd: [b, a])
    assert M.cmd_wheel(["--explorer", str(a)]) == 0
    assert sent == [(1234, ["actions", str(b), str(a)], win32.COPY_WHEEL)]
    # item fora da seleção (outra janela em primeiro plano): só ele
    sent.clear()
    monkeypatch.setattr(shellview, "selection_at", lambda hwnd: [b])
    M.cmd_wheel(["--explorer", "--group", "tools", str(a)])
    assert sent[0][1] == ["tools", str(a)]


def test_natural_order():
    from mexerica.desktop.shellview import natural_key
    names = ["R0-10.pdf", "R0-2.pdf", "R0.pdf", "r0-1.pdf"]
    assert sorted(names, key=lambda n: natural_key(Path(n))) == \
        ["R0.pdf", "r0-1.pdf", "R0-2.pdf", "R0-10.pdf"]


def test_linux_backend_choice(monkeypatch):
    from mexerica.desktop import cosmic
    for value, gnome, cos in (("ubuntu:GNOME", True, False),
                              ("pop:GNOME", True, False),
                              ("COSMIC", False, True), ("KDE", False, False)):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", value)
        assert cosmic.is_gnome() is gnome and cosmic.is_cosmic() is cos
    monkeypatch.setenv("MEXERICA_NO_LAYER_SHELL", "1")
    assert cosmic.layer_shell_preload() is None
