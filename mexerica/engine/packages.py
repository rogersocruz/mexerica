"""Formatos opcionais: baixar ou remover os programas de cada tipo de
arquivo (Configurações > Sobre > Formatos extras).

Cada Package diz que formatos libera, como saber se já está instalado
(programas e módulos que a Mexerica procura) e como instalar em cada
sistema:

  Windows  pacman do MSYS2 (o mesmo do install.ps1, sem administrador) e,
           para o que não existe no MSYS2, winget
  Linux    apt, dnf ou pacman, pedindo a senha pelo pkexec

Remover nunca leva junto o que outros programas usam: o pacman recusa
sozinho; no apt, uma simulação antes confere que só os pacotes pedidos
sairiam. Sem um jeito seguro (dnf), remover fica indisponível.

Puro Python, sem GTK: plan() monta os comandos (testável) e apply() roda.
"""
from __future__ import annotations

import importlib
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..i18n import N_, _
from . import tools as T

log = logging.getLogger("mexerica")

INSTALL, REMOVE = "install", "remove"
MSYS_PREFIX = "mingw-w64-ucrt-x86_64-"


@dataclass(frozen=True)
class Package:
    id: str
    title: str                         # português; a interface traduz
    formats: str
    programs: tuple[str, ...] = ()     # nomes lógicos de tools.resolve
    modules: tuple[str, ...] = ()      # módulos Python
    msys: tuple[str, ...] = ()         # Windows: pacotes do MSYS2
    winget: tuple[str, ...] = ()       # Windows: ids do winget
    linux: dict = field(default_factory=dict)   # apt/dnf/pacman -> nomes
    check: Callable[[], bool] | None = None      # detecção especial

    def installed(self) -> bool:
        if self.check is not None:
            return self.check()
        return all(T.has(p) for p in self.programs) and \
            all(T.has_module(m) for m in self.modules)


def _heic() -> bool:
    return T.has("magick") and "heic" in T.magick_writable()


PACKAGES: list[Package] = [
    Package("images", N_("Imagens"),
            N_("JPG, PNG, WEBP, GIF, TIFF, BMP e ICO"), programs=("magick",),
            msys=("imagemagick",),
            linux={"apt": ["imagemagick"], "dnf": ["ImageMagick"],
                   "pacman": ["imagemagick"]}),
    Package("heic", N_("HEIC e AVIF"),
            N_("Fotos de celular e imagens modernas"), check=_heic,
            msys=("libheif",),
            linux={"apt": ["libheif-plugin-libde265",
                           "libheif-plugin-aomenc"],
                   "dnf": ["libheif"], "pacman": ["libheif"]}),
    Package("svg", "SVG", N_("Desenhos vetoriais com mais fidelidade"),
            programs=("rsvg-convert",), msys=("librsvg",),
            linux={"apt": ["librsvg2-bin"], "dnf": ["librsvg2-tools"],
                   "pacman": ["librsvg"]}),
    Package("video", N_("Vídeo e áudio"),
            N_("MP4, MKV, MOV, WEBM, MP3, WAV, FLAC e OGG"),
            programs=("ffmpeg", "ffprobe"), msys=("ffmpeg",),
            linux={"apt": ["ffmpeg"], "dnf": ["ffmpeg-free"],
                   "pacman": ["ffmpeg"]}),
    Package("pdf", "PDF",
            N_("Juntar, dividir, comprimir e converter PDFs"),
            programs=("qpdf", "pdftoppm", "gs"),
            msys=("qpdf", "poppler", "ghostscript"),
            linux={"apt": ["qpdf", "poppler-utils", "ghostscript"],
                   "dnf": ["qpdf", "poppler-utils", "ghostscript"],
                   "pacman": ["qpdf", "poppler", "ghostscript"]}),
    Package("docs", N_("Documentos e Markdown"),
            N_("Markdown, EPUB, DOCX e texto para PDF"),
            programs=("pandoc",), msys=("typst",),
            winget=("JohnMacFarlane.Pandoc",),
            linux={"apt": ["pandoc"], "dnf": ["pandoc"],
                   "pacman": ["pandoc-cli", "typst"]}),
    Package("office", N_("Documentos do Office"),
            N_("DOCX, XLSX, PPTX e ODT para PDF, com o layout original"),
            programs=("soffice",),
            winget=("TheDocumentFoundation.LibreOffice",),
            linux={"apt": ["libreoffice-writer", "libreoffice-calc",
                           "libreoffice-impress"],
                   "dnf": ["libreoffice-writer", "libreoffice-calc",
                           "libreoffice-impress"],
                   "pacman": ["libreoffice-fresh"]}),
    Package("ebook", N_("E-books"), N_("MOBI, AZW3 e FB2"),
            programs=("ebook-convert",), winget=("calibre.calibre",),
            linux={"apt": ["calibre"], "dnf": ["calibre"],
                   "pacman": ["calibre"]}),
    Package("meta", N_("Metadados"),
            N_("Ver e apagar dados ocultos, como GPS e autor"),
            programs=("exiftool",), winget=("OliverBetz.ExifTool",),
            linux={"apt": ["libimage-exiftool-perl"],
                   "dnf": ["perl-Image-ExifTool"],
                   "pacman": ["perl-image-exiftool"]}),
    Package("qr", "QR code", N_("Ler e gerar QR codes"),
            programs=("zbarimg", "qrencode"), msys=("zbar", "qrencode"),
            linux={"apt": ["zbar-tools", "qrencode"],
                   "dnf": ["zbar", "qrencode"],
                   "pacman": ["zbar", "qrencode"]}),
    Package("archive", N_("Compactados"), N_("ZIP, 7Z, TAR e RAR"),
            programs=("bsdtar",), msys=("libarchive",),
            linux={"apt": ["libarchive-tools"], "dnf": ["bsdtar"],
                   "pacman": ["libarchive"]}),
    Package("data", N_("Dados"), N_("YAML para JSON, CSV e TOML"),
            modules=("yaml",), msys=("python-yaml",),
            linux={"apt": ["python3-yaml"], "dnf": ["python3-pyyaml"],
                   "pacman": ["python-yaml"]}),
    Package("fonts", N_("Fontes"), N_("TTF, OTF, WOFF e WOFF2"),
            modules=("fontTools", "brotli"),
            msys=("python-fonttools", "python-brotli"),
            linux={"apt": ["python3-fonttools", "python3-brotli"],
                   "dnf": ["python3-fonttools", "python3-brotli"],
                   "pacman": ["python-fonttools", "python-brotli"]}),
]
BY_ID = {p.id: p for p in PACKAGES}


# --------------------------------------------------------------------------
# Onde e como instalar
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class System:
    """O que existe nesta máquina para instalar pacotes."""
    kind: str               # windows | apt | dnf | pacman | store | none
    msys_bash: str | None = None    # Windows: bash do MSYS2
    winget: str | None = None
    pkexec: str | None = None

    @property
    def can_install(self) -> bool:
        return self.kind not in ("none", "store")


def detect() -> System:
    if sys.platform == "win32":
        from ..desktop.win32 import packaged
        if packaged():
            # loja: os conversores principais vêm no pacote, e um app da
            # loja não instala outros programas
            return System("store")
        bash = Path(sys.executable).resolve().parents[2] / "usr/bin/bash.exe"
        winget = shutil.which("winget") or _winget_alias()
        return System("windows", str(bash) if bash.exists() else None,
                      winget)
    pkexec = shutil.which("pkexec")
    for kind, exe in (("apt", "apt-get"), ("dnf", "dnf"),
                      ("pacman", "pacman")):
        if shutil.which(exe) and pkexec:
            return System(kind, pkexec=pkexec)
    return System("none")


def _winget_alias() -> str | None:
    alias = Path(os.environ.get("LOCALAPPDATA", ""),
                 "Microsoft/WindowsApps/winget.exe")
    return str(alias) if alias.exists() else None


def supported(pkg: Package, system: System, action: str) -> bool:
    """Dá para fazer `action` com este pacote neste sistema?"""
    if system.kind == "windows":
        if pkg.msys and not system.msys_bash:
            return False
        if pkg.winget and not system.winget:
            return False
        return bool(pkg.msys or pkg.winget)
    if system.kind in ("apt", "pacman"):
        return bool(pkg.linux.get(system.kind))
    if system.kind == "dnf":
        # o dnf tira junto o que depende do pacote: remover não é seguro
        return bool(pkg.linux.get("dnf")) and action == INSTALL
    return False


def plan(pkg: Package, system: System, action: str) -> list[list[str]]:
    """Os comandos para instalar ou remover `pkg` (sem rodar nada)."""
    if not supported(pkg, system, action):
        raise ValueError(_("Indisponível nesta versão."))
    steps: list[list[str]] = []
    if system.kind == "windows":
        if pkg.msys:
            names = " ".join(MSYS_PREFIX + n for n in pkg.msys)
            if action == INSTALL:
                cmd = f"pacman -S --needed --noconfirm {names}"
            else:
                # só o que está instalado (sem isso, um pacote ausente faz
                # o pacman recusar tudo); -R recusa se outro depende dele
                cmd = (f"pkgs=$(pacman -Qq {names} 2>/dev/null); "
                       f'[ -z "$pkgs" ] || pacman -R --noconfirm $pkgs')
            steps.append([system.msys_bash, "-lc", cmd])
        for wid in pkg.winget:
            steps.append([system.winget,
                          "install" if action == INSTALL else "uninstall",
                          "--id", wid, "-e", "--silent",
                          "--accept-source-agreements"]
                         + (["--accept-package-agreements"]
                            if action == INSTALL else []))
        return steps
    names = pkg.linux[system.kind]
    if system.kind == "apt":
        verb = ["install", "-y"] if action == INSTALL else ["remove", "-y"]
        return [[system.pkexec, "apt-get", *verb, *names]]
    if system.kind == "dnf":
        return [[system.pkexec, "dnf", "install", "-y", *names]]
    verb = ["-S", "--needed", "--noconfirm"] if action == INSTALL else \
        ["-R", "--noconfirm"]
    return [[system.pkexec, "pacman", *verb, *names]]


def apt_removes_only(names: list[str], simulation: str) -> list[str]:
    """Saída de `apt-get -s remove`: os pacotes que sairiam além dos
    pedidos (vazio = seguro)."""
    gone = [line.split()[1] for line in simulation.splitlines()
            if line.startswith("Remv ")]
    return [g for g in gone if g.split(":")[0] not in names]


def apply(pkg: Package, action: str,
          system: System | None = None) -> tuple[bool, str]:
    """Instala ou remove. Bloqueante (a interface chama numa thread).
    Devolve (deu certo, mensagem para mostrar)."""
    system = system or detect()
    try:
        steps = plan(pkg, system, action)
    except ValueError as exc:
        return False, str(exc)
    if system.kind == "apt" and action == REMOVE:
        names = pkg.linux["apt"]
        sim = subprocess.run(["apt-get", "-s", "remove", *names],
                             capture_output=True, text=True)
        extra = apt_removes_only(names, sim.stdout)
        if extra:
            return False, _("Não removido: outros programas usam este "
                            "pacote ({names}).").format(
                                names=", ".join(extra[:4]))
    for argv in steps:
        log.info("pacotes: %s", " ".join(argv))
        try:
            proc = subprocess.run(argv, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL)
        except OSError as exc:
            return False, str(exc)
        if _winget_done(argv, proc.returncode):
            continue
        if proc.returncode != 0 and _is_winget(argv):
            # programa instalado para todos os usuários (calibre, LibreOffice):
            # sem administrador o instalador falha (1603). Tenta de novo
            # pedindo permissão: o Windows mostra o aviso (UAC)
            log.info("pacotes: winget falhou (%#x); pedindo administrador",
                     proc.returncode & 0xFFFFFFFF)
            code = run_elevated(argv)
            if code == 0 or _winget_done(argv, code):
                continue
            if code == ERROR_CANCELLED:
                return False, _("Cancelado: o Windows pediu permissão de "
                                "administrador.")
            return False, (_("O Windows não deixou instalar.")
                           if action == INSTALL else
                           _("O Windows não deixou remover."))
        if proc.returncode != 0:
            out = (proc.stderr or proc.stdout or "").strip().splitlines()
            log.warning("pacotes: falhou (%s): %s", proc.returncode,
                        "\n".join(out[-6:]))
            if action == REMOVE and any("required by" in ln or
                                        "breaks dependency" in ln
                                        for ln in out):
                return False, _("Não removido: outros programas usam este "
                                "pacote.")
            return False, out[-1] if out else _("O gerenciador de pacotes "
                                                "falhou.")
    refresh()
    ok = pkg.installed() if action == INSTALL else not pkg.installed()
    if not ok and action == INSTALL:
        return False, _("Instalado, mas a Mexerica ainda não encontrou o "
                        "programa. Reinicie a Mexerica.")
    return True, ""


# winget: "já instalado" (instalar) e "não instalado" (remover) não são
# falha: o resultado é o pedido
WINGET_ALREADY = 0x8A15002B
WINGET_NOT_FOUND = 0x8A150014


ERROR_CANCELLED = 1223          # o usuário disse não ao aviso do UAC


def _is_winget(argv: list[str]) -> bool:
    return bool(argv) and "winget" in Path(argv[0]).name.lower()


def _winget_done(argv: list[str], code: int) -> bool:
    if not _is_winget(argv):
        return False
    return (code & 0xFFFFFFFF) in (WINGET_ALREADY, WINGET_NOT_FOUND)


def _ps_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def elevated_command(argv: list[str]) -> list[str]:
    """PowerShell que roda `argv` como administrador (aviso do UAC), espera
    e devolve o código de saída; 1223 se o usuário recusar."""
    args = ", ".join(_ps_quote(a) for a in argv[1:])
    script = (f"try {{ $p = Start-Process -FilePath {_ps_quote(argv[0])} "
              f"-ArgumentList @({args}) -Verb RunAs -Wait -PassThru "
              f"-WindowStyle Hidden; exit $p.ExitCode }} "
              f"catch {{ exit {ERROR_CANCELLED} }}")
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def run_elevated(argv: list[str]) -> int:
    proc = subprocess.run(elevated_command(argv), capture_output=True,
                          stdin=subprocess.DEVNULL)
    log.info("pacotes: como administrador, saiu com %#x",
             proc.returncode & 0xFFFFFFFF)
    return proc.returncode


def refresh() -> None:
    """Esquece o que já foi procurado: programas novos aparecem na roda."""
    for fn in (T.which, T.resolve, T._search_path, T._magick_formats,
               T.ffmpeg_encoders):
        fn.cache_clear()
    importlib.invalidate_caches()


__all__ = ["Package", "PACKAGES", "BY_ID", "System", "detect", "supported",
           "plan", "apply", "refresh", "apt_removes_only", "elevated_command",
           "run_elevated", "INSTALL", "REMOVE"]
