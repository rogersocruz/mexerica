#!/usr/bin/env bash
# Instalação de usuário (sem sudo) em ~/.local
set -euo pipefail
cd "$(dirname "$0")"
UUID=mexerica@rogersocruz.github.io
BIN="$HOME/.local/bin/mexerica"

if ! python3 -c 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk' 2>/dev/null; then
    echo "Falta PyGObject/GTK 4. No Arch: sudo pacman -S python-gobject gtk4" >&2
    exit 1
fi

make install \
    PREFIX="$HOME/.local" \
    AUTOSTARTDIR="$HOME/.config/autostart" \
    EXTDIR="$HOME/.local/share/gnome-shell/extensions/$UUID"

# habilita a extensão (vale no próximo login; no Wayland o Shell não recarrega)
python3 - "$UUID" <<'PY'
import ast, subprocess, sys
uuid = sys.argv[1]
get = lambda k: subprocess.run(["gsettings", "get", "org.gnome.shell", k],
                               capture_output=True, text=True).stdout.strip()
raw = get("enabled-extensions").removeprefix("@as ")
cur = ast.literal_eval(raw) if raw else []
if uuid not in cur:
    cur.append(uuid)
    subprocess.run(["gsettings", "set", "org.gnome.shell",
                    "enabled-extensions", str(cur)], check=True)
subprocess.run(["gsettings", "set", "org.gnome.shell",
                "disable-user-extensions", "false"], check=False)
PY

# (re)inicia o serviço
gapplication action io.github.rogersocruz.Mexerica quit 2>/dev/null || true
setsid "$BIN" --gapplication-service >/dev/null 2>&1 < /dev/null &

echo
"$BIN" doctor || true
cat <<MSG

Instalado. Falta um passo: SAIA E ENTRE DE NOVO NA SESSÃO para o GNOME
Shell carregar a extensão. Depois: arraste um arquivo e segure Shift.

Opcionais no Arch (as opções aparecem na roda conforme instalar):
  sudo pacman -S --needed ffmpeg imagemagick libheif librsvg poppler qpdf \\
      ghostscript perl-image-exiftool zbar pandoc-cli libreoffice-fresh
MSG
