"""Serviço GTK 4: janela overlay com a roda, execução dos jobs e notificações.

Fluxo:
  1. Alguém percebe Shift durante um arraste: no GNOME, a extensão do
     Shell, que chama a ação D-Bus `show(modo, uris, x, y)`; no Windows, o
     próprio serviço (desktop/windows.py), que chama `show_wheel`.
  2. Abrimos uma janela transparente do tamanho da tela, acima de tudo.
     Como ela fica sob o ponteiro, o arraste em andamento passa a apontar
     para ela e o GtkDropTarget recebe hover e drop.
  3. No drop, o setor sob o ponteiro decide a operação; a janela some e o
     job roda numa thread, com notificação de início/fim.

O que muda de um desktop para outro fica em mexerica/desktop/.

Também dá para testar sem extensão:
  gapplication action io.github.rogersocruz.Mexerica show \
      "('convert', ['file:///caminho/foto.png'], 600, 400)"
e clicar num setor.
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango  # noqa: E402

from . import APP_ID, __version__, cache_dir  # noqa: E402
from . import desktop  # noqa: E402
from . import theme as TH  # noqa: E402
from .engine import ACTIONS, CONVERT, TOOLS, options_for, run  # noqa: E402
from .engine import tools as T  # noqa: E402
from .engine.ops import ACTION, EDITOR, TEXT, Op  # noqa: E402
from .engine import BY_ID  # noqa: E402
from .editors import open_editor  # noqa: E402
from .engine.runner import unique_path  # noqa: E402
from .wheel.geometry import Wheel  # noqa: E402
from .wheel.render import Snapshot, WheelState, draw  # noqa: E402

log = logging.getLogger("mexerica")

OVERLAY_TITLE = "mexerica-overlay"     # a extensão reconhece por este título
IDLE_HIDE_MS = 4000      # trava de segurança: overlay sem atividade some

CSS = """
window.mexerica-overlay, window.mexerica-overlay > *,
window.mexerica-overlay.background, window.mexerica-overlay decoration {
  background: none; background-color: transparent;
  box-shadow: none; border: none; outline: none;
}
.mexerica-float-box { padding: 10px 14px; }
""" + TH.CSS


def paths_from_uris(uris) -> list[Path]:
    out = []
    for u in uris:
        f = Gio.File.new_for_uri(u) if "://" in u else Gio.File.new_for_path(u)
        p = f.get_path()
        if p:
            out.append(Path(p))
    return out


def paths_from_filelist(value) -> list[Path]:
    if value is None:
        return []
    files = value.get_files() if hasattr(value, "get_files") else []
    return [Path(f.get_path()) for f in files if f.get_path()]


def _caption(paths: list[Path]) -> str:
    """Notificações: nome do arquivo ou quantos são."""
    if not paths:
        return ""
    if len(paths) == 1:
        return paths[0].name
    return f"{len(paths)} arquivos"


def _size_caption(paths: list[Path]) -> str:
    """Miolo da roda: tamanho total, como no Tangerine ("1.1 MB")."""
    total = 0
    for p in paths:
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    if total:
        return TH.human_size(total)
    return f"{len(paths)} items" if paths else ""


# --------------------------------------------------------------------------
# Janela overlay com a roda
# --------------------------------------------------------------------------

class Overlay(Gtk.Window):
    def __init__(self, app: "MexericaApp"):
        super().__init__(application=app, title=OVERLAY_TITLE,
                         decorated=False)
        self.app = app
        self.add_css_class("mexerica-overlay")
        self.remove_css_class("background")     # tema não pinta fundo
        self.state = WheelState()
        self.ops: list[Op] = []
        self.paths: list[Path] = []
        self.center = (0.0, 0.0)
        self.wheel: Wheel | None = None
        self._wheel_size = (0, 0)
        self._anim_last = None
        self._ticking = False
        self._idle_src = 0
        self._dragging = False

        self.area = Gtk.DrawingArea(hexpand=True, vexpand=True)
        self.area.set_draw_func(self._on_draw)
        self.set_child(self.area)

        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.set_preload(True)
        drop.connect("enter", self._on_drag_enter)
        drop.connect("motion", self._on_drag_motion)
        drop.connect("leave", self._on_drag_leave)
        drop.connect("drop", self._on_drop)
        drop.connect("notify::value", self._on_drop_value)
        self.area.add_controller(drop)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", lambda _c, x, y: self._hover(x, y))
        self.area.add_controller(motion)

        click = Gtk.GestureClick()
        click.connect("released", self._on_click)
        self.area.add_controller(click)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

    # -- abrir/fechar ------------------------------------------------------
    def open(self, mode: str, paths: list[Path], x: int, y: int) -> None:
        first = not self.get_visible()
        st = self.state
        if not first and mode != st.mode and self.ops:
            # troca de modo: os setores antigos somem enquanto os novos
            # aparecem; o anel fica parado
            old = self._ensure_wheel(self.area.get_width(),
                                     self.area.get_height())
            st.prev = Snapshot(old, list(st.labels), list(st.icons))
            st.fade = 0.0
            st.hover_t.clear()
            self._animate()
        st.mode = mode
        if paths or first:
            # roda nova começa sem os arquivos do arraste anterior: até eles
            # chegarem, o miolo mostra "…"
            self.paths = paths
        self.center = (float(x), float(y))
        self._refresh_ops()
        if first:
            st.hover = None
            st.cancel_hover = False
            st.hover_t.clear()
            st.prev = None
            st.fade = 1.0
            st.progress = 0.0
            self._animate()
            self.app.desktop.show_overlay(self)
        self.wheel = None
        self.area.queue_draw()
        self._arm_idle_hide()

    def close_wheel(self) -> None:
        if self._idle_src:
            GLib.source_remove(self._idle_src)
            self._idle_src = 0
        self._dragging = False
        self.set_visible(False)

    def _arm_idle_hide(self) -> None:
        if self._idle_src:
            GLib.source_remove(self._idle_src)
        self._idle_src = GLib.timeout_add(IDLE_HIDE_MS, self._idle_hide)

    def _idle_hide(self):
        self._idle_src = 0
        if self._dragging:
            # arraste parado sobre a roda: quem fecha é a extensão no fim
            self._arm_idle_hide()
            return GLib.SOURCE_REMOVE
        log.info("overlay sem atividade; escondendo")
        self.set_visible(False)
        return GLib.SOURCE_REMOVE

    def _refresh_ops(self) -> None:
        self.ops = options_for(self.paths, self.state.mode)
        self.state.labels = [TH.wheel_label(op) for op in self.ops]
        self.state.icons = [TH.wheel_icon(op) for op in self.ops]
        self.state.hints = [op.hint for op in self.ops]
        self.state.caption = _size_caption(self.paths)
        self.state.loading = not self.paths
        self.wheel = None

    # -- desenho -----------------------------------------------------------
    def _ensure_wheel(self, w: float, h: float) -> Wheel:
        # recalcula se o tamanho mudou (o maximizar chega depois do map)
        if self.wheel is None or self._wheel_size != (w, h):
            cx, cy = self.app.desktop.wheel_center(self, w, h) or self.center
            if cx <= 0 and cy <= 0:
                cx, cy = w / 2, h / 2
            self.wheel = Wheel(len(self.ops), cx, cy, w or None, h or None)
            self._wheel_size = (w, h)
        return self.wheel

    def _on_draw(self, _area, cr, w, h) -> None:
        dim = self.app.desktop.overlay_dim
        if dim:
            # sem um compositor que escureça o fundo (Windows), a própria
            # janela escurece a tela atrás da roda, entrando junto com ela
            cr.set_source_rgba(0, 0, 0, dim * min(self.state.progress, 1.0))
            cr.paint()
        draw(cr, self._ensure_wheel(w, h), self.state)

    def _animate(self) -> None:
        if not self._ticking:
            self._ticking = True
            self._anim_last = None
            self.add_tick_callback(self._tick)

    def _tick(self, _widget, clock) -> bool:
        """Entrada (escala+opacidade), hover (cor e crescimento) e troca de
        modo (crossfade), todos no mesmo relógio de quadros."""
        now = clock.get_frame_time()
        dt = 0.0 if self._anim_last is None else (now - self._anim_last) / 1000
        self._anim_last = now
        st = self.state
        busy = False
        if st.progress < 1:
            st.progress = min(1.0, st.progress + dt / TH.ENTER_MS)
            busy |= st.progress < 1
        if st.fade < 1:
            st.fade = min(1.0, st.fade + dt / TH.MODE_FADE_MS)
            if st.fade >= 1:
                st.prev = None
            busy |= st.fade < 1
        step = dt / TH.HOVER_MS
        for idx in set(st.hover_t) | ({st.hover} - {None}):
            target = 1.0 if idx == st.hover else 0.0
            cur = st.hover_t.get(idx, 0.0)
            cur = min(target, cur + step) if target > cur \
                else max(target, cur - step)
            if cur <= 0:
                st.hover_t.pop(idx, None)
            else:
                st.hover_t[idx] = cur
            busy |= cur != target
        self.area.queue_draw()
        if not busy:
            self._ticking = False
        return busy

    # -- interação ---------------------------------------------------------
    def _hover(self, x: float, y: float) -> None:
        wheel = self._ensure_wheel(self.area.get_width(),
                                   self.area.get_height())
        hover = wheel.hit(x, y)
        cancel = wheel.in_cancel(x, y)
        if hover != self.state.hover or cancel != self.state.cancel_hover:
            self.state.hover = hover
            self.state.cancel_hover = cancel
            self._animate()
        self._arm_idle_hide()

    def _on_drag_enter(self, _t, x, y):
        self._dragging = True
        self._hover(x, y)
        return Gdk.DragAction.COPY

    def _on_drag_motion(self, _t, x, y):
        self._hover(x, y)
        return Gdk.DragAction.COPY

    def _on_drag_leave(self, _t):
        self._dragging = False
        self.state.hover = None
        self._animate()

    def _on_drop_value(self, target, _pspec):
        paths = paths_from_filelist(target.get_value())
        if paths and paths != self.paths:
            self.paths = paths
            self._refresh_ops()
            self.area.queue_draw()

    def _on_drop(self, _t, value, x, y) -> bool:
        paths = paths_from_filelist(value) or self.paths
        wheel = self._ensure_wheel(self.area.get_width(),
                                   self.area.get_height())
        idx = wheel.hit(x, y)
        ops = self.ops if paths == self.paths else \
            options_for(paths, self.state.mode)
        # esconder só depois que o GTK concluir o drop
        GLib.idle_add(lambda: (self.close_wheel(), False)[1])
        if idx is None or idx >= len(ops) or not paths:
            return False   # soltar no miolo/fora = cancelar
        GLib.idle_add(self.app.execute, ops[idx], paths)
        return True

    def _on_click(self, _g, _n, x, y) -> None:
        # Uso sem arraste (teste/demonstração): clicar escolhe o setor.
        wheel = self._ensure_wheel(self.area.get_width(),
                                   self.area.get_height())
        idx = wheel.hit(x, y)
        paths = list(self.paths)
        self.close_wheel()
        if idx is not None and idx < len(self.ops) and paths:
            self.app.execute(self.ops[idx], paths)

    def _on_key(self, _c, keyval, _code, _state) -> bool:
        n = len(self.ops)
        if keyval == Gdk.KEY_Escape:
            self.close_wheel()
            return True
        if n and keyval in (Gdk.KEY_Right, Gdk.KEY_Down, Gdk.KEY_Tab):
            self.state.hover = 0 if self.state.hover is None \
                else (self.state.hover + 1) % n
        elif n and keyval in (Gdk.KEY_Left, Gdk.KEY_Up, Gdk.KEY_ISO_Left_Tab):
            self.state.hover = n - 1 if self.state.hover is None \
                else (self.state.hover - 1) % n
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            idx = self.state.hover
            paths = list(self.paths)
            self.close_wheel()
            if idx is not None and paths:
                self.app.execute(self.ops[idx], paths)
            return True
        else:
            return False
        self._animate()
        return True


# --------------------------------------------------------------------------
# Janela "Flutuar": guarda arquivos para arrastar depois
# --------------------------------------------------------------------------

class FloatWindow(Gtk.Window):
    def __init__(self, app, paths: list[Path]):
        n = len(paths)
        super().__init__(application=app,
                         title=f"Mexerica — {paths[0].name if n == 1 else f'{n} arquivos'}",
                         resizable=False, default_width=220)
        self.add_css_class("mx-window")
        self.paths = paths
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.add_css_class("mexerica-float-box")
        ctype, _ = Gio.content_type_guess(str(paths[0]), None)
        icon = Gtk.Image.new_from_gicon(Gio.content_type_get_icon(ctype))
        icon.set_pixel_size(48)
        label = Gtk.Label(label=paths[0].name if n == 1 else f"{n} arquivos",
                          ellipsize=Pango.EllipsizeMode.END,
                          max_width_chars=22, xalign=0)
        close = Gtk.Button(icon_name="window-close-symbolic")
        close.add_css_class("flat")
        close.connect("clicked", lambda *_: self.close())
        box.append(icon)
        box.append(label)
        box.append(close)
        self.set_child(box)
        self.set_tooltip_text("Arraste daqui para qualquer lugar")

        src = Gtk.DragSource(actions=Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        src.connect("prepare", self._prepare)
        src.connect("drag-end", lambda *_: self.close())
        box.add_controller(src)

    def _prepare(self, _src, _x, _y):
        files = [Gio.File.new_for_path(str(p)) for p in self.paths]
        flist = Gdk.FileList.new_from_array(files)
        return Gdk.ContentProvider.new_for_value(
            GObject.Value(Gdk.FileList, flist))


# --------------------------------------------------------------------------
# Janela de texto (metadados)
# --------------------------------------------------------------------------

class TextWindow(Gtk.Window):
    def __init__(self, app, title: str, text: str):
        super().__init__(application=app, title=title, default_width=720,
                         default_height=560)
        header = Gtk.HeaderBar()
        copy = Gtk.Button(icon_name="edit-copy-symbolic",
                          tooltip_text="Copiar tudo")
        copy.connect("clicked", lambda *_: app.set_clipboard(text))
        header.pack_end(copy)
        self.set_titlebar(header)
        view = Gtk.TextView(editable=False, monospace=True,
                            wrap_mode=Gtk.WrapMode.WORD_CHAR,
                            left_margin=12, right_margin=12, top_margin=8)
        view.get_buffer().set_text(text)
        scroll = Gtk.ScrolledWindow(child=view)
        self.set_child(scroll)


# --------------------------------------------------------------------------
# Aplicação
# --------------------------------------------------------------------------

class MexericaApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.overlay: Overlay | None = None
        self.desktop = desktop.backend(self)
        self._job = 0
        self._keep_windows: list[Gtk.Window] = []

    # -- ciclo de vida -----------------------------------------------------
    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()          # serviço: continua vivo sem janelas
        provider = Gtk.CssProvider()
        if hasattr(provider, "load_from_string"):       # GTK >= 4.12
            provider.load_from_string(CSS)
        else:
            provider.load_from_data(CSS.encode(), -1)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        def add(name, ptype, cb):
            act = Gio.SimpleAction.new(
                name, GLib.VariantType.new(ptype) if ptype else None)
            act.connect("activate", cb)
            self.add_action(act)

        add("show", "(sasii)", self._act_show)
        add("hide", None, self._act_hide)
        add("reveal", "as", lambda _a, p: self.reveal(p.unpack()))
        add("open-editor", "(sas)", self._act_open_editor)
        add("open-file", "as", lambda _a, p: self.open_files(p.unpack()))
        add("open-log", None, lambda *_: self.open_files(
            [str(cache_dir() / "mexerica.log")]))
        add("quit", None, lambda *_: self.quit())
        self.desktop.start()
        log.info("Mexerica %s iniciado (pid %s, %s)", __version__,
                 os.getpid(), self.desktop.name)

    def do_activate(self):
        # Aberto pelo menu de apps: mostra uma janela de status.
        self._show_status()

    # -- roda ----------------------------------------------------------------
    def show_wheel(self, mode: str, paths: list[Path], x: int = 0,
                   y: int = 0) -> None:
        if mode not in (CONVERT, TOOLS, ACTIONS):
            mode = CONVERT
        if self.overlay is None:
            self.overlay = Overlay(self)
        self.overlay.open(mode, paths, x, y)

    def hide_wheel(self) -> None:
        if self.overlay is not None and self.overlay.get_visible():
            self.overlay.close_wheel()

    # -- ações D-Bus -------------------------------------------------------
    def _act_show(self, _action, param):
        mode, uris, x, y = param.unpack()
        self.show_wheel(mode, paths_from_uris(uris), x, y)

    def _act_open_editor(self, _action, param):
        """Abre uma janela de edição sem a roda (scripts, testes):
        gapplication action io.github.rogersocruz.Mexerica open-editor \
            "('img-crop', ['/caminho/foto.jpg'])" """
        op_id, files = param.unpack()
        op = BY_ID.get(op_id)
        paths = [p for p in paths_from_uris(files) if p.exists()]
        if op is None or op.mode != EDITOR or not paths:
            log.warning("open-editor inválido: %s %s", op_id, files)
            return
        open_editor(self, op, paths)

    def _act_hide(self, *_):
        self.hide_wheel()

    # -- execução ----------------------------------------------------------
    def execute(self, op: Op, paths: list[Path]) -> bool:
        log.info("executando %s em %d arquivo(s)", op.id, len(paths))
        if op.mode == ACTION:
            self._run_action(op, paths)
            return False
        if op.mode == EDITOR:
            open_editor(self, op, paths)
            return False
        self._job += 1
        job_id = f"job-{self._job}"
        verb = {CONVERT: "Convertendo", TOOLS: "Processando",
                ACTIONS: "Executando"}[op.group]
        self.notify(job_id, f"{verb}: {op.label}", _caption(paths),
                    progress=True)

        def worker():
            try:
                res = run(op, paths)
            except Exception as exc:  # noqa: BLE001
                log.exception("job falhou")
                GLib.idle_add(self._job_failed, job_id, op, str(exc))
                return
            GLib.idle_add(self._job_done, job_id, op, res, paths)

        threading.Thread(target=worker, daemon=True).start()
        return False

    def _job_done(self, job_id, op: Op, res, paths) -> bool:
        if op.result == TEXT and res.texts:
            text = "\n\n".join(res.texts)
            if op.id == "img-qr":
                self.set_clipboard(text)
                self.notify(job_id, "QR copiado", text[:200])
            else:
                win = TextWindow(self, f"{op.label} — {_caption(paths)}",
                                 text)
                win.present()
                self.desktop.withdraw(job_id)
            if res.errors:
                self._notify_errors(job_id + "-e", op, res.errors)
            return False
        if res.errors and not res.outputs:
            self._notify_errors(job_id, op, res.errors)
            return False
        uris = [Gio.File.new_for_path(str(p)).get_uri() for p in res.outputs]
        first = res.outputs[0]
        title = f"Pronto: {first.name}" if len(res.outputs) == 1 \
            else f"Pronto: {len(res.outputs)} arquivos"
        body = f"Salvo em {_short(first.parent)}"
        if res.errors:
            body += f" — {len(res.errors)} falharam"
        self.notify(job_id, title, body,
                    buttons=[("Mostrar na pasta", "app.reveal", uris),
                             ("Abrir", "app.open-file", uris[:1])],
                    default=("app.reveal", uris))
        return False

    def _job_failed(self, job_id, op, msg) -> bool:
        self._notify_errors(job_id, op, [(None, msg)])
        return False

    def _notify_errors(self, job_id, op, errors) -> None:
        first = errors[0][1].strip().splitlines()
        detail = first[-1] if first else "erro"
        self.notify(job_id, f"Falhou: {op.label}", detail[:240],
                    buttons=[("Ver log", "app.open-log", None)])

    # -- ações de arquivo --------------------------------------------------
    def _run_action(self, op: Op, paths: list[Path]) -> None:
        if op.id == "act-copy-path":
            text = "\n".join(str(p) for p in paths)
            self.set_clipboard(text)
            self.notify("copy-path", "Caminho copiado", text[:200])
        elif op.id == "act-terminal":
            self.open_terminal(paths[0] if paths[0].is_dir()
                               else paths[0].parent)
        elif op.id in ("act-copy-to", "act-move-to"):
            self._choose_folder(paths, move=op.id == "act-move-to")
        elif op.id == "act-float":
            win = FloatWindow(self, paths)
            win.present()

    def _choose_folder(self, paths, move: bool) -> None:
        dialog = Gtk.FileDialog(
            title="Mover para…" if move else "Copiar para…", modal=False)
        dialog.set_initial_folder(Gio.File.new_for_path(str(paths[0].parent)))
        parent = self.desktop.dialog_parent()

        def done(dlg, result):
            if parent is not None:
                parent.destroy()
            try:
                folder = dlg.select_folder_finish(result)
            except GLib.Error:
                return  # cancelado
            dest = Path(folder.get_path())
            threading.Thread(target=self._copy_move,
                             args=(paths, dest, move), daemon=True).start()

        dialog.select_folder(parent, None, done)

    def _copy_move(self, paths, dest: Path, move: bool) -> None:
        outs, errs = [], []
        for p in paths:
            target = unique_path(dest / p.name)
            try:
                if move:
                    shutil.move(str(p), str(target))
                elif p.is_dir():
                    shutil.copytree(p, target, symlinks=True)
                else:
                    shutil.copy2(p, target)
                outs.append(target)
            except OSError as exc:
                errs.append((p, str(exc)))
        uris = [Gio.File.new_for_path(str(o)).get_uri() for o in outs]

        def report():
            verb = "Movido" if move else "Copiado"
            if outs:
                self.notify("copy-move", f"{verb}: {len(outs)} item(ns)",
                            f"para {_short(dest)}"
                            + (f" — {len(errs)} falharam" if errs else ""),
                            buttons=[("Mostrar", "app.reveal", uris)])
            else:
                self.notify("copy-move", "Falhou", errs[0][1][:200])
            return False
        GLib.idle_add(report)

    # -- integração com o desktop (mexerica/desktop/) ----------------------
    def open_terminal(self, folder: Path) -> None:
        self.desktop.open_terminal(folder)

    def set_clipboard(self, text: str) -> None:
        self.desktop.set_clipboard(text)

    def reveal(self, uris) -> None:
        self.desktop.reveal(uris)

    def open_files(self, uris) -> None:
        for u in uris:
            if "://" not in u:
                u = Gio.File.new_for_path(u).get_uri()
            try:
                self.desktop.open_uri(u)
            except (GLib.Error, OSError) as exc:
                log.warning("não abriu %s: %s", u, exc)

    def notify(self, nid, title, body="", buttons=None, default=None,
               progress=False) -> None:
        self.desktop.notify(nid, title, body, buttons, default, progress)

    def _show_status(self) -> None:
        win = Gtk.Window(application=self, title="Mexerica",
                         default_width=460)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                      margin_top=18, margin_bottom=18, margin_start=18,
                      margin_end=18)
        lines = [
            f"<b>Mexerica {__version__}</b> está rodando.",
            "",
            "Arraste um arquivo e <b>segure Shift</b>: aparece a roda de "
            "formatos.",
            "<b>Shift + Alt</b>: ferramentas  ·  <b>Shift + Ctrl</b>: ações",
            "Solte no miolo para cancelar.",
            "",
            self.desktop.status(),
        ]
        missing = [n for n in ("ffmpeg", "magick", "soffice", "pandoc",
                               "qpdf", "gs", "exiftool", "zbarimg",
                               "bsdtar", "pdftoppm")
                   if not T.has(n)]
        if missing:
            lines.append("Programas ausentes (as opções somem da roda): "
                         + ", ".join(missing))
        label = Gtk.Label(use_markup=True, wrap=True, xalign=0)
        label.set_markup("\n".join(lines))
        box.append(label)
        win.set_child(box)
        win.present()


def _short(path: Path) -> str:
    home = str(Path.home())
    s = str(path)
    return "~" + s[len(home):] if s.startswith(home) else s


def main(argv=None) -> int:
    app = MexericaApp()
    return app.run(argv if argv is not None else sys.argv)
