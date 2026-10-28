// Teste da lógica da extensão sem GNOME Shell: troca os imports por mocks
// e simula o arraste (sinais do MetaDnd + modificadores + relógio).
// Rodar: node tests/extension_logic.test.mjs
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = readFileSync(path.join(here,
    '../extension/mexerica@rogersocruz.github.io/extension.js'), 'utf8');

// ---------- mocks --------------------------------------------------------
const SHIFT = 1, CTRL = 4, ALT = 8;
let now = 0;                     // microssegundos
const timers = [];
const calls = [];                // chamadas D-Bus ao serviço
let clipboard = null;

const GLib = {
    PRIORITY_DEFAULT: 0, SOURCE_REMOVE: false, SOURCE_CONTINUE: true,
    get_monotonic_time: () => now,
    idle_add(_p, fn) { return this.timeout_add(_p, 0, fn); },
    timeout_add(_p, ms, fn) {
        const t = {due: now + ms * 1000, ms, fn, alive: true};
        timers.push(t);
        return timers.length;
    },
    source_remove(id) { timers[id - 1].alive = false; },
    Variant: class { constructor(sig, v) { this.sig = sig; this.v = v; } },
    // configurações do serviço (~/.config/mexerica/settings.json)
    get_user_config_dir: () => '/home/r/.config',
    build_filenamev: parts => parts.join('/'),
    file_get_contents(file) {
        if (settingsJson === null || file !== '/home/r/.config/mexerica/settings.json')
            throw new Error('sem arquivo');
        return [true, new TextEncoder().encode(settingsJson)];
    },
};
let settingsJson = null;
function advance(ms) {
    const end = now + ms * 1000;
    for (;;) {
        const t = timers.filter(x => x.alive && x.due <= end)
            .sort((a, b) => a.due - b.due)[0];
        if (!t)
            break;
        now = t.due;
        if (t.fn())
            t.due = now + t.ms * 1000;
        else
            t.alive = false;
    }
    now = end;
}

function emitter() {
    const h = new Map(); let n = 0;
    return {
        connect(sig, fn) { h.set(++n, [sig, fn]); return n; },
        disconnect(id) { h.delete(id); },
        emit(sig, ...a) { for (const [s, fn] of [...h.values()]) if (s === sig) fn(this, ...a); },
        count() { return h.size; },
    };
}

const dnd = emitter();
const display = Object.assign(emitter(), {
    get_selection: () => ({
        get_mimetypes: () => ['text/uri-list', 'text/plain'],
        transfer_async: (_t, _m, _s, stream, _c, cb) => {
            stream.data = 'file:///home/r/foto.png\r\n# comentário\r\nfile:///home/r/b.png\r\n';
            cb({transfer_finish: () => true}, null);
        },
    }),
    get_current_monitor: () => 1,
    get_monitor_geometry: () => ({x: 1920, y: 0, width: 1920, height: 1080}),
});
let pointer = [2500, 400, 0];
const windows = [];
globalThis.global = {
    backend: {get_dnd: () => dnd},
    display,
    get_pointer: () => pointer,
    get_window_actors: () => windows.map(w => w.actor),
};

const Gio = {
    DBusCallFlags: {NONE: 0},
    DBus: {session: {call(dest, p, iface, method, params, _r, _f, _t, _c, cb) {
        calls.push({dest, iface, method, action: params.v[0], args: params.v[1][0]?.v});
        cb({call_finish: () => true}, null);
    }}},
    DBusExportedObject: {wrapJSObject: (_x, obj) => ({export() {}, unexport() {}, obj})},
    MemoryOutputStream: {new_resizable: () => ({
        data: '', close() {},
        steal_as_bytes() { const d = this.data; return {toArray: () => new TextEncoder().encode(d)}; },
    })},
    // o serviço entra e sai do barramento
    BusType: {SESSION: 1}, BusNameWatcherFlags: {NONE: 0},
    bus_watch_name(_t, name, _f, appeared, vanished) {
        watcher = {name, appeared, vanished, alive: true};
        return 7;
    },
    bus_unwatch_name(id) { if (id === 7) watcher.alive = false; },
    ThemedIcon: {new: name => ({name})},
};
let watcher = null;
// barra superior
const statusArea = new Map();
const PanelMenu = {Button: class {
    constructor(_align, name) {
        this.name = name; this.children = [];
        this.menu = {items: [], addMenuItem(i) { this.items.push(i); }};
    }
    add_child(c) { this.children.push(c); }
    destroy() {
        this.destroyed = true;
        for (const [k, v] of statusArea)
            if (v === this) statusArea.delete(k);
    }
}};
const PopupMenu = {
    PopupMenuItem: class {
        constructor(label) { this.label = label; this.handlers = []; }
        connect(sig, fn) { this.handlers.push([sig, fn]); }
        activate() { this.handlers.filter(([s]) => s === 'activate').forEach(([, fn]) => fn()); }
    },
    PopupSeparatorMenuItem: class { constructor() { this.separator = true; } },
};
// atores do compositor: só o necessário para o vidro
class FakeActor {
    constructor() { this.effects = new Map(); this.children = []; this.eased = {}; }
    add_effect_with_name(name, fx) { this.effects.set(name, fx); }
    get_effect(name) { return this.effects.get(name) ?? null; }
    remove_effect_by_name(name) { this.effects.delete(name); }
    ease_property(prop, value) { this.eased[prop] = value; }
    insert_child_below(child) { this.children.unshift(child); child.parent = this; }
    set_position(x, y) { this.pos = [x, y]; }
    set_size(w, h) { this.size = [w, h]; }
    destroy() {
        this.destroyed = true;
        this.parent.children = this.parent.children.filter(c => c !== this);
    }
}
const Clutter = {
    ModifierType: {SHIFT_MASK: SHIFT, CONTROL_MASK: CTRL, MOD1_MASK: ALT},
    AnimationMode: {EASE_OUT_QUAD: 1},
    Actor: FakeActor,
};
const Shell = {BlurMode: {BACKGROUND: 1},
    BlurEffect: class { constructor(p) { Object.assign(this, p); } }};
const Meta = {SelectionType: {SELECTION_DND: 2}};
const St = {Clipboard: {get_default: () => ({set_text: (_t, s) => { clipboard = s; }})},
    ClipboardType: {CLIPBOARD: 1},
    Icon: class { constructor(p) { Object.assign(this, p); } }};
const activated = [];
const Main = {activateWindow: w => activated.push(w),
    panel: {addToStatusArea: (role, button) => statusArea.set(role, button)}};
class Extension {
    constructor() { this.metadata = {version: 1}; this.uuid = 'mexerica@rogersocruz.github.io'; }
}

// ---------- carrega a extensão com os mocks ------------------------------
const body = src
    .replace(/^import .*$/gm, '')
    .replace('export default class', 'return class');
// eslint-disable-next-line no-new-func
const Ext = new Function('Clutter', 'Gio', 'GLib', 'Meta', 'Shell', 'St',
    'Extension', 'Main', 'PanelMenu', 'PopupMenu', body)(
    Clutter, Gio, GLib, Meta, Shell, St, Extension, Main, PanelMenu, PopupMenu);

const ext = new Ext();
ext.enable();

function fakeWindow(title, wmClass = 'io.github.rogersocruz.Mexerica') {
    const actor = new FakeActor();
    const win = Object.assign(emitter(), {
        above: false, raised: 0, monitor: 0, actor,
        get_compositor_private: () => actor,
        // buffer com 20 px de sombra do GTK em volta da parte visível
        get_frame_rect: () => ({x: 120, y: 80, width: 600, height: 400}),
        get_buffer_rect: () => ({x: 100, y: 60, width: 640, height: 440}),
        get_gtk_application_id: () => wmClass, get_wm_class: () => wmClass,
        get_title() { return title; }, is_above() { return this.above; },
        make_above() { this.above = true; }, raise() { this.raised++; },
        get_monitor() { return this.monitor; }, move_to_monitor(m) { this.monitor = m; },
    });
    actor.get_meta_window = () => win;
    return win;
}

// ---------- 1. arraste sem Shift: nada acontece --------------------------
dnd.emit('dnd-enter');
advance(300);
assert.equal(calls.length, 0, 'sem Shift não chama o serviço');

// ---------- 2. Shift -> roda de conversão, centrada no ponteiro ----------
pointer = [2500, 400, SHIFT];
advance(40);
assert.equal(calls.length, 1);
assert.equal(calls[0].action, 'show');
assert.deepEqual(calls[0].args, ['convert',
    ['file:///home/r/foto.png', 'file:///home/r/b.png'], 580, 400],
'modo, URIs (sem comentário) e coordenadas locais do monitor 1');

// ---------- 3. janela do overlay é fixada acima e no monitor certo -------
const ov = fakeWindow('mexerica-overlay');
// maximizada no monitor 1, abaixo de uma barra superior de 32 px
ov.get_frame_rect = () => ({x: 1920, y: 32, width: 1920, height: 1048});
display.emit('window-created', ov);
assert.ok(ov.above && ov.raised === 1 && ov.monitor === 1);
windows.push(ov);
assert.equal(calls.at(-1).action, 'show', 'janela posicionada: reenvia o centro');
assert.deepEqual(calls.at(-1).args.slice(2), [580, 400 - 32],
    'coordenadas locais à janela (abaixo da barra)');
const ovBlur = ov.actor.get_effect('mexerica-blur');
assert.ok(ovBlur && ovBlur.mode === Shell.BlurMode.BACKGROUND,
    'tela atrás da roda fica borrada');
assert.ok(ov.actor.eased['@effects.mexerica-blur.radius'] > 0, 'borrão entra animado');
assert.equal(ov.actor.eased['@effects.mexerica-blur.brightness'], 0.72,
    'sem configurações: escurece 28%');

// ---------- 4. + Alt -> ferramentas, mesmo centro ------------------------
pointer = [2700, 600, SHIFT | ALT];
advance(40);
const last = calls.at(-1);
assert.equal(last.args[0], 'tools');
assert.equal(last.args[2], 580, 'centro não muda ao trocar de modo');
assert.equal(last.args[3], 368);
pointer = [2700, 600, SHIFT | CTRL];
advance(40);
assert.equal(calls.at(-1).args[0], 'actions');

// ---------- 5. soltar Shift brevemente não fecha; segurar solto fecha ----
pointer = [2700, 600, 0];
advance(100);
assert.notEqual(calls.at(-1).action, 'hide', 'tolerância de 150 ms');
pointer = [2700, 600, SHIFT | CTRL];
advance(40);
pointer = [2700, 600, 0];
advance(250);
assert.equal(calls.at(-1).action, 'hide');
const n = calls.length;

// ---------- 6. Shift de novo: recentra onde está o ponteiro --------------
pointer = [3000, 100, SHIFT];
advance(40);
assert.equal(calls.at(-1).action, 'show');
assert.equal(calls.at(-1).args[2], 3000 - 1920);
assert.ok(calls.length > n);

// ---------- 7. fim do arraste: esconde depois do atraso ------------------
dnd.emit('dnd-leave');
advance(100);
assert.equal(calls.at(-1).action, 'show', 'ainda não escondeu');
advance(400);
assert.equal(calls.at(-1).action, 'hide');

// ---------- 8. janela de app alheio não é observada ----------------------
const other = fakeWindow('Arquivos', 'org.gnome.Nautilus');
display.emit('window-created', other);
assert.equal(other.count(), 0);

// ---------- 9. janela nossa sem título: observa e fixa quando chegar -----
let t = '';
const late = fakeWindow('', 'io.github.rogersocruz.Mexerica');
late.get_title = () => t;
display.emit('window-created', late);
assert.ok(late.count() > 0);
t = 'Mexerica — foto.png';
late.emit('notify::title');
assert.ok(late.above, 'janela flutuante fica acima');
assert.equal(late.count(), 2, 'parou de observar (sobram size-changed e unmanaged do vidro)');
assert.ok(activated.includes(late));
const glass = late.actor.children[0];
assert.ok(glass?.get_effect('mexerica-blur'), 'janela ganha vidro atrás');
assert.deepEqual([glass.pos, glass.size], [[20, 20], [600, 400]],
    'vidro só na parte visível, sem a sombra');
late.emit('unmanaged');
assert.ok(glass.destroyed && late.count() === 0, 'janela fechada: vidro sai');

// ---------- 10. clipboard via D-Bus e disable limpo -----------------------
ext.SetClipboard('/home/r/foto.png');
assert.equal(clipboard, '/home/r/foto.png');

// ---------- 12. ícone na barra superior enquanto o serviço roda -----------
assert.equal(watcher.name, 'io.github.rogersocruz.Mexerica');
assert.equal(statusArea.size, 0, 'serviço fora do ar: sem ícone');
watcher.appeared();
const button = statusArea.get('mexerica@rogersocruz.github.io');
assert.ok(button, 'serviço no ar: ícone na barra');
assert.equal(button.children[0].gicon.name, 'io.github.rogersocruz.Mexerica');
assert.deepEqual(button.menu.items.map(i => i.label ?? '—'),
    ['Configurações…', 'Abrir o log', '—', 'Sair da Mexerica']);
button.menu.items[0].activate();
assert.equal(calls.at(-1).action, 'settings', 'abre as Configurações no serviço');
button.menu.items[3].activate();
assert.equal(calls.at(-1).action, 'quit');
watcher.vanished();
assert.ok(button.destroyed && statusArea.size === 0, 'serviço saiu: ícone some');
watcher.appeared();

// ---------- 13. escurecer vem das Configurações ---------------------------
settingsJson = '{"dim": 40, "style": "oceano"}';
const ov2 = fakeWindow('mexerica-overlay');
display.emit('window-created', ov2);
assert.ok(Math.abs(ov2.actor.eased['@effects.mexerica-blur.brightness'] - 0.6) < 1e-9);
ov2.emit('unmanaged');

// ---------- 14. Flutuar é redonda: acima, mas sem vidro retangular --------
const bubble = fakeWindow('Mexerica — Flutuar · foto.png');
display.emit('window-created', bubble);
assert.ok(bubble.above && activated.includes(bubble));
assert.equal(bubble.actor.children.length, 0, 'sem borrão atrás da bolha');
// ---------- 11. disable tira todo o vidro ---------------------------------
const ed = fakeWindow('Editar — foto.png');
display.emit('window-created', ed);
windows.push(ed);
assert.equal(ed.actor.children.length, 1);
ext.disable();
assert.equal(dnd.count(), 0);
assert.equal(ed.actor.children.length, 0, 'vidro das janelas removido');
assert.equal(ov.actor.get_effect('mexerica-blur'), null, 'efeito do overlay removido');
assert.equal(ed.count(), 0);
assert.equal(ov.count(), 0, 'sinais da janela da roda soltos');
assert.ok(!watcher.alive && statusArea.size === 0, 'para de observar e tira o ícone');

console.log('extensão: 14 cenários ok');
