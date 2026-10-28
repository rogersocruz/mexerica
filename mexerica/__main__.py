"""Linha de comando.

  mexerica                     inicia o serviço (roda + notificações)
  mexerica list ARQ...         lista operações disponíveis para os arquivos
  mexerica run ID ARQ...       executa uma operação sem interface
  mexerica doctor              mostra quais programas externos foram achados

O `run` permite usar o mesmo motor em scripts, no Nautilus Scripts ou num
menu de serviço do Dolphin (KDE) sem depender da extensão do GNOME Shell.
No Windows, `daemon` é como o atalho de inicialização sobe o serviço.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__, cache_dir
from .desktop import WINDOWS, setup_process


def _setup_logging(verbose: bool) -> None:
    logdir = cache_dir()
    logdir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        logging.FileHandler(logdir / "mexerica.log", encoding="utf-8")]
    if verbose:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(message)s")


def cmd_list(args) -> int:
    from .engine import ACTIONS, CONVERT, TOOLS, options_for
    from .engine.formats import kind_of
    paths = [Path(p) for p in args.files]
    for p in paths:
        print(f"{p.name}: {kind_of(p)}")
    groups = [args.group] if args.group else [CONVERT, TOOLS, ACTIONS]
    names = {CONVERT: "Converter (Shift)", TOOLS: "Ferramentas (Shift+Alt)",
             ACTIONS: "Ações (Shift+Ctrl)"}
    for g in groups:
        print(f"\n{names[g]}")
        for op in options_for(paths, g):
            hint = f"  — {op.hint}" if op.hint else ""
            print(f"  {op.id:<18} {op.label}{hint}")
    return 0


def cmd_run(args) -> int:
    from .engine import BY_ID, run
    from .engine.ops import ACTION, EDITOR
    op = BY_ID.get(args.op)
    if op is None:
        print(f"operação desconhecida: {args.op}", file=sys.stderr)
        return 2
    if op.mode == EDITOR:
        return _open_editor(op.id, args.files)
    if op.mode == ACTION:
        print("ações de interface só funcionam pela roda", file=sys.stderr)
        return 2
    res = run(op, [Path(f) for f in args.files])
    for o in res.outputs:
        print(o)
    for t in res.texts:
        print(t)
    for src, err in res.errors:
        print(f"ERRO {src}: {err}", file=sys.stderr)
    return 0 if res.ok else 1


def _open_editor(op_id: str, files: list[str]) -> int:
    """Operações com janela: pede ao serviço (já rodando) para abri-la."""
    from gi.repository import Gio, GLib
    from . import APP_ID
    paths = [str(Path(f).resolve()) for f in files]
    try:
        Gio.bus_get_sync(Gio.BusType.SESSION, None).call_sync(
            APP_ID, "/" + APP_ID.replace(".", "/"),
            "org.freedesktop.Application", "ActivateAction",
            GLib.Variant("(sava{sv})", (
                "open-editor",
                [GLib.Variant("(sas)", (op_id, paths))], {})),
            None, Gio.DBusCallFlags.NONE, 5000, None)
    except GLib.Error as exc:
        print(f"serviço não respondeu: {exc.message}", file=sys.stderr)
        return 1
    return 0


def cmd_doctor(_args) -> int:
    from .engine import tools as T
    progs = [
        ("ffmpeg", "vídeo e áudio"), ("ffprobe", "duração/tamanho alvo"),
        ("magick", "imagens (ImageMagick)"), ("montage", "colagem"),
        ("soffice", "documentos (LibreOffice)"), ("pandoc", "Markdown/EPUB"),
        ("pdftoppm", "PDF → imagens (poppler)"), ("pdftotext", "PDF → texto"),
        ("pdfimages", "extrair imagens de PDF"), ("qpdf", "juntar/dividir PDF"),
        ("gs", "comprimir PDF (Ghostscript)"),
        ("exiftool", "metadados"), ("zbarimg", "ler QR code (zbar)"),
        ("bsdtar", "ZIP/7Z/TAR/RAR (libarchive)"),
        ("ffplay", "ouvir o trecho no Cortar…"),
        ("rembg", "remover fundo de fotos com IA (opcional)"),
    ]
    if not WINDOWS:
        progs.append(("wl-copy", "clipboard sem a extensão (wl-clipboard)"))
    for name, what in progs:
        found = T.resolve(name)
        mark = "ok " if found else "-- "
        print(f"{mark}{name:<10} {what}" + ("" if found else "  (ausente)"))
    fmts = T.magick_writable()
    extra = [f for f in ("heic", "avif", "webp", "jxl", "pdf") if f in fmts]
    print(f"\nImageMagick escreve: {', '.join(extra) or 'nenhum extra'}")
    if WINDOWS:
        print("Para instalar o que falta: .\\install.ps1 -Converters "
              "(LibreOffice: -Office)")
    return 0


def main(argv: list[str] | None = None) -> int:
    setup_process()
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0].startswith("--gapplication") or argv[0] == "daemon":
        _setup_logging(verbose=False)
        from .app import main as app_main
        rest = [a for a in argv if a != "daemon"]
        return app_main([sys.argv[0], *rest])

    parser = argparse.ArgumentParser(prog="mexerica")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="operações disponíveis")
    p.add_argument("--group", choices=["convert", "tools", "actions"])
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("run", help="executa uma operação")
    p.add_argument("op")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("doctor", help="checa dependências")
    p.set_defaults(func=cmd_doctor)
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
