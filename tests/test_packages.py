"""Formatos extras: os comandos de instalar/remover em cada sistema e a
trava que impede remover o que outros programas usam."""
import pytest

from mexerica.engine import packages as PK

WIN = PK.System("windows", msys_bash="C:/msys64/usr/bin/bash.exe",
                winget="winget.exe")
APT = PK.System("apt", pkexec="/usr/bin/pkexec")
DNF = PK.System("dnf", pkexec="/usr/bin/pkexec")
PAC = PK.System("pacman", pkexec="/usr/bin/pkexec")


def test_windows_msys_and_winget():
    steps = PK.plan(PK.BY_ID["qr"], WIN, PK.INSTALL)
    assert steps == [["C:/msys64/usr/bin/bash.exe", "-lc",
                      "pacman -S --needed --noconfirm "
                      "mingw-w64-ucrt-x86_64-zbar "
                      "mingw-w64-ucrt-x86_64-qrencode"]]
    # remover com -R sem -s/-c: o pacman recusa se outro pacote depende;
    # só o que está instalado entra (pacman -Qq)
    remove = PK.plan(PK.BY_ID["qr"], WIN, PK.REMOVE)[0][2]
    assert "pacman -R --noconfirm $pkgs" in remove
    assert "pacman -Qq mingw-w64-ucrt-x86_64-zbar" in remove
    docs = PK.plan(PK.BY_ID["docs"], WIN, PK.INSTALL)
    assert docs[1][:4] == ["winget.exe", "install", "--id",
                           "JohnMacFarlane.Pandoc"]
    assert PK.plan(PK.BY_ID["office"], WIN, PK.REMOVE)[0][1] == "uninstall"


def test_windows_without_winget():
    no_winget = PK.System("windows", msys_bash=WIN.msys_bash)
    assert not PK.supported(PK.BY_ID["office"], no_winget, PK.INSTALL)
    assert PK.supported(PK.BY_ID["video"], no_winget, PK.INSTALL)


def test_linux_managers():
    assert PK.plan(PK.BY_ID["video"], APT, PK.INSTALL) == \
        [["/usr/bin/pkexec", "apt-get", "install", "-y", "ffmpeg"]]
    assert PK.plan(PK.BY_ID["pdf"], PAC, PK.REMOVE) == \
        [["/usr/bin/pkexec", "pacman", "-R", "--noconfirm", "qpdf",
          "poppler", "ghostscript"]]
    assert PK.plan(PK.BY_ID["video"], DNF, PK.INSTALL)[0][-1] == "ffmpeg-free"
    # o dnf tira junto o que depende: remover não é oferecido
    assert not PK.supported(PK.BY_ID["video"], DNF, PK.REMOVE)
    with pytest.raises(ValueError):
        PK.plan(PK.BY_ID["video"], DNF, PK.REMOVE)


def test_store_cannot_install():
    for kind in ("none", "store"):
        system = PK.System(kind)
        assert not system.can_install
        assert not any(PK.supported(p, system, PK.INSTALL)
                       for p in PK.PACKAGES)


def test_winget_already_done_is_success(monkeypatch):
    class Proc:
        def __init__(self, code):
            self.returncode, self.stdout, self.stderr = code, "", "x"
    codes = iter([0, 0x8A15002B])                 # pacman ok, winget "já"
    monkeypatch.setattr(PK.subprocess, "run",
                        lambda argv, **kw: Proc(next(codes)))
    monkeypatch.setattr(PK, "refresh", lambda: None)
    monkeypatch.setattr(PK.Package, "installed", lambda self: True)
    assert PK.apply(PK.BY_ID["docs"], PK.INSTALL, WIN) == (True, "")
    assert PK._winget_done(["C:/x/winget.exe"], -1978335212)   # assinado
    assert not PK._winget_done(["bash.exe"], 0x8A15002B)


def test_winget_retries_as_admin(monkeypatch):
    """Programa instalado para todos os usuários: sem administrador o
    winget falha (1603 do instalador); a Mexerica tenta de novo pedindo
    permissão. Recusar o aviso dá uma mensagem clara."""
    class Proc:
        def __init__(self, code):
            self.returncode, self.stdout = code, ""
            self.stderr = "Uninstall failed with exit code: 1603"
    monkeypatch.setattr(PK.subprocess, "run",
                        lambda argv, **kw: Proc(0x8A150030))
    monkeypatch.setattr(PK, "refresh", lambda: None)
    monkeypatch.setattr(PK.Package, "installed", lambda self: False)
    asked = []
    monkeypatch.setattr(PK, "run_elevated",
                        lambda argv: asked.append(argv) or 0)
    assert PK.apply(PK.BY_ID["ebook"], PK.REMOVE, WIN) == (True, "")
    assert asked and asked[0][1] == "uninstall"
    monkeypatch.setattr(PK, "run_elevated", lambda argv: PK.ERROR_CANCELLED)
    ok, msg = PK.apply(PK.BY_ID["ebook"], PK.REMOVE, WIN)
    assert not ok and "administrador" in msg
    monkeypatch.setattr(PK, "run_elevated", lambda argv: 1603)
    ok, msg = PK.apply(PK.BY_ID["ebook"], PK.REMOVE, WIN)
    assert not ok and "remover" in msg


def test_elevated_command_quotes():
    cmd = PK.elevated_command(["C:/x/winget.exe", "uninstall", "--id",
                               "calibre.calibre", "it's"])
    script = cmd[-1]
    assert "-Verb RunAs" in script and "-Wait -PassThru" in script
    assert "'C:/x/winget.exe'" in script and "'it''s'" in script
    assert "exit 1223" in script


def test_apt_simulation_guard():
    sim = ("Remv ghostscript [10.0]\nRemv cups-filters [1.28]\n"
           "Remv qpdf [11.3]\n")
    assert PK.apt_removes_only(["qpdf", "ghostscript"], sim) == \
        ["cups-filters"]
    assert PK.apt_removes_only(["qpdf"], "Remv qpdf:amd64 [11.3]\n") == []


def test_apt_remove_refuses_when_others_depend(monkeypatch):
    class Done:
        returncode = 0
        stdout = "Remv ghostscript [10]\nRemv cups [2]\n"
        stderr = ""
    calls = []
    monkeypatch.setattr(PK.subprocess, "run",
                        lambda argv, **kw: calls.append(argv) or Done())
    ok, msg = PK.apply(PK.BY_ID["pdf"], PK.REMOVE, APT)
    assert not ok and "cups" in msg
    assert calls == [["apt-get", "-s", "remove", "qpdf", "poppler-utils",
                      "ghostscript"]]              # nada removido de verdade


def test_every_package_installable_somewhere():
    for pkg in PK.PACKAGES:
        assert PK.supported(pkg, WIN, PK.INSTALL) or \
            PK.supported(pkg, APT, PK.INSTALL), pkg.id
        assert pkg.programs or pkg.modules or pkg.check, pkg.id
