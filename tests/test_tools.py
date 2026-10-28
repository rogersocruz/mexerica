"""Nomes lógicos de programas em cada sistema (sem rodar nenhum)."""
import subprocess

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


LIST_FORMAT = """\
   Format  Module    Mode  Description
-------------------------------------------------------------------------------
      3FR  DNG       r--   Hasselblad CFV/H3D39II Raw Format (0.22.3-Release)
     HEIC  HEIC      rw+   High Efficiency Image Format (1.23.6)
     JPEG* JPEG      rw-   Joint Photographic Experts Group JFIF format
      PDF  PDF       rw+   Portable Document Format
"""


@pytest.fixture
def magick(tmp_path, monkeypatch):
    """magick falso: conta quantas vezes `-list format` rodou."""
    exe = tmp_path / "bin" / "magick.exe"
    exe.parent.mkdir()
    exe.touch()
    monkeypatch.setattr(T, "resolve", lambda _n: [str(exe)])
    monkeypatch.setattr(T, "cache_dir", lambda: tmp_path / "cache")
    calls = []

    def fake_run(argv, **_kw):
        calls.append(argv)
        if fake_run.fail:
            raise subprocess.TimeoutExpired(argv, 60)
        return subprocess.CompletedProcess(argv, 0, LIST_FORMAT, "")
    fake_run.fail = False
    monkeypatch.setattr(T.subprocess, "run", fake_run)
    T.magick_writable.cache_clear()
    yield exe, calls, fake_run
    T.magick_writable.cache_clear()


def test_magick_formats_cached_on_disk(magick):
    """`-list format` leva ~10 s no Windows: roda uma vez por instalação."""
    exe, calls, _run = magick
    assert T.magick_writable() == {"heic", "jpeg", "pdf"}   # 3FR só lê
    T.magick_writable.cache_clear()                         # outro processo
    assert T.magick_writable() == {"heic", "jpeg", "pdf"}
    assert len(calls) == 1
    (exe.parent / "libheif-1.dll").touch()                  # pasta mudou
    T.magick_writable.cache_clear()
    T.magick_writable()
    assert len(calls) == 2


def test_magick_listing_failure_keeps_basic_formats(magick):
    _exe, calls, run = magick
    run.fail = True
    assert T.magick_writable() == T.MAGICK_BASIC
    run.fail = False
    T.magick_writable.cache_clear()
    assert T.magick_writable() == {"heic", "jpeg", "pdf"}   # falha não ficou
    assert len(calls) == 2


def test_windows_tar_is_bsdtar(system):
    tar = r"C:\Windows\System32\tar.exe"
    system(True, {"tar": tar})
    assert T.resolve("bsdtar") == [tar]
    system(True, {"tar": tar}, bsdtar=False)
    assert T.resolve("bsdtar") is None
    system(False, {"tar": "/usr/bin/tar"})                # GNU tar não serve
    assert T.resolve("bsdtar") is None
