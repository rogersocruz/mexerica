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
    timeout_add(_p, ms, fn) {
        const t = {due: now + ms * 1000, ms, fn, alive: true};
        timers.push(t);
        return timers.length;
    },
    source_remove(id) { timers[id - 1].alive = false; },
    Variant: class { constructor(sig, v) { this.sig = sig; this.v = v; } },
};
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
    get_window_actors: () => windows.map(w => ({get_meta_window: () => w})),
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
};
const Clutter = {ModifierType: {SHIFT_MASK: SHIFT, CONTROL_MASK: CTRL, MOD1_MASK: ALT}};
const Meta = {SelectionType: {SELECTION_DND: 2}};
const St = {Clipboard: {get_default: () => ({set_text: (_t, s) => { clipboard = s; }})},
    ClipboardType: {CLIPBOARD: 1}};
const activated = [];
const Main = {activateWindow: w => activated.push(w)};
class Extension { constructor() { this.metadata = {version: 1}; } }

// ---------- carrega a extensão com os mocks ------------------------------
const body = src
    .replace(/^import .*$/gm, '')
    .replace('export default class', 'return class');
// eslint-disable-next-line no-new-func
const Ext = new Function('Clutter', 'Gio', 'GLib', 'Meta', 'St', 'Extension', 'Main', body)(
    Clutter, Gio, GLib, Meta, St, Extension, Main);

const ext = new Ext();
ext.enable();

function fakeWindow(title, wmClass = 'io.github.rogersocruz.Mexerica') {
    return Object.assign(emitter(), {
        above: false, raised: 0, monitor: 0,
        get_gtk_application_id: () => wmClass, get_wm_class: () => wmClass,
        get_title() { return title; }, is_above() { return this.above; },
        make_above() { this.above = true; }, raise() { this.raised++; },
        get_monitor() { return this.monitor; }, move_to_monitor(m) { this.monitor = m; },
    });
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
display.emit('window-created', ov);
assert.ok(ov.above && ov.raised === 1 && ov.monitor === 1);
windows.push(ov);

// ---------- 4. + Alt -> ferramentas, mesmo centro ------------------------
pointer = [2700, 600, SHIFT | ALT];
advance(40);
const last = calls.at(-1);
assert.equal(last.args[0], 'tools');
assert.equal(last.args[2], 580, 'centro não muda ao trocar de modo');
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
assert.equal(late.count(), 0, 'parou de observar');
assert.ok(activated.includes(late));

// ---------- 10. clipboard via D-Bus e disable limpo -----------------------
ext.SetClipboard('/home/r/foto.png');
assert.equal(clipboard, '/home/r/foto.png');
ext.disable();
assert.equal(dnd.count(), 0);

console.log('extensão: 10 cenários ok');
