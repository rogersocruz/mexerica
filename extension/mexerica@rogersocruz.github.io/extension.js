// Mexerica — extensão do GNOME Shell
//
// Por que uma extensão: no Wayland, durante um arraste o compositor (Mutter)
// segura o ponteiro e nenhum app enxerga o teclado nem sabe que existe um
// arraste acontecendo. O Shell roda dentro do compositor, então ele pode:
//   1. saber que um arraste começou/terminou (sinais do MetaDnd);
//   2. ler os modificadores (Shift/Alt/Ctrl) a qualquer momento;
//   3. ler a lista de arquivos arrastados (seleção DND do Mutter);
//   4. colocar a janela da roda acima de todas as outras;
//   5. escrever no clipboard em nome do serviço;
//   6. borrar o que está atrás das janelas do serviço (efeito de vidro):
//      um app não enxerga o que está atrás dele, o compositor sim;
//   7. mostrar um ícone na barra superior enquanto o serviço roda
//      (Configurações e Sair), o equivalente da bandeja do Windows.
// A roda em si é desenhada pelo serviço GTK (mexerica), que recebe o drop.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const APP_ID = 'io.github.rogersocruz.Mexerica';
const APP_PATH = '/io/github/rogersocruz/Mexerica';
const OVERLAY_TITLE = 'mexerica-overlay';
const FLOAT_PREFIX = 'Mexerica — ';                 // fica acima das outras
const ROUND_PREFIX = 'Mexerica — Flutuar · ';       // redonda: sem vidro atrás

const POLL_MS = 30;               // leitura dos modificadores durante o arraste
const RELEASE_GRACE_MS = 150;     // soltar Shift por menos que isso não fecha
const END_HIDE_DELAY_MS = 400;    // dá tempo do serviço processar o drop

// Vidro. Overlay: a tela inteira atrás da roda fica fosca e um pouco mais
// escura. Janelas (editores, Flutuar): o fundo atrás delas fica fosco.
const BLUR_EFFECT = 'mexerica-blur';
const OVERLAY_BLUR_RADIUS = 28;
const OVERLAY_DIM = 28;           // % padrão; o usuário muda nas Configurações
const WINDOW_BLUR_RADIUS = 36;
const WINDOW_BLUR_BRIGHTNESS = 0.92;
const BLUR_FADE_MS = 160;

const SHELL_IFACE = `
<node>
  <interface name="io.github.rogersocruz.Mexerica.Shell">
    <method name="SetClipboard">
      <arg type="s" direction="in" name="text"/>
    </method>
    <property name="Version" type="s" access="read"/>
  </interface>
</node>`;

function modeFor(mods) {
    if (!(mods & Clutter.ModifierType.SHIFT_MASK))
        return null;
    if (mods & Clutter.ModifierType.MOD1_MASK)
        return 'tools';
    if (mods & Clutter.ModifierType.CONTROL_MASK)
        return 'actions';
    return 'convert';
}

// Configurações do serviço (~/.config/mexerica/settings.json); daqui só sai
// o quanto a tela escurece atrás da roda.
function overlayBrightness() {
    let dim = OVERLAY_DIM;
    try {
        const file = GLib.build_filenamev([GLib.get_user_config_dir(),
            'mexerica', 'settings.json']);
        const [, bytes] = GLib.file_get_contents(file);
        const value = JSON.parse(new TextDecoder().decode(bytes)).dim;
        if (Number.isFinite(value))
            dim = Math.min(Math.max(value, 0), 90);
    } catch {
        // sem arquivo ou ilegível: o padrão
    }
    return 1 - dim / 100;
}

function isOurs(win) {
    if (!win)
        return false;
    return win.get_gtk_application_id?.() === APP_ID ||
        win.get_wm_class?.() === APP_ID;
}

export default class MexericaExtension extends Extension {
    enable() {
        this._active = false;
        this._generation = 0;
        this._pollId = 0;
        this._hideId = 0;
        this._shownMode = null;
        this._anchor = null;
        this._uris = [];
        this._monitor = -1;
        this._watched = new Map();
        this._blurred = new Map();    // MetaWindow -> {blur, ids}
        this._tracked = new Map();    // janela da roda -> ids de sinais
        this._sentOrigin = null;

        this._dnd = global.backend.get_dnd();
        this._dndIds = [
            this._dnd.connect('dnd-enter', () => this._onDragBegin()),
            this._dnd.connect('dnd-leave', () => this._onDragEnd()),
        ];
        this._windowCreatedId = global.display.connect('window-created',
            (_display, win) => this._onWindowCreated(win));

        this._dbus = Gio.DBusExportedObject.wrapJSObject(SHELL_IFACE, this);
        this._dbus.export(Gio.DBus.session, APP_PATH);

        // ícone na barra superior só enquanto o serviço está no barramento
        this._indicator = null;
        this._watchId = Gio.bus_watch_name(Gio.BusType.SESSION, APP_ID,
            Gio.BusNameWatcherFlags.NONE,
            () => this._showIndicator(), () => this._hideIndicator());
    }

    disable() {
        this._stopPoll();
        this._clearHideTimer();
        if (this._shownMode)
            this._callApp('hide', null);
        this._dndIds?.forEach(id => this._dnd.disconnect(id));
        this._dndIds = null;
        this._dnd = null;
        if (this._windowCreatedId)
            global.display.disconnect(this._windowCreatedId);
        this._windowCreatedId = 0;
        for (const [win, ids] of this._watched)
            ids.forEach(id => win.disconnect(id));
        this._watched = null;
        for (const win of [...this._blurred.keys()])
            this._unblurWindow(win);
        this._blurred = null;
        for (const [win, ids] of this._tracked)
            ids.forEach(id => win.disconnect(id));
        this._tracked = null;
        for (const actor of global.get_window_actors())
            actor.remove_effect_by_name(BLUR_EFFECT);
        this._dbus?.unexport();
        this._dbus = null;
        if (this._watchId)
            Gio.bus_unwatch_name(this._watchId);
        this._watchId = 0;
        this._hideIndicator();
    }

    // ---- ícone na barra superior ----------------------------------------
    _showIndicator() {
        if (this._indicator)
            return;
        const button = new PanelMenu.Button(0.0, 'Mexerica', false);
        button.add_child(new St.Icon({
            gicon: Gio.ThemedIcon.new(APP_ID),
            style_class: 'system-status-icon',
        }));
        const item = (label, action) => {
            const entry = new PopupMenu.PopupMenuItem(label);
            entry.connect('activate', () => this._callApp(action, null));
            button.menu.addMenuItem(entry);
        };
        item('Abrir a Mexerica', 'home');
        item('Configurações…', 'settings');
        item('Abrir o log', 'open-log');
        button.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        item('Sair da Mexerica', 'quit');
        Main.panel.addToStatusArea(this.uuid, button);
        this._indicator = button;
    }

    _hideIndicator() {
        this._indicator?.destroy();
        this._indicator = null;
    }

    // ---- D-Bus exportado para o serviço -------------------------------
    SetClipboard(text) {
        St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text);
    }

    get Version() {
        return String(this.metadata.version ?? '0');
    }

    // ---- arraste -------------------------------------------------------
    _onDragBegin() {
        this._clearHideTimer();
        this._stopPoll();
        this._generation++;
        this._active = true;
        this._shownMode = null;
        this._anchor = null;
        this._releasedAt = 0;
        this._uris = [];
        if (!this._dragHasFiles())
            return;
        this._fetchUris(this._generation);
        this._pollId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, POLL_MS,
            () => this._tick());
    }

    _onDragEnd() {
        this._active = false;
        this._stopPoll();
        if (!this._shownMode)
            return;
        this._clearHideTimer();
        this._hideId = GLib.timeout_add(GLib.PRIORITY_DEFAULT,
            END_HIDE_DELAY_MS, () => {
                this._hideId = 0;
                this._hide();
                return GLib.SOURCE_REMOVE;
            });
    }

    _tick() {
        if (!this._active) {
            this._pollId = 0;
            return GLib.SOURCE_REMOVE;
        }
        const [x, y, mods] = global.get_pointer();
        const mode = modeFor(mods);
        if (mode) {
            this._releasedAt = 0;
            if (!this._anchor)
                this._anchor = [x, y];
            if (mode !== this._shownMode)
                this._show(mode);
        } else if (this._shownMode) {
            const now = GLib.get_monotonic_time();
            if (!this._releasedAt)
                this._releasedAt = now;
            else if (now - this._releasedAt > RELEASE_GRACE_MS * 1000)
                this._hide();
        }
        return GLib.SOURCE_CONTINUE;
    }

    _stopPoll() {
        if (this._pollId)
            GLib.source_remove(this._pollId);
        this._pollId = 0;
    }

    _clearHideTimer() {
        if (this._hideId)
            GLib.source_remove(this._hideId);
        this._hideId = 0;
    }

    _dragHasFiles() {
        try {
            const mimes = global.display.get_selection()
                .get_mimetypes(Meta.SelectionType.SELECTION_DND);
            return mimes.includes('text/uri-list') ||
                mimes.includes('application/vnd.portal.filetransfer') ||
                mimes.includes('application/vnd.portal.files');
        } catch (e) {
            console.warn(`Mexerica: não li os tipos do arraste: ${e}`);
            return true;   // na dúvida, o serviço decide
        }
    }

    _fetchUris(generation) {
        const selection = global.display.get_selection();
        const stream = Gio.MemoryOutputStream.new_resizable();
        selection.transfer_async(Meta.SelectionType.SELECTION_DND,
            'text/uri-list', -1, stream, null, (sel, res) => {
                try {
                    sel.transfer_finish(res);
                    stream.close(null);
                    if (generation !== this._generation)
                        return;
                    const bytes = stream.steal_as_bytes();
                    const text = new TextDecoder().decode(bytes.toArray());
                    this._uris = text.split(/\r?\n/)
                        .map(l => l.trim())
                        .filter(l => l && !l.startsWith('#'));
                    if (this._shownMode)
                        this._show(this._shownMode);  // atualiza a roda
                } catch (e) {
                    console.warn(`Mexerica: não li os arquivos: ${e}`);
                }
            });
    }

    // ---- conversa com o serviço ---------------------------------------
    _show(mode, ov = this._overlayWindow()) {
        this._shownMode = mode;
        const [ax, ay] = this._anchor ?? global.get_pointer();
        this._monitor = global.display.get_current_monitor();
        // Coordenadas locais da janela da roda. Ela é maximizada (fica
        // abaixo da barra superior); antes de existir, vale o monitor.
        const origin = ov && ov.get_monitor() === this._monitor
            ? ov.get_frame_rect()
            : global.display.get_monitor_geometry(this._monitor);
        this._sentOrigin = [origin.x, origin.y];
        const param = new GLib.Variant('(sasii)', [
            mode, this._uris, Math.round(ax - origin.x),
            Math.round(ay - origin.y),
        ]);
        this._callApp('show', param);
        this._raiseOverlay();
    }

    _overlayWindow() {
        for (const actor of global.get_window_actors()) {
            const win = actor.get_meta_window();
            if (isOurs(win) && win.get_title() === OVERLAY_TITLE)
                return win;
        }
        return null;
    }

    _resendIfMoved(win) {
        // a janela foi posicionada depois do show: corrige o centro
        if (!this._shownMode || !this._sentOrigin)
            return;
        const f = win.get_frame_rect();
        if (f.x !== this._sentOrigin[0] || f.y !== this._sentOrigin[1])
            this._show(this._shownMode, win);
    }

    _hide() {
        if (!this._shownMode)
            return;
        this._shownMode = null;
        this._anchor = null;
        this._callApp('hide', null);
    }

    _callApp(action, param) {
        const params = param ? [param] : [];
        Gio.DBus.session.call(APP_ID, APP_PATH,
            'org.freedesktop.Application', 'ActivateAction',
            new GLib.Variant('(sava{sv})', [action, params, {}]),
            null, Gio.DBusCallFlags.NONE, 3000, null,
            (conn, res) => {
                try {
                    conn.call_finish(res);
                } catch (e) {
                    console.warn(`Mexerica: serviço não respondeu (${action}): ${e.message}`);
                }
            });
    }

    // ---- janelas do serviço -------------------------------------------
    _pin(win) {
        if (!isOurs(win))
            return false;
        const title = win.get_title() ?? '';
        if (!title)
            return false;
        if (title === OVERLAY_TITLE) {
            if (this._monitor >= 0 && win.get_monitor() !== this._monitor)
                win.move_to_monitor(this._monitor);
            if (!win.is_above())
                win.make_above();
            win.raise();
            this._blurOverlay(win);
            this._trackOverlay(win);
        } else {
            if (title.startsWith(FLOAT_PREFIX) && !win.is_above())
                win.make_above();
            Main.activateWindow(win);
            if (!title.startsWith(ROUND_PREFIX))
                this._blurWindow(win);
        }
        return true;
    }

    // ---- vidro ----------------------------------------------------------
    // Shell.BlurEffect no modo BACKGROUND borra o que já foi pintado atrás
    // do ator. A janela do serviço é translúcida, então o borrão aparece
    // através dela.
    _withActor(win, fn, tries = 10) {
        const actor = win.get_compositor_private();
        if (actor) {
            fn(actor);
            return;
        }
        if (tries > 0) {
            GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                this._withActor(win, fn, tries - 1);
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    _blurOverlay(win) {
        // tela cheia e sem sombra: o efeito vai direto no ator da janela
        this._withActor(win, actor => {
            if (actor.get_effect(BLUR_EFFECT))
                return;
            actor.add_effect_with_name(BLUR_EFFECT, new Shell.BlurEffect({
                mode: Shell.BlurMode.BACKGROUND, radius: 0, brightness: 1,
            }));
            const ease = {
                duration: BLUR_FADE_MS,
                mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            };
            actor.ease_property(`@effects.${BLUR_EFFECT}.radius`,
                OVERLAY_BLUR_RADIUS, ease);
            actor.ease_property(`@effects.${BLUR_EFFECT}.brightness`,
                overlayBrightness(), ease);
        });
    }

    _blurWindow(win) {
        // Janela comum: o buffer inclui a sombra do GTK, então o borrão
        // fica num ator filho, do tamanho da parte visível, pintado antes
        // da janela. Como filho, acompanha movimento e animações.
        if (this._blurred.has(win))
            return;
        this._withActor(win, actor => {
            if (!this._blurred || this._blurred.has(win))
                return;
            const blur = new Clutter.Actor({reactive: false});
            blur.add_effect_with_name(BLUR_EFFECT, new Shell.BlurEffect({
                mode: Shell.BlurMode.BACKGROUND,
                radius: WINDOW_BLUR_RADIUS,
                brightness: WINDOW_BLUR_BRIGHTNESS,
            }));
            actor.insert_child_below(blur, null);
            const sync = () => {
                const f = win.get_frame_rect();
                const b = win.get_buffer_rect();
                blur.set_position(f.x - b.x, f.y - b.y);
                blur.set_size(f.width, f.height);
            };
            sync();
            this._blurred.set(win, {
                blur,
                ids: [
                    win.connect('size-changed', sync),
                    win.connect('unmanaged', () => this._unblurWindow(win)),
                ],
            });
        });
    }

    _unblurWindow(win) {
        const entry = this._blurred?.get(win);
        if (!entry)
            return;
        entry.ids.forEach(id => win.disconnect(id));
        entry.blur.destroy();
        this._blurred.delete(win);
    }

    _raiseOverlay() {
        const win = this._overlayWindow();
        if (win)
            this._pin(win);
    }

    _trackOverlay(win) {
        if (this._tracked.has(win))
            return;
        const ids = [
            win.connect('position-changed', () => this._resendIfMoved(win)),
            win.connect('size-changed', () => this._resendIfMoved(win)),
        ];
        ids.push(win.connect('unmanaged', () => {
            ids.forEach(id => win.disconnect(id));
            this._tracked.delete(win);
        }));
        this._tracked.set(win, ids);
        this._resendIfMoved(win);
    }

    _onWindowCreated(win) {
        if (this._pin(win))
            return;
        if (win.get_wm_class() && !isOurs(win))
            return;   // janela de outro app: nada a fazer
        // app_id e título podem chegar depois do window-created
        const unwatch = () => {
            const ids = this._watched?.get(win);
            if (!ids)
                return;
            ids.forEach(id => win.disconnect(id));
            this._watched.delete(win);
        };
        const retry = () => {
            if (this._pin(win))
                unwatch();
        };
        this._watched.set(win, [
            win.connect('notify::wm-class', retry),
            win.connect('notify::title', retry),
            win.connect('shown', retry),
            win.connect('unmanaged', unwatch),
        ]);
    }
}
