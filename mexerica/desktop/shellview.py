"""O que as janelas do Explorer estão mostrando, via COM (ctypes puro).

- view_order(paths): os arquivos na ordem em que aparecem na tela (o
  arraste do Explorer entrega primeiro o arquivo em que se clicou, depois o
  resto na ordem da seleção; o Juntar quer a ordem da lista).
- selection_at(hwnd): os itens selecionados na janela do Explorer (ou na
  área de trabalho) `hwnd`, na ordem da tela: a roda no clique direito.

Caminho: IShellWindows -> IServiceProvider -> IShellBrowser ->
IShellView/IFolderView -> Items(SVGIO_*, IShellItemArray) -> IShellItem.
Sem comtypes/pywin32 (o Python do MSYS2 não tem): as chamadas vão direto
pela vtable de cada interface. Tudo devolve [] se algo falhar.
"""
from __future__ import annotations

import ctypes
import logging
import os
from ctypes import wintypes as W
from pathlib import Path

log = logging.getLogger("mexerica")

ole32 = ctypes.WinDLL("ole32")
oleaut32 = ctypes.WinDLL("oleaut32")


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    @classmethod
    def of(cls, text: str) -> "GUID":
        g = cls()
        ole32.CLSIDFromString(ctypes.c_wchar_p(text), ctypes.byref(g))
        return g


class VARIANT(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort),
                ("r2", ctypes.c_ushort), ("r3", ctypes.c_ushort),
                ("value", ctypes.c_longlong), ("extra", ctypes.c_longlong)]


CLSID_ShellWindows = GUID.of("{9BA05972-F6A8-11CF-A442-00A0C90A8F39}")
IID_IShellWindows = GUID.of("{85CB6900-4D95-11CF-960C-0080C7F4EE85}")
IID_IServiceProvider = GUID.of("{6D5140C1-7436-11CE-8034-00AA006009FA}")
SID_STopLevelBrowser = GUID.of("{4C96BE40-915C-11CF-99D3-00AA004AE837}")
IID_IShellBrowser = GUID.of("{000214E2-0000-0000-C000-000000000046}")
IID_IFolderView = GUID.of("{CDE725B0-CCC9-4519-917E-325D72FAB4CE}")
IID_IShellItemArray = GUID.of("{B63EA76D-1F85-456F-A19C-48159EFA858B}")

CLSCTX_ALL = 0x17
VT_I4, VT_EMPTY = 3, 0
SWC_DESKTOP = 8
SWFO_NEEDDISPATCH = 1
SVGIO_SELECTION, SVGIO_ALLVIEW = 0x1, 0x2
SVGIO_FLAG_VIEWORDER = 0x80000000
SIGDN_FILESYSPATH = 0x80058000

# índices na vtable (IUnknown: 0 QueryInterface, 1 AddRef, 2 Release)
_SW_COUNT, _SW_ITEM, _SW_FINDWINDOW = 7, 8, 15        # IShellWindows
_SP_QUERYSERVICE = 3                                    # IServiceProvider
_SB_QUERYACTIVESHELLVIEW = 15                           # IShellBrowser
_FV_ITEMS = 8                                           # IFolderView
_SIA_COUNT, _SIA_ITEMAT = 7, 8                          # IShellItemArray
_SI_DISPLAYNAME = 5                                     # IShellItem
_OW_GETWINDOW = 3                                       # IOleWindow


def _call(ptr, index: int, restype, *args):
    """Chama o método `index` da vtable do objeto COM `ptr`."""
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
    byref = type(ctypes.byref(ctypes.c_int()))
    types = [ctypes.c_void_p if type(a) is byref else type(a) for a in args]
    fn = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *types)(vtbl[0][index])
    return fn(ptr, *args)


def _release(ptr) -> None:
    if ptr:
        _call(ptr, 2, ctypes.c_ulong)


def _qi(ptr, iid: GUID):
    out = ctypes.c_void_p()
    hr = _call(ptr, 0, ctypes.c_long, ctypes.byref(iid), ctypes.byref(out))
    return out if hr == 0 and out.value else None


class _Com:
    """CoInitialize na thread atual (STA) enquanto dura o with."""

    def __enter__(self):
        self.hr = ole32.CoInitializeEx(None, 0x2)      # APARTMENTTHREADED
        return self

    def __exit__(self, *_a):
        if self.hr in (0, 1):                          # S_OK, S_FALSE
            ole32.CoUninitialize()


def _browsers():
    """(hwnd, IShellBrowser) de cada janela do Explorer e da área de
    trabalho. Quem chama solta os ponteiros."""
    sw = ctypes.c_void_p()
    if ole32.CoCreateInstance(ctypes.byref(CLSID_ShellWindows), None,
                              CLSCTX_ALL, ctypes.byref(IID_IShellWindows),
                              ctypes.byref(sw)) != 0 or not sw.value:
        return []
    disps = []
    try:
        count = ctypes.c_long()
        _call(sw, _SW_COUNT, ctypes.c_long, ctypes.byref(count))
        for i in range(count.value):
            disp = ctypes.c_void_p()
            if _call(sw, _SW_ITEM, ctypes.c_long, VARIANT(vt=VT_I4, value=i),
                     ctypes.byref(disp)) == 0 and disp.value:
                disps.append(disp)
        # a área de trabalho não está na lista: FindWindowSW(SWC_DESKTOP)
        hwnd, disp = ctypes.c_long(), ctypes.c_void_p()
        empty = VARIANT(vt=VT_EMPTY)
        if _call(sw, _SW_FINDWINDOW, ctypes.c_long, ctypes.byref(empty),
                 ctypes.byref(empty), ctypes.c_int(SWC_DESKTOP),
                 ctypes.byref(hwnd), ctypes.c_int(SWFO_NEEDDISPATCH),
                 ctypes.byref(disp)) == 0 and disp.value:
            disps.append(disp)
    finally:
        _release(sw)
    out = []
    for disp in disps:
        try:
            sp = _qi(disp, IID_IServiceProvider)
            if not sp:
                continue
            sb = ctypes.c_void_p()
            hr = _call(sp, _SP_QUERYSERVICE, ctypes.c_long,
                       ctypes.byref(SID_STopLevelBrowser),
                       ctypes.byref(IID_IShellBrowser), ctypes.byref(sb))
            _release(sp)
            if hr != 0 or not sb.value:
                continue
            hwnd = W.HWND()
            _call(sb, _OW_GETWINDOW, ctypes.c_long, ctypes.byref(hwnd))
            out.append((hwnd.value or 0, sb))
        finally:
            _release(disp)
    return out


def _items(sb, flags: int) -> list[Path]:
    """Itens da vista ativa do IShellBrowser `sb`, na ordem da tela."""
    view = ctypes.c_void_p()
    if _call(sb, _SB_QUERYACTIVESHELLVIEW, ctypes.c_long,
             ctypes.byref(view)) != 0 or not view.value:
        return []
    paths: list[Path] = []
    fv = _qi(view, IID_IFolderView)
    _release(view)
    if not fv:
        return []
    arr = ctypes.c_void_p()
    try:
        if _call(fv, _FV_ITEMS, ctypes.c_long,
                 ctypes.c_uint(flags | SVGIO_FLAG_VIEWORDER),
                 ctypes.byref(IID_IShellItemArray), ctypes.byref(arr)) != 0 \
                or not arr.value:
            return []
        n = ctypes.c_ulong()
        _call(arr, _SIA_COUNT, ctypes.c_long, ctypes.byref(n))
        for i in range(n.value):
            item = ctypes.c_void_p()
            if _call(arr, _SIA_ITEMAT, ctypes.c_long, ctypes.c_ulong(i),
                     ctypes.byref(item)) != 0 or not item.value:
                continue
            name = ctypes.c_wchar_p()
            if _call(item, _SI_DISPLAYNAME, ctypes.c_long,
                     ctypes.c_int(SIGDN_FILESYSPATH - 2**32),
                     ctypes.byref(name)) == 0 and name.value:
                paths.append(Path(name.value))
                ole32.CoTaskMemFree(name)
            _release(item)
    finally:
        _release(arr)
        _release(fv)
    return paths


def _key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def view_order(paths: list[Path]) -> list[Path] | None:
    """Os caminhos na ordem da janela do Explorer que mostra todos eles, ou
    None se nenhuma mostra (arraste de outro app, pasta já fechada)."""
    want = {_key(p): p for p in paths}
    try:
        with _Com():
            browsers = _browsers()
            try:
                for _hwnd, sb in browsers:
                    shown = [_key(p) for p in _items(sb, SVGIO_ALLVIEW)]
                    if want.keys() <= set(shown):
                        pos = {k: i for i, k in enumerate(shown)}
                        return sorted(paths, key=lambda p: pos[_key(p)])
            finally:
                for _hwnd, sb in browsers:
                    _release(sb)
    except OSError as exc:
        log.info("ordem do Explorer indisponível: %s", exc)
    return None


DESKTOP_CLASSES = ("Progman", "WorkerW")


def selection_at(hwnd: int) -> list[Path]:
    """Os itens selecionados na janela `hwnd` (Explorer ou área de
    trabalho, qualquer janela filha serve), na ordem da tela."""
    from . import win32 as W
    root = W.root_window(hwnd)
    desktop = W.class_name(root) in DESKTOP_CLASSES
    try:
        with _Com():
            browsers = _browsers()
            try:
                for top, sb in browsers:
                    top = W.root_window(top)
                    if top == root or (desktop and W.class_name(top)
                                       in DESKTOP_CLASSES):
                        return _items(sb, SVGIO_SELECTION)
            finally:
                for _top, sb in browsers:
                    _release(sb)
    except OSError as exc:
        log.info("seleção do Explorer indisponível: %s", exc)
    return []


def natural_key(path: Path):
    """Como o Explorer ordena por nome: 'R0-2' antes de 'R0-10' e o nome
    sem a extensão primeiro ('R0.pdf' antes de 'R0-1.pdf')."""
    import re

    def parts(text: str):
        return [(0, int(t), "") if t.isdigit() else (1, 0, t.casefold())
                for t in re.split(r"(\d+)", text) if t]
    return parts(path.stem), path.suffix.casefold()


__all__ = ["view_order", "selection_at", "natural_key"]
