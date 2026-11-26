"""Linha de comando.

  mexerica                     inicia o serviço (roda + notificações)
  mexerica open ARQ...         abre a janela Início com os arquivos
  mexerica list ARQ...         lista operações disponíveis para os arquivos
  mexerica run ID ARQ...       executa uma operação sem interface
  mexerica doctor              mostra quais programas externos foram achados

O `run` permite usar o mesmo motor em scripts, no Nautilus Scripts ou num
menu de serviço do Dolphin (KDE) sem depender da extensão do GNOME Shell.
No Windows, `daemon` é como o atalho de inicialização sobe o serviço (sem
janela); `mexerica` sem argumento abre as Configurações.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from . import __version__, cache_dir
from .desktop import WINDOWS, setup_process
from .i18n import N_, _


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
    names = {CONVERT: _("Converter") + " (Shift)",
             TOOLS: _("Ferramentas") + " (Shift+Alt)",
             ACTIONS: _("Ações") + " (Shift+Ctrl)"}
    for g in groups:
        print(f"\n{names[g]}")
        for op in options_for(paths, g):
            hint = f"  — {_(op.hint)}" if op.hint else ""
            print(f"  {op.id:<18} {_(op.label)}{hint}")
    return 0


def cmd_run(args) -> int:
    from .engine import BY_ID, run
    from .engine.ops import ACTION, EDITOR
    op = BY_ID.get(args.op)
    if op is None:
        print(_("operação desconhecida: {op}").format(op=args.op),
              file=sys.stderr)
        return 2
    if op.mode == EDITOR:
        return _open_editor(op.id, args.files)
    if op.mode == ACTION:
        print(_("ações de interface só funcionam pela roda"),
              file=sys.stderr)
        return 2
    res = run(op, [Path(f) for f in args.files])
    for o in res.outputs:
        print(o)
    for t in res.texts:
        print(t)
    for src, err in res.errors:
        print(_("ERRO {src}: {err}").format(src=src, err=err),
              file=sys.stderr)
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
        print(_("serviço não respondeu: {err}").format(err=exc.message),
              file=sys.stderr)
        return 1
    return 0


def cmd_doctor(_args) -> int:
    from .engine import office
    from .engine import tools as T
    for name, what in T.PROGRAMS:
        found = T.resolve(name)
        mark = "ok " if found else "-- "
        print(f"{mark}{name:<10} {_(what)}"
              + ("" if found else "  " + _("(ausente)")))
    for name, what in T.MODULES:
        found = T.has_module(name)
        mark = "ok " if found else "-- "
        print(f"{mark}{name:<10} {_(what)}, " + _("módulo Python")
              + ("" if found else "  " + _("(ausente)")))
    fmts = T.magick_writable()
    extra = [f for f in ("heic", "avif", "webp", "jxl", "pdf") if f in fmts]
    print("\n" + _("ImageMagick escreve: {list}").format(
        list=", ".join(extra) or _("nenhum extra")))
    if WINDOWS:
        apps = [name for family, name in ((office.TEXT, "Word"),
                                          (office.SHEET, "Excel"),
                                          (office.SLIDES, "PowerPoint"))
                if office.ms_office(family)]
        print("Microsoft Office: " + (", ".join(apps) or _("ausente")))
    who = {office.MS: "Microsoft Office", office.LO: "LibreOffice",
           office.PANDOC: _("pandoc + typst (só o conteúdo, sem layout)")}
    for family, label, src in ((office.TEXT, N_("Textos"), "docx"),
                               (office.SHEET, N_("Planilhas"), "xlsx"),
                               (office.SLIDES, N_("Apresentações"), "pptx")):
        backend = office.route(family, src, "pdf")
        print(f"{_(label)} → PDF: {who.get(backend, _('ninguém'))}")
    if WINDOWS and not _packaged():
        print(_("Para instalar o que falta: .\\install.ps1 -Converters "
                "(LibreOffice: -Office)"))
    return 0


def _layer_shell_reexec() -> None:
    """COSMIC e outros sem a extensão do GNOME: o gtk4-layer-shell (a roda
    acima de tudo) só funciona carregado antes do libwayland, então o
    serviço reinicia uma vez com LD_PRELOAD."""
    if WINDOWS or "MEXERICA_LAYER_SHELL" in os.environ:
        return
    from .desktop.cosmic import is_gnome, layer_shell_preload
    if is_gnome() or not os.environ.get("WAYLAND_DISPLAY"):
        return
    lib = layer_shell_preload()
    if not lib:
        return
    env = dict(os.environ, MEXERICA_LAYER_SHELL="1")
    env["LD_PRELOAD"] = " ".join(filter(None, [lib, env.get("LD_PRELOAD")]))
    # o -m mexerica precisa achar o pacote de onde ele veio agora
    root = str(Path(__file__).resolve().parent.parent)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [root,
                                                      env.get("PYTHONPATH")]))
    os.execve(sys.executable, [sys.executable, "-m", "mexerica",
                               *sys.argv[1:]], env)


def cmd_wheel(argv: list[str]) -> int:
    """mexerica wheel [--group convert|tools|actions] [--explorer] ARQ...

    Abre a roda no ponteiro com os arquivos; clicar num item escolhe.
    --explorer (o "Ações da Mexerica" do menu de contexto): usa a seleção
    da janela do Explorer em primeiro plano, que o Explorer não passa
    inteira (chama uma vez por item)."""
    parser = argparse.ArgumentParser(prog="mexerica wheel")
    parser.add_argument("--group", default="actions",
                        choices=["convert", "tools", "actions"])
    parser.add_argument("--explorer", action="store_true")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv)
    _setup_logging(verbose=False)
    files = [Path(f).resolve() for f in args.files]
    if WINDOWS and args.explorer:
        from .desktop import shellview, win32
        sel = shellview.selection_at(win32.GetForegroundWindow())
        keys = {os.path.normcase(str(p)) for p in sel}
        if sel and (not files or any(os.path.normcase(str(f)) in keys
                                     for f in files)):
            files = sel
    given = bool(files)
    files = [f for f in files if f.exists()]
    if given and not files:
        print("mexerica wheel: " + _("nenhum arquivo"), file=sys.stderr)
        return 1
    # sem arquivos (atalho de teclado no COSMIC): a roda espera o arraste
    if WINDOWS:
        from .desktop import win32
        tray = win32.FindWindowExW(None, None, win32.TRAY_CLASS, None)
        if tray and win32.send_files(tray, [args.group, *map(str, files)],
                                     win32.COPY_WHEEL):
            return 0
    from .app import main as app_main
    return app_main([sys.argv[0]], wheel=(args.group, files))


def _packaged() -> bool:
    from .desktop import win32
    return win32.packaged()


def _startup_disabled(argv: list[str]) -> bool:
    """Versão da Store: a StartupTask do pacote sempre sobe o serviço (o
    MexericaService.exe marca MEXERICA_STARTUP); se o usuário desligou o
    "Iniciar com o sistema", ele sai antes de abrir qualquer coisa."""
    if not (WINDOWS and argv[:1] == ["daemon"]
            and os.environ.pop("MEXERICA_STARTUP", None) and _packaged()):
        return False
    from . import settings
    return not settings.get()["autostart"]


def main(argv: list[str] | None = None) -> int:
    setup_process()
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0].startswith("--gapplication") or argv[0] == "daemon":
        if _startup_disabled(argv):
            return 0
        _setup_logging(verbose=False)
        _layer_shell_reexec()
        from .app import main as app_main
        # daemon (atalho de inicialização do Windows) = modo serviço do
        # GApplication, o mesmo do autostart do GNOME: sobe sem abrir janela.
        # Sem argumento (menu Iniciar), abre as Configurações.
        rest = ["--gapplication-service" if a == "daemon" else a for a in argv]
        return app_main([sys.argv[0], *rest])
    if argv[0] == "open":
        # "Converter com a Mexerica" (Explorer/Nautilus): o GApplication
        # entrega os arquivos ao serviço que já roda ou vira o serviço
        _setup_logging(verbose=False)
        from .app import main as app_main
        files = [str(Path(a).resolve()) for a in argv[1:]]
        return app_main([sys.argv[0], *files])

    if argv[0] == "wheel":
        return cmd_wheel(argv[1:])

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
