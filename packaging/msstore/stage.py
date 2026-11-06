"""Monta a pasta do pacote MSIX da Microsoft Store (o build.ps1 chama).

Roda no Python do MSYS2 (UCRT64), o mesmo que vai dentro do pacote:

  runtime/            o pedaço do MSYS2 que a Mexerica usa: Python, GTK 4,
                      PyGObject e os conversores, com as dependências
                      (o fecho do pactree), sem cabeçalhos, .a e manuais
    lib/python3.X/site-packages/mexerica   o app
    bin/pandoc.exe, bin/exiftool.exe       baixados (não estão no MSYS2)
  Assets/             logos do menu Iniciar, da barra e da Store (do SVG)
  AppxManifest.xml    do AppxManifest.xml.in, com a identidade do store.json
  THIRD-PARTY-NOTICES.txt

O que o MSYS2 gera ao instalar (loaders.cache do gdk-pixbuf, schemas do
GLib, cache dos ícones) não está na lista de arquivos dos pacotes e é
copiado à parte. Os .pyc são gerados aqui: a pasta de um pacote MSIX é
somente leitura e o Python não conseguiria gravá-los.

  python stage.py --msys C:\\msys64 --out build\\stage --version 0.1.0.0
"""
from __future__ import annotations

import argparse
import compileall
import json
import os
import py_compile
import re
import shutil
import stat
import struct
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
from mexerica.engine.formats import EXT_TO_KIND  # noqa: E402

PKG = "mingw-w64-ucrt-x86_64-"
# o mesmo que o install.ps1 -Converters instala
PACKAGES = ["python", "gtk4", "python-gobject", "python-cairo",
            "adwaita-icon-theme", "ffmpeg", "imagemagick", "libheif",
            "librsvg", "poppler", "qpdf", "ghostscript", "zbar", "libarchive",
            "typst", "python-yaml", "python-fonttools", "python-brotli"]

# Fora do MSYS2: versões fixas, para o pacote ser reproduzível
PANDOC = ("3.13", "https://github.com/jgm/pandoc/releases/download/"
                   "{v}/pandoc-{v}-windows-x86_64.zip")
EXIFTOOL = ("13.60", "https://sourceforge.net/projects/exiftool/files/"
                     "exiftool-{v}_64.zip/download")

# (os .la ficam: é por eles que o ImageMagick acha os próprios módulos)
PRUNE = re.compile(r"""
    ^include/ | \.a$ | ^lib/cmake/ | ^lib/pkgconfig/
  | ^share/(doc|man|info|gtk-doc|aclocal|pkgconfig|gettext|bash-completion)/
  | ^share/locale/(?!pt_BR/|pt/)
  | ^lib/python3\.\d+/(test|idlelib|turtledemo|ensurepip)/
  | ^share/gir-1.0/ | /__pycache__/ | /tests?/.*\.py$
""", re.X)

# Dos executáveis do runtime, só os que o motor chama (tools.PROGRAMS e
# os needs= das operações), os auxiliares do GLib e o próprio Python; os
# outros (demos do GTK, ferramentas do x265, djvu, gst...) só ocupam espaço.
# DLL nenhuma sai: o ffmpeg e o magick carregam muitas.
KEEP_EXE = re.compile(r"""^(
    python[\d.]*w?|ffmpeg|ffprobe|ffplay|magick|gs|gswin64c|pdftoppm
  | pdftotext|pdfimages|pdfinfo|qpdf|zbarimg|bsdtar|typst|rsvg-convert
  | gdbus|gspawn-win64-helper(-console)?|gdk-pixbuf-query-loaders
)\.exe$""", re.X | re.I)

# gerados pelos hooks do pacman (não constam do `pacman -Ql`)
GENERATED = ["lib/gdk-pixbuf-2.0/2.10.0/loaders.cache",
             "share/glib-2.0/schemas/gschemas.compiled",
             "share/icons/Adwaita/icon-theme.cache",
             "share/icons/AdwaitaLegacy/icon-theme.cache",
             "share/icons/hicolor/icon-theme.cache"]

# (arquivo, lado, largura x altura da página) para o Assets/
ASSETS = [
    *[(f"Square44x44Logo.scale-{s}.png", 44 * s // 100, (44 * s // 100,) * 2)
      for s in (100, 200)],
    *[(f"Square44x44Logo.targetsize-{n}{alt}.png", n, (n, n))
      for n in (16, 24, 32, 48, 256) for alt in ("", "_altform-unplated")],
    *[(f"Square150x150Logo.scale-{s}.png", 96 * s // 100,
       (150 * s // 100,) * 2) for s in (100, 200)],
    *[(f"Wide310x150Logo.scale-{s}.png", 96 * s // 100,
       (310 * s // 100, 150 * s // 100)) for s in (100, 200)],
    *[(f"LargeTile.scale-{s}.png", 200 * s // 100, (310 * s // 100,) * 2)
      for s in (100, 200)],
    *[(f"SmallTile.scale-{s}.png", 50 * s // 100, (71 * s // 100,) * 2)
      for s in (100, 200)],
    *[(f"StoreLogo.scale-{s}.png", 50 * s // 100, (50 * s // 100,) * 2)
      for s in (100, 200)],
]


def msys_bash(msys: Path, script: str) -> str:
    env = {**os.environ, "MSYSTEM": "UCRT64", "CHERE_INVOKING": "1"}
    out = subprocess.run([str(msys / "usr/bin/bash.exe"), "-lc", script],
                         capture_output=True, text=True, encoding="utf-8",
                         env=env, check=True)
    return out.stdout


def closure(msys: Path, wanted: list[str]) -> list[str]:
    """Os pacotes pedidos e todas as dependências deles."""
    names: set[str] = set()
    for name in wanted:
        out = msys_bash(msys, f"pactree -lu {name}")
        # (algumas vêm com versão: "...-libgcc=16.2.0-6")
        names.update(re.split(r"[<>=]", line.strip())[0]
                     for line in out.splitlines() if line.strip())
    # o pactree também lista o que é só "provides" (sem pacote próprio)
    installed = set(msys_bash(msys, "pacman -Qq").split())
    return sorted(names & installed)


def copy_runtime(msys: Path, packages: list[str], runtime: Path) -> int:
    listing = msys_bash(msys, "pacman -Qlq " + " ".join(packages))
    count = 0
    for line in listing.splitlines():
        if not line.startswith("/ucrt64/") or line.endswith("/"):
            continue
        rel = line[len("/ucrt64/"):]
        if PRUNE.search(rel) or (rel.startswith("bin/") and rel.endswith(".exe")
                                 and not KEEP_EXE.match(rel[4:])):
            continue
        src = msys / "ucrt64" / rel
        if not src.is_file():
            continue
        dst = runtime / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        count += 1
    for rel in GENERATED:
        src = msys / "ucrt64" / rel
        if src.is_file():
            (runtime / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, runtime / rel)
    return count


def pe_imports(path: Path) -> list[str]:
    """DLLs que um .exe/.dll/.pyd importa ao carregar (tabela de importação
    do PE; as de carga atrasada ficam de fora)."""
    data = path.read_bytes()
    if data[:2] != b"MZ":
        return []
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        return []
    nsec, = struct.unpack_from("<H", data, pe + 6)
    optsize, = struct.unpack_from("<H", data, pe + 20)
    opt = pe + 24
    pe32plus = struct.unpack_from("<H", data, opt)[0] == 0x20B
    imp_rva, = struct.unpack_from("<I", data, opt + (112 if pe32plus else 96) + 8)
    sections = [struct.unpack_from("<IIII", data, opt + optsize + 40 * i + 8)
                for i in range(nsec)]

    def offset(rva: int) -> int | None:
        for vsize, va, rawsize, raw in sections:
            if va <= rva < va + max(vsize, rawsize):
                return rva - va + raw
        return None

    names = []
    desc = offset(imp_rva) if imp_rva else None
    while desc is not None and desc + 20 <= len(data):
        name_rva, = struct.unpack_from("<I", data, desc + 12)
        at = offset(name_rva) if name_rva else None
        if at is None:
            break
        names.append(data[at:data.index(b"\0", at)].decode("ascii", "replace"))
        desc += 20
    return names


def missing_dlls(runtime: Path) -> dict[str, set[str]]:
    """DLL importada que não está no runtime nem no Windows: o programa nem
    abriria (0xC0000135). Confere tudo que vai no pacote."""
    system = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    have = {p.name.lower() for p in (runtime / "bin").glob("*.dll")}
    missing: dict[str, set[str]] = {}
    for path in runtime.rglob("*"):
        if path.suffix.lower() not in (".exe", ".dll", ".pyd"):
            continue
        if "exiftool_files" in path.parts:
            continue        # o perl do exiftool carrega as DLLs da própria pasta
        for dll in pe_imports(path):
            low = dll.lower()
            if low in have or low.startswith(("api-ms-win-", "ext-ms-")) \
                    or (path.parent / dll).exists() or (system / dll).exists():
                continue
            missing.setdefault(dll, set()).add(str(path.relative_to(runtime)))
    return missing


def fix_dlls(msys: Path, packages: list[str], runtime: Path) -> list[str]:
    """Fecha as DLLs que faltam: a que o MSYS2 tem entra com o pacote dela
    (dependências declaradas só como "provides", como o OpenMP do magick e
    do ffmpeg); a que nem está instalada é de um plugin opcional (frei0r com
    OpenCV, o coder DOT do graphviz...), e o plugin sai do pacote."""
    for _ in range(8):
        missing = missing_dlls(runtime)
        if not missing:
            return packages
        owners: set[str] = set()
        for dll, users in sorted(missing.items()):
            if (msys / "ucrt64/bin" / dll).is_file():
                owners.add(msys_bash(msys, f"pacman -Qoq /ucrt64/bin/{dll}")
                           .strip())
                continue
            for user in sorted(users):
                (runtime / user).unlink(missing_ok=True)
                print(f"sem {dll}: {user} ficou de fora")
        new = sorted(set(closure(msys, sorted(owners))) - set(packages))
        if new:
            print(f"+{len(new)} pacotes por DLLs que faltavam: {', '.join(new)}")
            copy_runtime(msys, new, runtime)
            packages = sorted(set(packages) | set(new))
    raise SystemExit(f"DLLs ainda faltando: {sorted(missing_dlls(runtime))}")


def site_packages(runtime: Path) -> Path:
    return runtime / "lib" / f"python{sys.version_info[0]}.{sys.version_info[1]}" \
        / "site-packages"


def copy_app(runtime: Path) -> None:
    dest = site_packages(runtime) / "mexerica"
    shutil.copytree(REPO / "mexerica", dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def compile_python(runtime: Path) -> None:
    # sem conferir a data do .py: a instalação do MSIX não garante mtimes
    ok = compileall.compile_dir(
        runtime / "lib", quiet=1, workers=0,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
    if not ok:
        print("aviso: alguns .py não compilaram (veja acima)")


def download(url: str, cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^\w.-]", "_", url.rstrip("/").removesuffix("/download")
                  .rsplit("/", 1)[-1])
    target = cache / name
    if not target.exists():
        print(f"baixando {url}")
        tmp = target.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=120) as resp, \
                open(tmp, "wb") as fh:
            shutil.copyfileobj(resp, fh)
        tmp.replace(target)
    return target


def add_pandoc(runtime: Path, cache: Path) -> str | None:
    version, url = PANDOC
    try:
        archive = download(url.format(v=version), cache)
    except OSError as exc:
        print(f"aviso: pandoc não entrou ({exc})")
        return None
    with zipfile.ZipFile(archive) as zf:
        member = next(n for n in zf.namelist() if n.endswith("/pandoc.exe"))
        with zf.open(member) as src, open(runtime / "bin/pandoc.exe", "wb") as dst:
            shutil.copyfileobj(src, dst)
    return version


def add_exiftool(runtime: Path, cache: Path) -> str | None:
    version, url = EXIFTOOL
    try:
        archive = download(url.format(v=version), cache)
    except OSError as exc:
        print(f"aviso: exiftool não entrou ({exc})")
        return None
    bindir = runtime / "bin"
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            # exiftool-13.25_64/exiftool(-k).exe e exiftool-13.25_64/exiftool_files/...
            rel = member.filename.split("/", 1)[1]
            if rel == "exiftool(-k).exe":
                rel = "exiftool.exe"    # sem o "(-k)", não espera um Enter
            dst = bindir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dst, "wb") as fh:
                shutil.copyfileobj(src, fh)
    return version


def make_assets(msys: Path, out: Path) -> None:
    svg = REPO / "data/icons/io.github.rogersocruz.Mexerica.svg"
    rsvg = msys / "ucrt64/bin/rsvg-convert.exe"
    out.mkdir(parents=True, exist_ok=True)
    for name, side, (w, h) in ASSETS:
        subprocess.run([str(rsvg), "-w", str(side), "-h", str(side),
                        "--page-width", str(w), "--page-height", str(h),
                        "--left", str((w - side) // 2),
                        "--top", str((h - side) // 2),
                        "-o", str(out / name), str(svg)], check=True)


def write_manifest(out: Path, identity: dict, version: str) -> None:
    # o Windows reserva algumas extensões (o makeappx recusa o manifesto)
    reserved = {"ttf"}
    types = "\n".join(f"              <uap:FileType>.{ext}</uap:FileType>"
                      for ext in sorted(set(EXT_TO_KIND) - reserved))
    text = (HERE / "AppxManifest.xml.in").read_text(encoding="utf-8")
    for key, value in {"IDENTITY_NAME": identity["identityName"],
                       "PUBLISHER": identity["publisher"],
                       "PUBLISHER_DISPLAY_NAME":
                           identity["publisherDisplayName"],
                       "VERSION": version, "FILE_TYPES": types}.items():
        text = text.replace(f"@{key}@", value)
    (out / "AppxManifest.xml").write_text(text, encoding="utf-8")


def write_notices(msys: Path, packages: list[str], out: Path,
                  extra: list[tuple[str, str, str, str]]) -> None:
    info = msys_bash(msys, "pacman -Qi " + " ".join(packages))
    rows = []
    for block in info.strip().split("\n\n"):
        fields = dict(re.findall(r"^(\w[\w ]*?)\s*:\s*(.*)$", block, re.M))
        rows.append((fields.get("Name", "?").removeprefix(PKG),
                     fields.get("Version", "?"), fields.get("Licenses", "?"),
                     fields.get("URL", "")))
    rows += extra
    lines = [
        "Mexerica — avisos de terceiros",
        "",
        "A Mexerica é distribuída sob a licença MIT (LICENSE, abaixo). Este",
        "pacote inclui os programas e bibliotecas listados, cada um sob a",
        "própria licença; os textos completos ficam em runtime/share/licenses.",
        "O código-fonte dos pacotes do MSYS2 está em",
        "https://github.com/msys2/MINGW-packages e, nas versões exatas",
        "usadas aqui, em https://repo.msys2.org/mingw/sources/.",
        "",
        f"{'Componente':<34} {'Versão':<22} Licença",
        "-" * 100,
    ]
    lines += [f"{n:<34} {v:<22} {lic}  {url}" for n, v, lic, url in rows]
    lines += ["", "-" * 100, "", (REPO / "LICENSE").read_text(encoding="utf-8")]
    (out / "THIRD-PARTY-NOTICES.txt").write_text("\n".join(lines),
                                                  encoding="utf-8")


def _writable_retry(func, path, _exc) -> None:
    """Alguns arquivos do MSYS2 vêm somente leitura (e o copy2 mantém)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--msys", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--identity", type=Path, default=HERE / "store.json")
    ap.add_argument("--cache", type=Path, default=HERE / "build" / "downloads")
    args = ap.parse_args()

    out: Path = args.out
    if out.exists():
        shutil.rmtree(out, onexc=_writable_retry)
    runtime = out / "runtime"
    identity = json.loads(args.identity.read_text(encoding="utf-8"))

    packages = closure(args.msys, [PKG + name for name in PACKAGES])
    print(f"{len(packages)} pacotes do MSYS2")
    print(f"{copy_runtime(args.msys, packages, runtime)} arquivos copiados")
    packages = fix_dlls(args.msys, packages, runtime)
    extra = []
    if (v := add_pandoc(runtime, args.cache)):
        extra.append(("pandoc", v, "GPL-2.0-or-later", "https://pandoc.org"))
    if (v := add_exiftool(runtime, args.cache)):
        extra.append(("exiftool", v, "Artistic-1.0-Perl OR GPL-1.0-or-later",
                      "https://exiftool.org"))
    copy_app(runtime)
    compile_python(runtime)
    make_assets(args.msys, out / "Assets")
    write_manifest(out, identity, args.version)
    write_notices(args.msys, packages, out, extra)
    shutil.copy2(REPO / "LICENSE", out / "LICENSE.txt")
    print(f"pasta do pacote pronta: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
