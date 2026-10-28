"""Backend do GNOME: quem percebe o arraste é a extensão do Shell
(extension/), que chama a ação D-Bus `show` do serviço, põe a roda acima
de tudo, borra o fundo e mostra o ícone na barra superior enquanto o
serviço roda. Aqui fica o resto da conversa com o desktop.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk  # noqa: E402

from ..engine import tools as T  # noqa: E402

log = logging.getLogger("mexerica")

SHELL_BUS = "org.gnome.Shell"
SHELL_PATH = "/io/github/rogersocruz/Mexerica"
SHELL_IFACE = "io.github.rogersocruz.Mexerica.Shell"
EXT_UUID = "mexerica@rogersocruz.github.io"


class GnomeDesktop:
    name = "GNOME"
    overlay_dim = 0.0        # quem escurece a tela atrás da roda é a extensão

    def __init__(self, app):
        self.app = app

    def start(self) -> None:
        pass                 # o arraste chega pela extensão

    def stop(self) -> None:
        pass

    # -- roda ----------------------------------------------------------------
    def show_overlay(self, win) -> None:
        # Fallback para quando o maximizar não é aplicado (sem gerenciador
        # de janelas); no GNOME o maximizar manda.
        monitors = Gdk.Display.get_default().get_monitors()
        if monitors.get_n_items():
            geo = monitors.get_item(0).get_geometry()
            win.set_default_size(geo.width, geo.height)
        # Maximizada, não tela cheia: o Mutter pinta um fundo preto
        # atrás de janelas Wayland em tela cheia, e a roda precisa do
        # fundo transparente. A extensão converte as coordenadas para a
        # posição real da janela (abaixo da barra superior).
        win.maximize()
        win.present()

    def wheel_center(self, win, w: float, h: float):
        return None          # a extensão manda o centro na ação `show`

    def dialog_parent(self):
        return None

    def drag_source(self, widget, paths: list[Path], done) -> None:
        """Arrastar `widget` leva os arquivos (janela Flutuar)."""
        def prepare(*_):
            files = [Gio.File.new_for_path(str(p)) for p in paths]
            return Gdk.ContentProvider.new_for_value(
                GObject.Value(Gdk.FileList, Gdk.FileList.new_from_array(files)))
        src = Gtk.DragSource(actions=Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        src.connect("prepare", prepare)
        src.connect("drag-end", lambda *_: done())
        widget.add_controller(src)

    # -- arquivos como o gerenciador de arquivos mostra ----------------------
    def file_icon(self, path: Path, size: int):
        """Miniatura (se o Nautilus já gerou) ou o ícone do tipo (Gio.Icon)."""
        try:
            info = Gio.File.new_for_path(str(path)).query_info(
                "standard::icon,thumbnail::path", Gio.FileQueryInfoFlags.NONE,
                None)
        except GLib.Error:
            return None
        thumb = info.get_attribute_byte_string("thumbnail::path")
        if thumb:
            try:
                return Gdk.Texture.new_from_filename(thumb)
            except GLib.Error:
                pass
        return info.get_icon()

    def display_name(self, path: Path) -> str:
        try:
            return Gio.File.new_for_path(str(path)).query_info(
                "standard::display-name", Gio.FileQueryInfoFlags.NONE,
                None).get_display_name()
        except GLib.Error:
            return Path(path).name

    # -- iniciar com o sistema (autostart do XDG) ----------------------------
    def autostart(self) -> bool | None:
        src = _autostart_source()
        if src is None:
            return None
        return "X-GNOME-Autostart-enabled=false" not in src.read_text()

    def set_autostart(self, enabled: bool) -> None:
        """Grava a escolha na cópia do usuário (~/.config/autostart), que
        vale por cima da do sistema."""
        src = _autostart_source()
        if src is None:
            return
        lines = [ln for ln in src.read_text().splitlines()
                 if not ln.startswith("X-GNOME-Autostart-enabled=")]
        lines.append(f"X-GNOME-Autostart-enabled={str(enabled).lower()}")
        _USER_AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
        _USER_AUTOSTART.write_text("\n".join(lines) + "\n")

    # -- sistema -------------------------------------------------------------
    def set_clipboard(self, text: str) -> None:
        """No Wayland, um serviço sem foco não consegue escrever no
        clipboard; a extensão do Shell faz isso por nós."""
        try:
            _session().call_sync(
                SHELL_BUS, SHELL_PATH, SHELL_IFACE, "SetClipboard",
                GLib.Variant("(s)", (text,)), None,
                Gio.DBusCallFlags.NONE, 1000, None)
            return
        except GLib.Error as exc:
            log.info("clipboard via extensão indisponível: %s", exc.message)
        if T.which("wl-copy"):
            subprocess.run(["wl-copy"], input=text, text=True, check=False)
            return
        display = Gdk.Display.get_default()
        if display:
            display.get_clipboard().set(text)

    def reveal(self, uris) -> None:
        try:
            _session().call_sync(
                "org.freedesktop.FileManager1", "/org/freedesktop/FileManager1",
                "org.freedesktop.FileManager1", "ShowItems",
                GLib.Variant("(ass)", (list(uris), "")), None,
                Gio.DBusCallFlags.NONE, 3000, None)
        except GLib.Error:
            parent = Gio.File.new_for_uri(uris[0]).get_parent()
            Gio.AppInfo.launch_default_for_uri(parent.get_uri(), None)

    def open_uri(self, uri: str) -> None:
        Gio.AppInfo.launch_default_for_uri(uri, None)

    def open_terminal(self, folder: Path) -> None:
        d = str(folder)
        candidates = [
            ["kgx", f"--working-directory={d}"],
            ["ptyxis", "--new-window", f"--working-directory={d}"],
            ["gnome-terminal", f"--working-directory={d}"],
            ["kitty", "--directory", d],
            ["alacritty", "--working-directory", d],
            ["foot", f"--working-directory={d}"],
            ["wezterm", "start", "--cwd", d],
            ["konsole", "--workdir", d],
            ["xdg-terminal-exec"],
            ["xterm"],
        ]
        term = os.environ.get("TERMINAL")
        if term:
            candidates.insert(0, [term])
        for argv in candidates:
            if shutil.which(argv[0]):
                subprocess.Popen(argv, cwd=d, start_new_session=True,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return
        self.app.notify("term", "Nenhum terminal encontrado",
                        "Instale gnome-console (kgx) ou defina $TERMINAL")

    def notify(self, nid, title, body="", buttons=None, default=None,
               progress=False) -> None:
        n = Gio.Notification.new(title)
        if body:
            n.set_body(body)
        n.set_priority(Gio.NotificationPriority.LOW if progress
                       else Gio.NotificationPriority.NORMAL)
        for label, action, target in buttons or []:
            if target is None:
                n.add_button(label, action)
            else:
                n.add_button_with_target(label, action,
                                         GLib.Variant("as", target))
        if default:
            n.set_default_action_and_target(default[0],
                                            GLib.Variant("as", default[1]))
        self.app.send_notification(nid, n)

    def withdraw(self, nid) -> None:
        self.app.withdraw_notification(nid)

    def status(self) -> str:
        return f"Extensão do GNOME Shell: <b>{_extension_state()}</b>"


_DESKTOP_FILE = "io.github.rogersocruz.Mexerica.desktop"
_USER_AUTOSTART = Path(os.environ.get("XDG_CONFIG_HOME")
                       or Path.home() / ".config") / "autostart" / _DESKTOP_FILE


def _autostart_source() -> Path | None:
    """O .desktop de autostart que vale: o do usuário ou o do sistema."""
    for path in (_USER_AUTOSTART, Path("/etc/xdg/autostart", _DESKTOP_FILE),
                 Path("/usr/local/etc/xdg/autostart", _DESKTOP_FILE)):
        if path.exists():
            return path
    return None


def _session() -> Gio.DBusConnection:
    return Gio.bus_get_sync(Gio.BusType.SESSION, None)


def _extension_state() -> str:
    try:
        reply = _session().call_sync(
            "org.gnome.Shell.Extensions", "/org/gnome/Shell/Extensions",
            "org.gnome.Shell.Extensions", "GetExtensionInfo",
            GLib.Variant("(s)", (EXT_UUID,)), None,
            Gio.DBusCallFlags.NONE, 1000, None)
        info = reply.unpack()[0]
        if not info:
            return "não instalada"
        state = int(info.get("state", 0))
        return {1: "ativa", 2: "desativada", 3: "com erro",
                4: "desatualizada", 6: "inicializada"}.get(state,
                                                           f"estado {state}")
    except GLib.Error:
        return "GNOME Shell não encontrado"
