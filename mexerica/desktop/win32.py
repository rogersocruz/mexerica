"""Chamadas Win32 (ctypes) do backend do Windows.

Só a API do sistema, sem regra do app: ler mouse e teclado, achar a
imagem de arraste do shell, posicionar janelas, vidro do DWM, foco,
clipboard e "mostrar na pasta". Coordenadas em pixels físicos (o GTK
deixa o processo ciente do DPI de cada monitor).
"""
from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes as W
from pathlib import Path

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32")
ole32 = ctypes.WinDLL("ole32")
dwmapi = ctypes.WinDLL("dwmapi")


def _fn(dll, name, restype, *argtypes):
    f = getattr(dll, name, None)
    if f is not None:
        f.restype = restype
        f.argtypes = argtypes
    return f


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", W.DWORD), ("rcMonitor", W.RECT),
                ("rcWork", W.RECT), ("dwFlags", W.DWORD)]


class ACCENTPOLICY(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


class WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p),
                ("SizeOfData", ctypes.c_size_t)]


WNDENUMPROC = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

GetAsyncKeyState = _fn(user32, "GetAsyncKeyState", ctypes.c_short, ctypes.c_int)
GetSystemMetrics = _fn(user32, "GetSystemMetrics", ctypes.c_int, ctypes.c_int)
GetCursorPos = _fn(user32, "GetCursorPos", W.BOOL, ctypes.POINTER(W.POINT))
FindWindowW = _fn(user32, "FindWindowW", W.HWND, W.LPCWSTR, W.LPCWSTR)
IsWindowVisible = _fn(user32, "IsWindowVisible", W.BOOL, W.HWND)
MonitorFromPoint = _fn(user32, "MonitorFromPoint", W.HMONITOR, W.POINT,
                       W.DWORD)
GetMonitorInfoW = _fn(user32, "GetMonitorInfoW", W.BOOL, W.HMONITOR,
                      ctypes.POINTER(MONITORINFO))
SetWindowPos = _fn(user32, "SetWindowPos", W.BOOL, W.HWND, W.HWND,
                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                   W.UINT)
GetWindowRect = _fn(user32, "GetWindowRect", W.BOOL, W.HWND,
                    ctypes.POINTER(W.RECT))
GetWindowLongPtrW = _fn(user32, "GetWindowLongPtrW", ctypes.c_ssize_t,
                        W.HWND, ctypes.c_int)
SetWindowLongPtrW = _fn(user32, "SetWindowLongPtrW", ctypes.c_ssize_t,
                        W.HWND, ctypes.c_int, ctypes.c_ssize_t)
GetForegroundWindow = _fn(user32, "GetForegroundWindow", W.HWND)
SetForegroundWindow = _fn(user32, "SetForegroundWindow", W.BOOL, W.HWND)
BringWindowToTop = _fn(user32, "BringWindowToTop", W.BOOL, W.HWND)
AllowSetForegroundWindow = _fn(user32, "AllowSetForegroundWindow", W.BOOL,
                               W.DWORD)
GetWindowThreadProcessId = _fn(user32, "GetWindowThreadProcessId", W.DWORD,
                               W.HWND, ctypes.POINTER(W.DWORD))
AttachThreadInput = _fn(user32, "AttachThreadInput", W.BOOL, W.DWORD,
                        W.DWORD, W.BOOL)
GetCurrentThreadId = _fn(kernel32, "GetCurrentThreadId", W.DWORD)
CreateMutexW = _fn(kernel32, "CreateMutexW", W.HANDLE, ctypes.c_void_p,
                   W.BOOL, W.LPCWSTR)
EnumWindows = _fn(user32, "EnumWindows", W.BOOL, WNDENUMPROC, W.LPARAM)
GetWindowTextW = _fn(user32, "GetWindowTextW", ctypes.c_int, W.HWND,
                     W.LPWSTR, ctypes.c_int)
# não documentada, mas é o que dá o borrão atrás de janelas comuns
SetWindowCompositionAttribute = _fn(user32, "SetWindowCompositionAttribute",
                                    W.BOOL, W.HWND,
                                    ctypes.POINTER(WINCOMPATTRDATA))
DwmSetWindowAttribute = _fn(dwmapi, "DwmSetWindowAttribute", ctypes.c_long,
                            W.HWND, W.DWORD, ctypes.c_void_p, W.DWORD)
OpenClipboard = _fn(user32, "OpenClipboard", W.BOOL, W.HWND)
EmptyClipboard = _fn(user32, "EmptyClipboard", W.BOOL)
SetClipboardData = _fn(user32, "SetClipboardData", W.HANDLE, W.UINT,
                       W.HANDLE)
CloseClipboard = _fn(user32, "CloseClipboard", W.BOOL)
GlobalAlloc = _fn(kernel32, "GlobalAlloc", W.HGLOBAL, W.UINT, ctypes.c_size_t)
GlobalLock = _fn(kernel32, "GlobalLock", ctypes.c_void_p, W.HGLOBAL)
GlobalUnlock = _fn(kernel32, "GlobalUnlock", W.BOOL, W.HGLOBAL)
GlobalFree = _fn(kernel32, "GlobalFree", W.HGLOBAL, W.HGLOBAL)
CoInitializeEx = _fn(ole32, "CoInitializeEx", ctypes.c_long, ctypes.c_void_p,
                     W.DWORD)
ILCreateFromPathW = _fn(shell32, "ILCreateFromPathW", ctypes.c_void_p,
                        W.LPCWSTR)
ILFree = _fn(shell32, "ILFree", None, ctypes.c_void_p)
SHOpenFolderAndSelectItems = _fn(shell32, "SHOpenFolderAndSelectItems",
                                 ctypes.c_long, ctypes.c_void_p, W.UINT,
                                 ctypes.POINTER(ctypes.c_void_p), W.DWORD)

VK_LBUTTON, VK_RBUTTON = 0x01, 0x02
VK_SHIFT, VK_CONTROL, VK_MENU = 0x10, 0x11, 0x12
SM_SWAPBUTTON = 23
MONITOR_DEFAULTTONEAREST = 2
HWND_TOPMOST = W.HWND(-1)
SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER = 0x1, 0x2, 0x4
SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x10, 0x20
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x80            # sem botão na barra de tarefas
WS_EX_NOACTIVATE = 0x08000000      # clicar não rouba o foco
WS_EX_APPWINDOW = 0x40000
ASFW_ANY = 0xFFFFFFFF
WCA_ACCENT_POLICY = 19
ACCENT_ENABLE_BLURBEHIND = 3
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_BORDER_COLOR = 34
DWMWCP_DONOTROUND, DWMWCP_ROUND = 1, 2
DWMWA_COLOR_NONE = 0xFFFFFFFE
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x2
COINIT_APARTMENTTHREADED = 0x2
ERROR_ALREADY_EXISTS = 183

# Janela da imagem que acompanha o ponteiro num arraste do shell (Explorer,
# área de trabalho, diálogos de arquivo). Só existe durante um arraste.
DRAG_IMAGE_CLASS = "SysDragImage"

Rect = tuple[int, int, int, int]      # left, top, right, bottom

_instance = None


def claim_instance(name: str) -> bool:
    """False se outro processo da sessão já é `name` (vale até sair)."""
    global _instance
    ctypes.set_last_error(0)
    _instance = CreateMutexW(None, False, f"Local\\{name}")
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS

# --------------------------------------------------------------------------
# Mouse e teclado
# --------------------------------------------------------------------------


def _down(vk: int) -> bool:
    return bool(GetAsyncKeyState(vk) & 0x8000)


def primary_button_down() -> bool:
    """Botão principal pressionado (respeita mouse de canhoto)."""
    return _down(VK_RBUTTON if GetSystemMetrics(SM_SWAPBUTTON) else VK_LBUTTON)


def modifiers() -> tuple[bool, bool, bool]:
    """(Shift, Alt, Ctrl), lidos do teclado físico, com o foco em qualquer app."""
    return _down(VK_SHIFT), _down(VK_MENU), _down(VK_CONTROL)


def pointer() -> tuple[int, int]:
    pt = W.POINT()
    GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def drag_image() -> int:
    """HWND da imagem de arraste do shell, se houver um arraste agora."""
    hwnd = FindWindowW(DRAG_IMAGE_CLASS, None)
    return hwnd if hwnd and IsWindowVisible(hwnd) else 0

# --------------------------------------------------------------------------
# Monitores e janelas
# --------------------------------------------------------------------------


def _rect(r: W.RECT) -> Rect:
    return r.left, r.top, r.right, r.bottom


def monitor_at(point: tuple[int, int]) -> tuple[Rect, Rect]:
    """(monitor inteiro, área útil sem a barra de tarefas) sob o ponto."""
    mon = MonitorFromPoint(W.POINT(*point), MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    GetMonitorInfoW(mon, ctypes.byref(info))
    return _rect(info.rcMonitor), _rect(info.rcWork)


def window_rect(hwnd: int) -> Rect:
    r = W.RECT()
    GetWindowRect(hwnd, ctypes.byref(r))
    return _rect(r)


def load_gdk_win32() -> None:
    """Carrega o GdkWin32 antes das janelas existirem, para o PyGObject
    embrulhar as superfícies com o tipo certo (Win32Surface)."""
    try:
        import gi
        gi.require_version("GdkWin32", "4.0")
        from gi.repository import GdkWin32  # noqa: F401
    except (ImportError, ValueError):
        pass


def hwnd_of(win) -> int:
    """HWND de uma Gtk.Window (realiza a janela se preciso)."""
    surface = win.get_surface()
    if surface is None:
        win.realize()
        surface = win.get_surface()
    cached = getattr(win, "_mx_hwnd", None)
    if cached and cached[0] is surface:
        return cached[1]
    hwnd = _gdk_handle(surface) or _hwnd_by_title(win)
    win._mx_hwnd = (surface, hwnd)
    return hwnd


def _gdk_handle(surface) -> int:
    try:
        from gi.repository import GdkWin32
        return int(GdkWin32.Win32Surface.get_handle(surface) or 0)
    except (ImportError, AttributeError, TypeError, ValueError):
        return 0


def _hwnd_by_title(win) -> int:
    """Sem o GdkWin32 no PyGObject: dá um título único à janela e procura
    entre as janelas deste processo."""
    title = win.get_title() or ""
    probe = f"mexerica-{id(win):x}"
    win.set_title(probe)
    try:
        return find_window(probe)
    finally:
        win.set_title(title)


def find_window(title: str) -> int:
    pid, found = os.getpid(), []
    buf = ctypes.create_unicode_buffer(256)

    @WNDENUMPROC
    def each(hwnd, _lparam):
        owner = W.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            GetWindowTextW(hwnd, buf, len(buf))
            if buf.value == title:
                found.append(hwnd)
                return False
        return True
    EnumWindows(each, 0)
    return found[0] if found else 0


def add_ex_style(hwnd: int, bits: int, remove: int = 0) -> None:
    cur = GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    new = (cur | bits) & ~remove
    if new != cur:
        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new)
        SetWindowPos(hwnd, None, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE
                     | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)


def place(hwnd: int, rect: Rect) -> None:
    """Cobre `rect` e fica acima de todas as janelas, sem tomar o foco."""
    left, top, right, bottom = rect
    SetWindowPos(hwnd, HWND_TOPMOST, left, top, right - left, bottom - top,
                 SWP_NOACTIVATE)


def move(hwnd: int, x: int, y: int) -> None:
    SetWindowPos(hwnd, HWND_TOPMOST, x, y, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)


def set_topmost(hwnd: int) -> None:
    SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def place_below(hwnd: int, above: int) -> None:
    """Põe `hwnd` logo abaixo de `above` (as duas ficam acima de tudo)."""
    SetWindowPos(hwnd, above, 0, 0, 0, 0,
                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def _dwm_uint(hwnd: int, attr: int, value: int) -> None:
    v = ctypes.c_uint(value)
    DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))


def set_glass(hwnd: int, rounded: bool) -> None:
    """Vidro: o DWM borra o que está atrás da janela (no GNOME é a extensão
    que faz isso). A janela GTK já é translúcida, então o borrão aparece
    através dela. Com cantos, o DWM arredonda a janela (8 px, Windows 11)
    e corta o borrão junto."""
    if SetWindowCompositionAttribute is not None:
        accent = ACCENTPOLICY(ACCENT_ENABLE_BLURBEHIND, 0, 0, 0)
        data = WINCOMPATTRDATA(WCA_ACCENT_POLICY,
                               ctypes.cast(ctypes.pointer(accent),
                                           ctypes.c_void_p),
                               ctypes.sizeof(accent))
        SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    # no Windows 10 estes dois só devolvem erro, sem efeito
    _dwm_uint(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
              DWMWCP_ROUND if rounded else DWMWCP_DONOTROUND)
    _dwm_uint(hwnd, DWMWA_BORDER_COLOR, DWMWA_COLOR_NONE)

# --------------------------------------------------------------------------
# Foco
# --------------------------------------------------------------------------


def bring_to_front(hwnd: int) -> None:
    """Traz a janela para a frente com o foco em outro app (Explorer, logo
    depois do drop). O Windows só deixa o dono da janela ativa escolher a
    próxima, então a fila de entrada dele é emprestada por um instante."""
    fg = GetForegroundWindow()
    me = GetCurrentThreadId()
    other = GetWindowThreadProcessId(fg, None) if fg else 0
    attached = bool(other and other != me and AttachThreadInput(other, me,
                                                                True))
    try:
        BringWindowToTop(hwnd)
        SetForegroundWindow(hwnd)
    finally:
        if attached:
            AttachThreadInput(other, me, False)


def allow_foreground() -> None:
    """Deixa o app que vamos abrir (Explorer, terminal) vir para a frente."""
    AllowSetForegroundWindow(ASFW_ANY)

# --------------------------------------------------------------------------
# Clipboard e Explorer
# --------------------------------------------------------------------------


def set_clipboard(text: str) -> bool:
    data = (text + "\0").encode("utf-16-le")
    for _ in range(10):             # outro app pode estar com ele aberto
        if OpenClipboard(None):
            break
        time.sleep(0.02)
    else:
        return False
    try:
        EmptyClipboard()
        handle = GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            return False
        ctypes.memmove(GlobalLock(handle), data, len(data))
        GlobalUnlock(handle)
        if not SetClipboardData(CF_UNICODETEXT, handle):
            GlobalFree(handle)
            return False
        return True
    finally:
        CloseClipboard()


def reveal(paths: list[Path]) -> bool:
    """Abre o Explorer com os itens selecionados (uma janela por pasta)."""
    CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    groups: dict[Path, list[Path]] = {}
    for p in paths:
        groups.setdefault(p.parent, []).append(p)
    ok = True
    for folder, items in groups.items():
        pidls = [ILCreateFromPathW(str(folder))]
        pidls += [ILCreateFromPathW(str(p)) for p in items]
        try:
            if not all(pidls):
                ok = False
                continue
            arr = (ctypes.c_void_p * len(items))(*pidls[1:])
            ok &= SHOpenFolderAndSelectItems(pidls[0], len(items), arr, 0) >= 0
        finally:
            for pidl in pidls:
                if pidl:
                    ILFree(pidl)
    return ok
