"""Chamadas Win32 que dá para testar sem mexer no mouse (só no Windows)."""
import ctypes
import sys
from ctypes import wintypes as W
from pathlib import Path

import pytest

if sys.platform != "win32":
    pytest.skip("só no Windows", allow_module_level=True)

from mexerica.desktop import win32  # noqa: E402

CF_HDROP, DVASPECT_CONTENT, TYMED_HGLOBAL = 15, 1, 1


class FORMATETC(ctypes.Structure):
    _fields_ = [("cfFormat", ctypes.c_ushort), ("ptd", ctypes.c_void_p),
                ("dwAspect", W.DWORD), ("lindex", ctypes.c_long),
                ("tymed", W.DWORD)]


class STGMEDIUM(ctypes.Structure):
    _fields_ = [("tymed", W.DWORD), ("hGlobal", ctypes.c_void_p),
                ("pUnkForRelease", ctypes.c_void_p)]


DragQueryFileW = win32._fn(ctypes.WinDLL("shell32"), "DragQueryFileW", W.UINT,
                           ctypes.c_void_p, W.UINT, W.LPWSTR, W.UINT)
ReleaseStgMedium = win32._fn(ctypes.WinDLL("ole32"), "ReleaseStgMedium",
                             None, ctypes.POINTER(STGMEDIUM))


def dropped_paths(obj: int) -> list[str]:
    """O que um app recebe ao soltar: o CF_HDROP do IDataObject."""
    vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
    get_data = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                  ctypes.POINTER(FORMATETC),
                                  ctypes.POINTER(STGMEDIUM))(vtbl.contents[3])
    fmt = FORMATETC(CF_HDROP, None, DVASPECT_CONTENT, -1, TYMED_HGLOBAL)
    medium = STGMEDIUM()
    assert get_data(obj, ctypes.byref(fmt), ctypes.byref(medium)) == 0
    try:
        count = DragQueryFileW(medium.hGlobal, 0xFFFFFFFF, None, 0)
        buf = ctypes.create_unicode_buffer(1024)
        out = []
        for i in range(count):
            DragQueryFileW(medium.hGlobal, i, buf, len(buf))
            out.append(buf.value)
        return out
    finally:
        ReleaseStgMedium(ctypes.byref(medium))


@pytest.fixture(autouse=True)
def ole():
    win32.OleInitialize(None)


class MSG(ctypes.Structure):
    _fields_ = [("hwnd", W.HWND), ("message", W.UINT), ("wParam", W.WPARAM),
                ("lParam", W.LPARAM), ("time", W.DWORD), ("pt", W.POINT),
                ("lPrivate", W.DWORD)]


PeekMessageW = win32._fn(win32.user32, "PeekMessageW", W.BOOL,
                         ctypes.POINTER(MSG), W.HWND, W.UINT, W.UINT, W.UINT)
DispatchMessageW = win32._fn(win32.user32, "DispatchMessageW",
                             ctypes.c_ssize_t, ctypes.POINTER(MSG))


def pump(hwnd) -> None:
    """Entrega as mensagens da janela (no serviço, quem faz é o laço do GTK)."""
    msg = MSG()
    while PeekMessageW(ctypes.byref(msg), hwnd, 0, 0, 1):        # PM_REMOVE
        DispatchMessageW(ctypes.byref(msg))


IsWindow = win32._fn(win32.user32, "IsWindow", W.BOOL, W.HWND)


def tray_windows() -> list[int]:
    """Janelas da bandeja da Mexerica (o serviço de verdade pode ter uma)."""
    found, hwnd = [], None
    while hwnd := win32.FindWindowExW(None, hwnd, win32.TRAY_CLASS, None):
        found.append(hwnd)
    return found


def test_tray_icon_click_and_close():
    icon = Path(win32.__file__).parents[1] / "data" / "icon.ico"
    events = []
    tray = win32.Tray(icon, "Mexerica (teste)", lambda: events.append("abrir"),
                      [("Sair", lambda: None)], lambda: events.append("fechar"))
    try:
        assert tray.shown, "ícone entrou na área de notificação"
        # o instalador acha a janela pela classe
        assert tray.hwnd in tray_windows()
        win32.PostMessageW(tray.hwnd, tray.CALLBACK, 0, win32.WM_LBUTTONUP)
        win32.PostMessageW(tray.hwnd, tray.OPEN, 0, 0)       # 2ª instância
        win32.PostMessageW(tray.hwnd, win32.WM_CLOSE, 0, 0)  # instalador
        pump(tray.hwnd)
        assert events == ["abrir", "abrir", "fechar"]
    finally:
        tray.remove()
    assert not IsWindow(tray.hwnd)


def test_tray_receives_files_from_another_instance(tmp_path):
    """Sem o D-Bus do GLib, o "Converter com a Mexerica" de outro processo
    entrega a lista de arquivos à janela da bandeja (WM_COPYDATA)."""
    icon = Path(win32.__file__).parents[1] / "data" / "icon.ico"
    got = []
    tray = win32.Tray(icon, "Mexerica (teste)", lambda: None, [], lambda: None,
                      on_files=got.append)
    try:
        paths = [str(tmp_path / "relatório final.pdf"), str(tmp_path / "b.png")]
        assert win32.send_files(tray.hwnd, paths)
        assert got == [[Path(p) for p in paths]]
    finally:
        tray.remove()


def test_explorer_image_and_name(tmp_path):
    doc = tmp_path / "relatório final.txt"
    doc.write_text("oi", encoding="utf-8")
    w, h, pixels = win32.shell_image(doc, 64)
    assert w > 0 and h > 0 and len(pixels) == w * h * 4
    assert any(pixels[3::4]), "ícone com alguma parte visível"
    assert win32.display_name(doc) in ("relatório final.txt", "relatório final")


@pytest.mark.parametrize("names", [
    ["relatório de sondagem.pdf"],
    ["a.png", "b é.txt"],
    ["pasta 1/um.txt", "pasta 2/dois.txt"],          # pastas diferentes
])
def test_float_drag_carries_the_files(tmp_path, names):
    paths = []
    for name in names:
        p = tmp_path / name
        p.parent.mkdir(exist_ok=True)
        p.write_text("x", encoding="utf-8")
        paths.append(p)
    obj = win32.file_data_object(paths)
    try:
        assert dropped_paths(obj) == [str(p) for p in paths]
    finally:
        win32.com_release(obj)
