"""Windows: um executável com o nome e o ícone da Mexerica.

O serviço roda no Python do MSYS2, e o Gerenciador de Tarefas mostra a
descrição gravada no executável: "Python". O install.ps1 cria aqui uma
cópia do pythonw.exe, na mesma pasta dele (para achar as DLLs e a
biblioteca padrão), com outros recursos:

  versão   FileDescription e ProductName "Mexerica" (o nome que o
           Gerenciador de Tarefas mostra), a versão da Mexerica
  ícone    o da Mexerica (o da lista de processos e da barra de tarefas)

Só esses recursos mudam; o manifesto e o resto do pythonw ficam.

    python -m mexerica.desktop.branding <pythonw.exe> <destino.exe> <ícone.ico>
"""
from __future__ import annotations

import ctypes
import shutil
import struct
import sys
from ctypes import wintypes as W
from pathlib import Path

RT_ICON, RT_GROUP_ICON, RT_VERSION = 3, 14, 16
LANG_EN_US = 0x0409
LOAD_LIBRARY_AS_DATAFILE = 0x2
NAME = "Mexerica"


# --------------------------------------------------------------------------
# VS_VERSIONINFO
# --------------------------------------------------------------------------

def _pad(data: bytes) -> bytes:
    return data + b"\0" * (-len(data) % 4)


def _node(key: str, value: bytes = b"", text: bool = False,
          children: list[bytes] = ()) -> bytes:
    """Um bloco do recurso de versão: cabeçalho, chave, valor e filhos,
    cada parte alinhada em 4 bytes."""
    kind = 1 if text else 0
    body = _pad(struct.pack("<HHH", 0, 0, kind)
                + (key + "\0").encode("utf-16-le"))
    if value:
        body += value
    for child in children:
        body = _pad(body) + child
    vlen = len(value) // 2 if text else len(value)
    return struct.pack("<HHH", len(body), vlen, kind) + body[6:]


def _text(value: str) -> bytes:
    return (value + "\0").encode("utf-16-le")


def version_resource(version: str, filename: str) -> bytes:
    nums = [int(x) for x in version.split(".")[:4]]
    nums += [0] * (4 - len(nums))
    ms, ls = (nums[0] << 16) | nums[1], (nums[2] << 16) | nums[3]
    fixed = struct.pack("<13I", 0xFEEF04BD, 0x00010000, ms, ls, ms, ls,
                        0x3F, 0, 0x00040004, 1, 0, 0, 0)  # VOS_NT_WINDOWS32, app
    dotted = ".".join(map(str, nums))
    strings = [_node(k, _text(v), text=True) for k, v in (
        ("CompanyName", "Roger Cruz"),
        ("FileDescription", NAME),
        ("FileVersion", dotted),
        ("InternalName", Path(filename).stem),
        ("LegalCopyright", "© 2026 Roger Augusto Souza da Cruz"),
        ("OriginalFilename", filename),
        ("ProductName", NAME),
        ("ProductVersion", dotted))]
    table = _node("040904B0", text=True, children=strings)
    sfi = _node("StringFileInfo", text=True, children=[table])
    vfi = _node("VarFileInfo", text=True, children=[
        _node("Translation", struct.pack("<HH", LANG_EN_US, 1200))])
    return _node("VS_VERSION_INFO", fixed, children=[sfi, vfi])


# --------------------------------------------------------------------------
# Ícone
# --------------------------------------------------------------------------

def icon_resources(ico: bytes, first_id: int = 1) -> tuple[list[tuple[int,
                                                                      bytes]],
                                                           bytes]:
    """De um .ico: as imagens (RT_ICON, com ids a partir de first_id) e o
    diretório (RT_GROUP_ICON)."""
    _reserved, kind, count = struct.unpack_from("<HHH", ico, 0)
    if kind != 1 or not count:
        raise ValueError("não é um .ico")
    images, group = [], struct.pack("<HHH", 0, 1, count)
    for i in range(count):
        (w, h, colors, res, planes, bits, size,
         offset) = struct.unpack_from("<BBBBHHII", ico, 6 + 16 * i)
        rid = first_id + i
        images.append((rid, ico[offset:offset + size]))
        group += struct.pack("<BBBBHHIH", w, h, colors, res, planes, bits,
                             size, rid)
    return images, group


# --------------------------------------------------------------------------
# Gravar no .exe
# --------------------------------------------------------------------------

def _existing(path: Path, rtype: int) -> list[tuple[object, int]]:
    """(nome, idioma) dos recursos `rtype` que o executável já tem."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.LoadLibraryExW.restype = W.HMODULE
    k32.LoadLibraryExW.argtypes = [W.LPCWSTR, W.HANDLE, W.DWORD]
    mod = k32.LoadLibraryExW(str(path), None, LOAD_LIBRARY_AS_DATAFILE)
    if not mod:
        return []
    found: list[tuple[object, int]] = []
    NAMEPROC = ctypes.WINFUNCTYPE(W.BOOL, W.HMODULE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_void_p)
    LANGPROC = ctypes.WINFUNCTYPE(W.BOOL, W.HMODULE, ctypes.c_void_p,
                                  ctypes.c_void_p, W.WORD, ctypes.c_void_p)
    k32.EnumResourceNamesW.argtypes = [W.HMODULE, ctypes.c_void_p, NAMEPROC,
                                       ctypes.c_void_p]
    k32.EnumResourceLanguagesW.argtypes = [W.HMODULE, ctypes.c_void_p,
                                           ctypes.c_void_p, LANGPROC,
                                           ctypes.c_void_p]
    k32.FreeLibrary.argtypes = [W.HMODULE]
    names: list[object] = []

    def on_name(_m, _t, name, _p):
        # id numérico (< 0x10000) ou texto
        names.append(name if name < 0x10000 else
                     ctypes.wstring_at(name))
        return True

    def on_lang(_m, _t, _n, lang, _p):
        found.append((current[0], lang))
        return True
    name_cb, lang_cb = NAMEPROC(on_name), LANGPROC(on_lang)
    try:
        k32.EnumResourceNamesW(mod, ctypes.c_void_p(rtype), name_cb, None)
        current = [None]
        for name in names:
            current[0] = name
            arg = ctypes.c_void_p(name) if isinstance(name, int) else \
                ctypes.c_wchar_p(name)
            k32.EnumResourceLanguagesW(mod, ctypes.c_void_p(rtype), arg,
                                       lang_cb, None)
    finally:
        k32.FreeLibrary(mod)
    return found


def brand(src: Path, dst: Path, ico: Path, version: str) -> None:
    """Copia `src` para `dst` com a versão e o ícone da Mexerica."""
    tmp = dst.with_name(dst.name + ".tmp")
    shutil.copy2(src, tmp)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.BeginUpdateResourceW.restype = W.HANDLE
    k32.BeginUpdateResourceW.argtypes = [W.LPCWSTR, W.BOOL]
    k32.UpdateResourceW.restype = W.BOOL
    k32.UpdateResourceW.argtypes = [W.HANDLE, ctypes.c_void_p,
                                    ctypes.c_void_p, W.WORD,
                                    ctypes.c_void_p, W.DWORD]
    k32.EndUpdateResourceW.restype = W.BOOL
    k32.EndUpdateResourceW.argtypes = [W.HANDLE, W.BOOL]

    def name_arg(name):
        return ctypes.c_void_p(name) if isinstance(name, int) else \
            ctypes.cast(ctypes.c_wchar_p(name), ctypes.c_void_p)

    old = {t: _existing(tmp, t) for t in (RT_VERSION, RT_ICON, RT_GROUP_ICON)}
    handle = k32.BeginUpdateResourceW(str(tmp), False)
    if not handle:
        raise OSError(ctypes.get_last_error(), "BeginUpdateResource")
    try:
        for rtype, entries in old.items():      # tira versão e ícones antigos
            for name, lang in entries:
                if not k32.UpdateResourceW(handle, ctypes.c_void_p(rtype),
                                           name_arg(name), lang, None, 0):
                    raise OSError(ctypes.get_last_error(), "remover recurso")

        def put(rtype, rid, data):
            buf = ctypes.create_string_buffer(data, len(data))
            if not k32.UpdateResourceW(handle, ctypes.c_void_p(rtype),
                                       ctypes.c_void_p(rid), LANG_EN_US, buf,
                                       len(data)):
                raise OSError(ctypes.get_last_error(), "gravar recurso")
        put(RT_VERSION, 1, version_resource(version, dst.name))
        images, group = icon_resources(ico.read_bytes())
        for rid, data in images:
            put(RT_ICON, rid, data)
        put(RT_GROUP_ICON, 1, group)
    except Exception:
        k32.EndUpdateResourceW(handle, True)    # descarta
        tmp.unlink(missing_ok=True)
        raise
    if not k32.EndUpdateResourceW(handle, False):
        tmp.unlink(missing_ok=True)
        raise OSError(ctypes.get_last_error(), "EndUpdateResource")
    tmp.replace(dst)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    from .. import __version__
    src, dst, ico = map(Path, argv)
    brand(src, dst, ico, __version__)
    print(f"{dst}: {NAME} {__version__}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
