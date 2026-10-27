#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
UUID=mexerica@rogersocruz.github.io
gapplication action io.github.rogersocruz.Mexerica quit 2>/dev/null || true
gnome-extensions disable "$UUID" 2>/dev/null || true
make uninstall \
    PREFIX="$HOME/.local" \
    AUTOSTARTDIR="$HOME/.config/autostart" \
    EXTDIR="$HOME/.local/share/gnome-shell/extensions/$UUID"
echo "Removido. Log e cache em ~/.cache/mexerica (apague se quiser)."
