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


class GUID(ctypes.Structure):
    _fields_ = [("Data1", W.DWORD), ("Data2", W.WORD), ("Data3", W.WORD),
                ("Data4", ctypes.c_ubyte * 8)]


IID_IDataObject = GUID(0x0000010E, 0, 0,
                       (ctypes.c_ubyte * 8)(0xC0, 0, 0, 0, 0, 0, 0, 0x46))
IID_IShellItemImageFactory = GUID(
    0xBCC18B79, 0xBA16, 0x442F,
    (ctypes.c_ubyte * 8)(0x80, 0xC4, 0x8A, 0x59, 0xC3, 0x0C, 0x46, 0x3B))

WNDENUMPROC = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, W.HWND, W.UINT, W.WPARAM,
                             W.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", W.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", W.HINSTANCE), ("hIcon", W.HICON),
                ("hCursor", W.HANDLE), ("hbrBackground", W.HBRUSH),
                ("lpszMenuName", W.LPCWSTR), ("lpszClassName", W.LPCWSTR)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", W.DWORD), ("hWnd", W.HWND), ("uID", W.UINT),
                ("uFlags", W.UINT), ("uCallbackMessage", W.UINT),
                ("hIcon", W.HICON), ("szTip", W.WCHAR * 128),
                ("dwState", W.DWORD), ("dwStateMask", W.DWORD),
                ("szInfo", W.WCHAR * 256), ("uVersion", W.UINT),
                ("szInfoTitle", W.WCHAR * 64), ("dwInfoFlags", W.DWORD),
                ("guidItem", GUID), ("hBalloonIcon", W.HICON)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class BITMAP(ctypes.Structure):
    _fields_ = [("bmType", ctypes.c_long), ("bmWidth", ctypes.c_long),
                ("bmHeight", ctypes.c_long), ("bmWidthBytes", ctypes.c_long),
                ("bmPlanes", W.WORD), ("bmBitsPixel", W.WORD),
                ("bmBits", ctypes.c_void_p)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", W.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", W.WORD),
                ("biBitCount", W.WORD), ("biCompression", W.DWORD),
                ("biSizeImage", W.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", W.DWORD),
                ("biClrImportant", W.DWORD)]


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [("hIcon", W.HICON), ("iIcon", ctypes.c_int),
                ("dwAttributes", W.DWORD), ("szDisplayName", W.WCHAR * 260),
                ("szTypeName", W.WCHAR * 80)]

GetAsyncKeyState = _fn(user32, "GetAsyncKeyState", ctypes.c_short, ctypes.c_int)
GetSystemMetrics = _fn(user32, "GetSystemMetrics", ctypes.c_int, ctypes.c_int)
GetCursorPos = _fn(user32, "GetCursorPos", W.BOOL, ctypes.POINTER(W.POINT))
FindWindowExW = _fn(user32, "FindWindowExW", W.HWND, W.HWND, W.HWND,
                    W.LPCWSTR, W.LPCWSTR)
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
ILFindLastID = _fn(shell32, "ILFindLastID", ctypes.c_void_p, ctypes.c_void_p)
OleInitialize = _fn(ole32, "OleInitialize", ctypes.c_long, ctypes.c_void_p)
SHCreateDataObject = _fn(shell32, "SHCreateDataObject", ctypes.c_long,
                         ctypes.c_void_p, W.UINT,
                         ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
                         ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))
SHDoDragDrop = _fn(shell32, "SHDoDragDrop", ctypes.c_long, W.HWND,
                   ctypes.c_void_p, ctypes.c_void_p, W.DWORD,
                   ctypes.POINTER(W.DWORD))
SHCreateItemFromParsingName = _fn(shell32, "SHCreateItemFromParsingName",
                                  ctypes.c_long, W.LPCWSTR, ctypes.c_void_p,
                                  ctypes.POINTER(GUID),
                                  ctypes.POINTER(ctypes.c_void_p))
SHGetFileInfoW = _fn(shell32, "SHGetFileInfoW", ctypes.c_size_t, W.LPCWSTR,
                     W.DWORD, ctypes.POINTER(SHFILEINFOW), W.UINT, W.UINT)
Shell_NotifyIconW = _fn(shell32, "Shell_NotifyIconW", W.BOOL, W.DWORD,
                        ctypes.POINTER(NOTIFYICONDATAW))
gdi32 = ctypes.WinDLL("gdi32")
GetObjectW = _fn(gdi32, "GetObjectW", ctypes.c_int, W.HANDLE, ctypes.c_int,
                 ctypes.c_void_p)
GetDIBits = _fn(gdi32, "GetDIBits", ctypes.c_int, W.HDC, W.HBITMAP, W.UINT,
                W.UINT, ctypes.c_void_p, ctypes.POINTER(BITMAPINFOHEADER),
                W.UINT)
DeleteObject = _fn(gdi32, "DeleteObject", W.BOOL, W.HANDLE)
GetDC = _fn(user32, "GetDC", W.HDC, W.HWND)
ReleaseDC = _fn(user32, "ReleaseDC", ctypes.c_int, W.HWND, W.HDC)
GetModuleHandleW = _fn(kernel32, "GetModuleHandleW", W.HMODULE, W.LPCWSTR)
RegisterClassW = _fn(user32, "RegisterClassW", W.ATOM,
                     ctypes.POINTER(WNDCLASSW))
CreateWindowExW = _fn(user32, "CreateWindowExW", W.HWND, W.DWORD, W.LPCWSTR,
                      W.LPCWSTR, W.DWORD, ctypes.c_int, ctypes.c_int,
                      ctypes.c_int, ctypes.c_int, W.HWND, W.HMENU,
                      W.HINSTANCE, ctypes.c_void_p)
DestroyWindow = _fn(user32, "DestroyWindow", W.BOOL, W.HWND)
DefWindowProcW = _fn(user32, "DefWindowProcW", ctypes.c_ssize_t, W.HWND,
                     W.UINT, W.WPARAM, W.LPARAM)
RegisterWindowMessageW = _fn(user32, "RegisterWindowMessageW", W.UINT,
                             W.LPCWSTR)
LoadImageW = _fn(user32, "LoadImageW", W.HANDLE, W.HINSTANCE, W.LPCWSTR,
                 W.UINT, ctypes.c_int, ctypes.c_int, W.UINT)
DestroyIcon = _fn(user32, "DestroyIcon", W.BOOL, W.HICON)
CreatePopupMenu = _fn(user32, "CreatePopupMenu", W.HMENU)
AppendMenuW = _fn(user32, "AppendMenuW", W.BOOL, W.HMENU, W.UINT,
                  ctypes.c_size_t, W.LPCWSTR)
TrackPopupMenu = _fn(user32, "TrackPopupMenu", ctypes.c_int, W.HMENU, W.UINT,
                     ctypes.c_int, ctypes.c_int, ctypes.c_int, W.HWND,
                     ctypes.c_void_p)
DestroyMenu = _fn(user32, "DestroyMenu", W.BOOL, W.HMENU)
PostMessageW = _fn(user32, "PostMessageW", W.BOOL, W.HWND, W.UINT, W.WPARAM,
                   W.LPARAM)
SendMessageTimeoutW = _fn(user32, "SendMessageTimeoutW", W.LPARAM, W.HWND,
                          W.UINT, W.WPARAM, W.LPARAM, W.UINT, W.UINT,
                          ctypes.POINTER(ctypes.c_size_t))
SHGetKnownFolderPath = _fn(shell32, "SHGetKnownFolderPath", ctypes.c_long,
                           ctypes.POINTER(GUID), W.DWORD, W.HANDLE,
                           ctypes.POINTER(ctypes.c_wchar_p))
CoTaskMemFree = _fn(ole32, "CoTaskMemFree", None, ctypes.c_void_p)
FOLDERID_Startup = GUID(0xB97D20BB, 0xF46A, 0x4C97,
                        (ctypes.c_ubyte * 8)(0xBA, 0x10, 0x5E, 0x36, 0x08, 0x43,
                                             0x08, 0x54))

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
DROPEFFECT_COPY, DROPEFFECT_MOVE = 1, 2
WM_NULL, WM_CLOSE, WM_CONTEXTMENU = 0x0000, 0x0010, 0x007B
WM_LBUTTONUP, WM_RBUTTONUP, WM_APP = 0x0202, 0x0205, 0x8000
NIM_ADD, NIM_DELETE = 0, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x1, 0x2, 0x4
IMAGE_ICON, LR_LOADFROMFILE = 1, 0x10
SM_CXSMICON, SM_CYSMICON = 49, 50
MF_STRING, MF_SEPARATOR = 0x0, 0x800
TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x2, 0x100
SHGFI_DISPLAYNAME = 0x200
TRAY_CLASS = "MexericaTray"         # o instalador acha a janela por aqui

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
    """HWND da imagem de arraste do shell, se houver uma visível agora
    (pode sobrar uma escondida de um arraste anterior)."""
    hwnd = None
    while True:
        hwnd = FindWindowExW(None, hwnd, DRAG_IMAGE_CLASS, None)
        if not hwnd or IsWindowVisible(hwnd):
            return hwnd or 0

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


def plain_frame(hwnd: int) -> None:
    """Sem cantos nem borda do DWM: a janela desenha a própria forma (a
    bolha da Flutuar)."""
    _dwm_uint(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_DONOTROUND)
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


def com_release(ptr: int) -> None:
    """IUnknown::Release (terceira entrada da vtable)."""
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
    ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl.contents[2])(ptr)


_DESKTOP = (ctypes.c_ubyte * 2)()      # IDLIST vazia: a raiz do shell


def file_data_object(paths: list[Path]) -> int:
    """IDataObject do shell para os arquivos, o mesmo que o Explorer arrasta
    (CF_HDROP, lista de itens e miniatura). Quem chama faz o com_release."""
    pidls = [ILCreateFromPathW(str(p)) for p in paths]
    parents = {str(Path(p).parent).lower() for p in paths}
    # mesma pasta: pasta + itens dela; pastas diferentes: tudo a partir da raiz
    folder = ILCreateFromPathW(str(Path(paths[0]).parent)) \
        if len(parents) == 1 else None
    try:
        if not all(pidls) or (len(parents) == 1 and not folder):
            raise OSError("caminho fora do shell: " + str(paths[0]))
        items = [ILFindLastID(p) for p in pidls] if folder else pidls
        arr = (ctypes.c_void_p * len(items))(*items)
        obj = ctypes.c_void_p()
        hr = SHCreateDataObject(folder or ctypes.addressof(_DESKTOP),
                                len(items), arr, None,
                                ctypes.byref(IID_IDataObject),
                                ctypes.byref(obj))
        if hr < 0 or not obj.value:
            raise OSError(f"SHCreateDataObject falhou ({hr & 0xFFFFFFFF:#x})")
        return obj.value
    finally:
        for pidl in [*pidls, folder]:
            if pidl:
                ILFree(pidl)


def drag_files(hwnd: int, paths: list[Path]) -> int:
    """Arrasta os arquivos como o Explorer, a partir do botão já pressionado:
    miniatura do Windows, a barra de tarefas traz as janelas para a frente e
    qualquer app recebe. Bloqueia até o drop; devolve o efeito (0 se
    cancelou)."""
    OleInitialize(None)                 # o GTK já fez; aqui só confirma
    obj = file_data_object(paths)
    try:
        effect = W.DWORD(0)
        SHDoDragDrop(hwnd, obj, None, DROPEFFECT_COPY | DROPEFFECT_MOVE,
                     ctypes.byref(effect))
        return effect.value
    finally:
        com_release(obj)


def shell_image(path: Path, size: int) -> tuple[int, int, bytes] | None:
    """A imagem que o Explorer mostra para o arquivo: miniatura, se houver,
    senão o ícone (o de um atalho ou .exe é o do programa). Devolve largura,
    altura e pixels BGRA pré-multiplicados, de cima para baixo."""
    CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    factory = ctypes.c_void_p()
    if SHCreateItemFromParsingName(str(path), None,
                                   ctypes.byref(IID_IShellItemImageFactory),
                                   ctypes.byref(factory)) < 0:
        return None
    hbm = W.HBITMAP()
    try:
        vtbl = ctypes.cast(factory,
                           ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
        get_image = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, SIZE, ctypes.c_int,
            ctypes.POINTER(W.HBITMAP))(vtbl.contents[3])
        if get_image(factory, SIZE(size, size), 0, ctypes.byref(hbm)) < 0:
            return None
    finally:
        com_release(factory.value)
    if not hbm:
        return None
    try:
        bm = BITMAP()
        GetObjectW(hbm, ctypes.sizeof(bm), ctypes.byref(bm))
        w, h = bm.bmWidth, abs(bm.bmHeight)
        header = BITMAPINFOHEADER(biSize=ctypes.sizeof(BITMAPINFOHEADER),
                                  biWidth=w, biHeight=-h, biPlanes=1,
                                  biBitCount=32)
        buf = (ctypes.c_ubyte * (w * h * 4))()
        dc = GetDC(None)
        try:
            GetDIBits(dc, hbm, 0, h, buf, ctypes.byref(header), 0)
        finally:
            ReleaseDC(None, dc)
        data = bytearray(buf)
        if not any(data[3::4]):         # miniatura sem alfa (JPEG): opaca
            data[3::4] = b"\xff" * (w * h)
        return w, h, bytes(data)
    finally:
        DeleteObject(hbm)


def startup_folder() -> Path | None:
    """A pasta Inicializar do usuário (a política pode tê-la mudado de
    lugar; o instalador pergunta do mesmo jeito)."""
    out = ctypes.c_wchar_p()
    if SHGetKnownFolderPath(ctypes.byref(FOLDERID_Startup), 0, None,
                            ctypes.byref(out)) < 0:
        return None
    try:
        return Path(out.value)
    finally:
        CoTaskMemFree(out)


def display_name(path: Path) -> str:
    """O nome como o Explorer mostra (atalho sem .lnk, extensão escondida
    se o Explorer esconde)."""
    info = SHFILEINFOW()
    if SHGetFileInfoW(str(path), 0, ctypes.byref(info), ctypes.sizeof(info),
                      SHGFI_DISPLAYNAME) and info.szDisplayName:
        return info.szDisplayName
    return Path(path).name


class COPYDATASTRUCT(ctypes.Structure):
    _fields_ = [("dwData", ctypes.c_size_t), ("cbData", W.DWORD),
                ("lpData", ctypes.c_void_p)]


WM_COPYDATA = 0x004A
SMTO_ABORTIFHUNG = 0x0002
COPY_FILES = 0x4D58         # "MX": identifica a lista de arquivos


def send_files(hwnd, paths: list[str]) -> bool:
    """Manda caminhos para a janela da bandeja de outro processo (o
    "Converter com a Mexerica" sem o D-Bus do GLib)."""
    raw = "\n".join(paths).encode("utf-16-le")
    buf = ctypes.create_string_buffer(raw, len(raw))
    data = COPYDATASTRUCT(COPY_FILES, len(raw),
                          ctypes.cast(buf, ctypes.c_void_p))
    result = ctypes.c_size_t()
    return bool(SendMessageTimeoutW(hwnd, WM_COPYDATA, 0,
                                    ctypes.addressof(data), SMTO_ABORTIFHUNG,
                                    5000, ctypes.byref(result)))


class Tray:
    """Ícone na área de notificação, perto do relógio. Clique abre `on_open`;
    o botão direito abre o menu (rótulo, função; None é um separador). Vive
    numa janela invisível da thread principal: o laço do GTK entrega as
    mensagens dela. WM_CLOSE nessa janela (o instalador manda) chama
    `on_close`; uma lista de arquivos de outra instância (send_files) chama
    `on_files`."""

    CALLBACK = WM_APP + 1
    OPEN = WM_APP + 2       # outra instância pede para abrir (sem D-Bus)

    # A classe da janela é registrada uma vez por processo, com um _proc só
    # que entrega cada mensagem à Tray daquela janela (por hwnd): com o
    # _wndproc de uma Tray na classe, uma segunda Tray receberia as
    # mensagens pela primeira, já removida.
    _live: dict = {}
    _proc = None

    def __init__(self, icon: Path, tip: str, on_open, menu, on_close,
                 on_files=None):
        self._on_open, self._menu, self._on_close = on_open, menu, on_close
        self._on_files = on_files
        self._recreated = RegisterWindowMessageW("TaskbarCreated")
        instance = GetModuleHandleW(None)
        if Tray._proc is None:
            Tray._proc = WNDPROC(Tray._dispatch)    # vivo enquanto o processo
            RegisterClassW(ctypes.byref(WNDCLASSW(lpfnWndProc=Tray._proc,
                                                  hInstance=instance,
                                                  lpszClassName=TRAY_CLASS)))
        self.hwnd = CreateWindowExW(0, TRAY_CLASS, "Mexerica", 0, 0, 0, 0, 0,
                                    None, None, instance, None)
        Tray._live[self.hwnd] = self
        self._icon = LoadImageW(None, str(icon), IMAGE_ICON,
                                GetSystemMetrics(SM_CXSMICON),
                                GetSystemMetrics(SM_CYSMICON), LR_LOADFROMFILE)
        self._data = NOTIFYICONDATAW(
            cbSize=ctypes.sizeof(NOTIFYICONDATAW), hWnd=self.hwnd, uID=1,
            uFlags=NIF_MESSAGE | NIF_ICON | NIF_TIP,
            uCallbackMessage=self.CALLBACK, hIcon=self._icon, szTip=tip[:127])
        self.shown = bool(Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._data)))

    def remove(self) -> None:
        Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._data))
        DestroyWindow(self.hwnd)
        Tray._live.pop(self.hwnd, None)
        if self._icon:
            DestroyIcon(self._icon)

    @staticmethod
    def _dispatch(hwnd, msg, wparam, lparam):
        # (as mensagens da criação chegam antes de a janela ter dono)
        tray = Tray._live.get(hwnd)
        if tray is None:
            return DefWindowProcW(hwnd, msg, wparam, lparam)
        return tray._wndproc(hwnd, msg, wparam, lparam)

    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == self.CALLBACK:
                event = lparam & 0xFFFF
                if event == WM_LBUTTONUP:
                    self._on_open()
                elif event in (WM_RBUTTONUP, WM_CONTEXTMENU):
                    self._popup()
                return 0
            if msg == self.OPEN:
                self._on_open()
                return 0
            if msg == WM_COPYDATA and self._on_files:
                data = ctypes.cast(lparam,
                                   ctypes.POINTER(COPYDATASTRUCT)).contents
                if data.dwData != COPY_FILES:
                    return 0
                text = ctypes.wstring_at(data.lpData, data.cbData // 2)
                self._on_files([Path(p) for p in text.split("\n") if p])
                return 1
            if msg == self._recreated:      # o Explorer reiniciou
                self.shown = bool(Shell_NotifyIconW(NIM_ADD,
                                                    ctypes.byref(self._data)))
                return 0
            if msg == WM_CLOSE:
                self._on_close()
                return 0
        except Exception:  # noqa: BLE001 - erro aqui sumiria calado
            import logging
            logging.getLogger("mexerica").exception("bandeja")
        return DefWindowProcW(hwnd, msg, wparam, lparam)

    def _popup(self) -> None:
        menu = CreatePopupMenu()
        for i, item in enumerate(self._menu, start=1):
            if item is None:
                AppendMenuW(menu, MF_SEPARATOR, 0, None)
            else:
                AppendMenuW(menu, MF_STRING, i, item[0])
        x, y = pointer()
        # sem isso o menu não fecha ao clicar fora (comportamento do Windows)
        SetForegroundWindow(self.hwnd)
        chosen = TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD, x, y,
                                0, self.hwnd, None)
        PostMessageW(self.hwnd, WM_NULL, 0, 0)
        DestroyMenu(menu)
        if chosen:
            self._menu[chosen - 1][1]()


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
