"""Nomes lógicos de programas em cada sistema (sem rodar nenhum)."""
import pytest

from mexerica.engine import tools as T


@pytest.fixture
def system(monkeypatch):
    """Finge um sistema com os programas dados: system(windows, {nome: caminho})."""
    def setup(windows: bool, found: dict[str, str], bsdtar: bool = True):
        monkeypatch.setattr(T, "WINDOWS", windows)
        monkeypatch.setattr(T, "which", found.get)
        monkeypatch.setattr(T, "_is_bsdtar", lambda _p: bsdtar)
        T.resolve.cache_clear()
    yield setup
    T.resolve.cache_clear()


def test_windows_never_takes_the_system_convert(system):
    system(True, {"convert": r"C:\Windows\System32\convert.exe"})
    assert T.resolve("magick") is None
    assert T.resolve("montage") is None
    system(False, {"convert": "/usr/bin/convert"})
    assert T.resolve("magick") == ["/usr/bin/convert"]   # ImageMagick 6


def test_magick_is_absolute(system):
    system(True, {"magick": r"C:\msys64\ucrt64\bin\magick.exe"})
    assert T.resolve("magick") == [r"C:\msys64\ucrt64\bin\magick.exe"]
    assert T.resolve("montage") == [r"C:\msys64\ucrt64\bin\magick.exe",
                                    "montage"]


def test_ghostscript_windows_name(system):
    gs = r"C:\Program Files\gs\gs10.04.0\bin\gswin64c.exe"
    system(True, {"gswin64c": gs})
    assert T.resolve("gs") == [gs]


def test_windows_tar_is_bsdtar(system):
    tar = r"C:\Windows\System32\tar.exe"
    system(True, {"tar": tar})
    assert T.resolve("bsdtar") == [tar]
    system(True, {"tar": tar}, bsdtar=False)
    assert T.resolve("bsdtar") is None
    system(False, {"tar": "/usr/bin/tar"})                # GNU tar não serve
    assert T.resolve("bsdtar") is None
