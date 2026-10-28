"""Vídeo e áudio: "Trim" (TRIM) e "Resize Video" (RESIZE, em lote)."""
from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .. import theme as TH  # noqa: E402
from ..engine import edits as E  # noqa: E402
from ..engine import formats as F  # noqa: E402
from ..engine import tools as T  # noqa: E402
from ..engine.ops import Op  # noqa: E402
from .base import EditorWindow, dropdown, label, row  # noqa: E402
from .common import Latest, bg, fmt_size, fmt_time, run_out, texture  # noqa: E402


def _section(text: str) -> Gtk.Label:
    return label(text.upper(), "mx-dim")


MIN_CLIP = 0.1


class TrimWindow(EditorWindow):
    def __init__(self, app, op: Op, path: Path):
        self.video = F.kind_of(path) == F.VIDEO
        super().__init__(app, op, "Trim Video" if self.video
                         else "Trim Audio", 900 if self.video else 720,
                         640 if self.video else 380, primary="Save")
        self.path = path
        self.dur = 0.0
        self.start = 0.0
        self.end = 0.0
        self._drag = None
        self._syncing = False
        self.player: subprocess.Popen | None = None
        self._play_t0 = 0.0          # relógio monotônico no início do play
        self._play_src = 0
        self.frames = {"start": Latest(60), "end": Latest(60)}
        self.keyframe = Latest(150)
        self._fast_auto = True       # o usuário ainda não mexeu no "Rápido"

        box = self.body

        if self.video:
            frames = Gtk.Box(spacing=14, homogeneous=True, vexpand=True)
            self.pics = {}
            for key, title in (("start", "Start"), ("end", "End")):
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                col.append(_section(title))
                pic = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN,
                                  can_shrink=True, vexpand=True)
                pic.add_css_class("mx-frame")
                self.pics[key] = pic
                col.append(pic)
                frames.append(col)
            box.append(frames)

        # linha do tempo: forma de onda (áudio) + seleção desenhada por cima
        self.wave = Gtk.Picture(content_fit=Gtk.ContentFit.FILL,
                                can_shrink=True)
        self.timeline = Gtk.DrawingArea(content_height=92 if not self.video
                                        else 72, hexpand=True)
        self.timeline.set_draw_func(self._draw)
        self._play_from = 0.0
        tl = Gtk.Overlay(child=self.wave)
        tl.add_overlay(self.timeline)
        tl.add_css_class("mx-frame")
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end", lambda *_: setattr(self, "_drag", None))
        self.timeline.add_controller(drag)
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._motion)
        self.timeline.add_controller(motion)
        box.append(tl)

        # campos numéricos
        fields = Gtk.Box(spacing=10)
        self.spin = {}
        for key, title in (("start", "Start (s)"), ("end", "End (s)")):
            sp = Gtk.SpinButton.new_with_range(0, 1, 0.1)
            sp.set_digits(2)
            sp.connect("value-changed", self._on_spin, key)
            self.spin[key] = sp
            fields.append(label(title, "mx-dim"))
            fields.append(sp)
        self.len_lbl = Gtk.Label(hexpand=True, xalign=1)
        self.len_lbl.add_css_class("mx-label")
        fields.append(self.len_lbl)
        box.append(fields)

        opts = Gtk.Box(spacing=18)
        self.play_btn = Gtk.Button(icon_name="media-playback-start-symbolic",
                                   tooltip_text="Play the selection (Space)",
                                   visible=T.has("ffplay"))
        self.play_btn.connect("clicked", lambda *_: self._toggle_play())
        opts.append(self.play_btn)
        self.fast = Gtk.CheckButton(label="Fast (no re-encode)",
                                    active=True)
        self.fast.set_tooltip_text(
            "Instant and lossless. For video the start may move back to the "
            "previous keyframe; turn off for an exact cut.")
        self.fast.connect("toggled", self._on_fast_toggled)
        opts.append(self.fast)
        self.cut_out = Gtk.CheckButton(label="Remove selection (keep the rest)")
        self.cut_out.connect("toggled", lambda *_: self._check_keyframe())
        opts.append(self.cut_out)
        box.append(opts)
        self.say("Loading…")
        self._load()

    # --- carregamento ---------------------------------------------------
    def _load(self) -> None:
        path = self.path
        bg(lambda: E.duration(path), self.alive(self._got_duration))
        if not self.video:
            argv = T.cmd("ffmpeg") + [
                "-hide_banner", "-nostdin", "-v", "error", "-i", str(path),
                "-filter_complex",
                "aformat=channel_layouts=mono,"
                "showwavespic=s=1600x180:scale=sqrt:colors=#ffffff",
                "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-"]
            bg(lambda: run_out(argv), self.alive(self._got_wave))
        else:
            bg(self._filmstrip, self.alive(self._got_wave))

    def _filmstrip(self) -> bytes:
        """Tira de quadros para o fundo da linha do tempo (só vídeo):
        buscas rápidas (-ss antes do -i) em paralelo, coladas lado a lado."""
        n, dur = 12, E.duration(self.path)

        def grab(i: int) -> Path | None:
            f = self.tmp / f"tira{i:02d}.jpg"
            subprocess.run(T.cmd("ffmpeg") + [
                "-hide_banner", "-nostdin", "-v", "error", "-y",
                "-ss", f"{dur * (i + 0.5) / n:.3f}", "-i", str(self.path),
                "-frames:v", "1", "-vf", "scale=-2:72", "-q:v", "5", str(f)],
                capture_output=True, stdin=subprocess.DEVNULL)
            return f if f.exists() else None
        with ThreadPoolExecutor(4) as pool:
            frames = [f for f in pool.map(grab, range(n)) if f]
        if not frames:
            raise RuntimeError("no frames")
        return run_out(T.cmd("magick") + [*map(str, frames), "+append",
                                       "png:-"])

    def _got_duration(self, res) -> None:
        if isinstance(res, Exception):
            self.say(f"Could not read the duration: {res}", error=True)
            return
        self.dur = res
        self.start, self.end = 0.0, res
        self._syncing = True
        for key in ("start", "end"):
            self.spin[key].set_range(0, res)
            self.spin[key].set_value(getattr(self, key))
        self._syncing = False
        self.save_btn.set_sensitive(True)
        self.say("Drag the handles or type the times.")
        self._changed("start")
        self._changed("end")

    def _got_wave(self, res) -> None:
        if not isinstance(res, Exception):
            self.wave.set_paintable(texture(res))

    def _frame(self, key: str) -> None:
        if not self.video:
            return
        t = self.start if key == "start" else max(self.end - 0.05, 0)
        argv = T.cmd("ffmpeg") + [
            "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{t:.3f}",
            "-i", str(self.path), "-frames:v", "1", "-vf", "scale=640:-2",
            "-f", "image2pipe", "-c:v", "png", "-"]
        pic = self.pics[key]
        self.frames[key].request(
            lambda: run_out(argv),
            self.alive(lambda r: None if isinstance(r, Exception)
                       else pic.set_paintable(texture(r))))

    # --- tocar ----------------------------------------------------------
    # ffplay num processo à parte: o GtkMediaFile/GStreamer pode abortar o
    # processo inteiro com certos arquivos, e aqui isso derrubaria a roda.
    def _toggle_play(self) -> None:
        if self.player:
            self._stop()
            return
        if not self.dur:
            return
        self.player = subprocess.Popen(
            T.cmd("ffplay") + ["-nodisp", "-autoexit", "-loglevel", "quiet",
                               "-ss", f"{self.start:.3f}",
                               "-t", f"{self.end - self.start:.3f}",
                               str(self.path)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        self._play_t0 = GLib.get_monotonic_time() / 1e6
        self._play_from = self.start
        self.play_btn.set_icon_name("media-playback-stop-symbolic")
        self._play_src = GLib.timeout_add(40, self._play_tick)

    def _playhead(self) -> float | None:
        if not self.player:
            return None
        return self._play_from + GLib.get_monotonic_time() / 1e6 \
            - self._play_t0

    def _play_tick(self):
        if self.closed or not self.player or \
                self.player.poll() is not None:
            self._play_src = 0
            self._stop()
            return GLib.SOURCE_REMOVE
        self.timeline.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _stop(self) -> None:
        if self.player:
            if self.player.poll() is None:
                self.player.terminate()
            self.player = None
        if self._play_src:
            GLib.source_remove(self._play_src)
            self._play_src = 0
        self.play_btn.set_icon_name("media-playback-start-symbolic")
        self.timeline.queue_draw()

    # --- linha do tempo -------------------------------------------------
    def _x(self, t: float) -> float:
        w = self.timeline.get_width()
        return t / self.dur * w if self.dur else 0

    def _t(self, x: float) -> float:
        w = self.timeline.get_width() or 1
        return min(max(x / w, 0), 1) * self.dur

    def _hit(self, x: float) -> str:
        xs, xe = self._x(self.start), self._x(self.end)
        if abs(x - xs) <= 10 and abs(x - xs) <= abs(x - xe):
            return "start"
        if abs(x - xe) <= 10:
            return "end"
        if xs < x < xe:
            return "move"
        return "start" if abs(x - xs) < abs(x - xe) else "end"

    def _motion(self, _c, x, _y) -> None:
        if self.dur and self._drag is None:
            mode = self._hit(x)
            self.timeline.set_cursor_from_name(
                "grab" if mode == "move" else "col-resize")

    def _drag_begin(self, _g, x, _y) -> None:
        if not self.dur:
            return
        mode = self._hit(x)
        if mode != "move" and abs(x - self._x(getattr(self, mode))) > 10:
            self._set(mode, self._t(x))       # clique fora: pula a alça
        self._drag = (mode, x, self.start, self.end)

    def _drag_update(self, _g, dx, _dy) -> None:
        if not self._drag:
            return
        mode, x0, s0, e0 = self._drag
        if mode == "move":
            span = e0 - s0
            s = min(max(s0 + self._t(x0 + dx) - self._t(x0), 0),
                    self.dur - span)
            self._set("start", s, also_end=s + span)
        else:
            self._set(mode, self._t(x0 + dx))

    def _set(self, key: str, t: float, also_end: float | None = None) -> None:
        if also_end is not None:
            self.start, self.end = t, also_end
            self._changed("start")
            self._changed("end")
            return
        if key == "start":
            self.start = min(max(t, 0), self.end - MIN_CLIP)
        else:
            self.end = max(min(t, self.dur), self.start + MIN_CLIP)
        self._changed(key)

    def _on_spin(self, sp, key) -> None:
        if self._syncing or not self.dur:
            return
        self._set(key, sp.get_value())

    def _changed(self, key: str) -> None:
        self._syncing = True
        self.spin[key].set_value(getattr(self, key))
        self._syncing = False
        self.len_lbl.set_text(
            f"{fmt_time(self.start)} → {fmt_time(self.end)}   "
            f"({fmt_time(self.end - self.start)})")
        self.timeline.queue_draw()
        self._frame(key)
        self._check_keyframe()

    # --- corte rápido x quadro-chave ------------------------------------
    def _on_fast_toggled(self, *_a) -> None:
        if not self._syncing:
            self._fast_auto = False
        self._check_keyframe()

    def _check_keyframe(self) -> None:
        """Vídeo: o corte rápido começa no quadro-chave anterior. Se ele
        estiver longe do ponto pedido, avisa e (se o usuário não escolheu)
        passa para corte exato."""
        if not self.video or not self.dur:
            return
        t = self.end if self.cut_out.get_active() else self.start
        if t < 0.05:
            self._keyframe_result(t, 0.0)
            return
        path = self.path
        self.keyframe.request(
            lambda: E.keyframe_before(path, t),
            self.alive(lambda r: None if isinstance(r, Exception)
                       else self._keyframe_result(t, r)))

    def _keyframe_result(self, t: float, kf: float) -> None:
        gap = t - kf
        if self._fast_auto:
            self._syncing = True
            self.fast.set_active(gap <= 0.3)
            self._syncing = False
        if gap > 0.3 and self.fast.get_active():
            self.say(f"Fast cut starts at {fmt_time(kf)} (keyframe), "
                     f"{gap:.1f} s early. Turn off “Fast” for an exact cut.",
                     error=True)
        elif gap > 0.3:
            self.say(f"Exact cut (re-encodes): nearest keyframe is "
                     f"{gap:.1f} s earlier.")
        else:
            self.say("Fast cut starts exactly where you chose.")

    def _draw(self, _area, cr, W, H) -> None:
        if not self.dur:
            return
        xs, xe = self._x(self.start), self._x(self.end)
        cr.set_source_rgba(*TH.CROP_DIM)            # fora da seleção
        cr.rectangle(0, 0, xs, H)
        cr.rectangle(xe, 0, W - xe, H)
        cr.fill()
        cr.set_source_rgba(*TH.HANDLE[:3], 0.15)    # seleção
        cr.rectangle(xs, 0, xe - xs, H)
        cr.fill()
        cr.set_source_rgba(*TH.HANDLE)
        cr.set_line_width(2)
        cr.rectangle(xs + 1, 1, xe - xs - 2, H - 2)
        cr.stroke()
        for x in (xs, xe):                          # alças
            cr.rectangle(x - 4, H / 2 - 14, 8, 28)
            cr.fill()
        head = self._playhead()
        if head is not None and head <= self.end:
            px = self._x(head)
            cr.set_source_rgba(1, 1, 1, 0.95)
            cr.rectangle(px - 1, 0, 2, H)
            cr.fill()

    def on_key(self, keyval, state) -> bool:
        if keyval == Gdk.KEY_space and self.play_btn.get_visible() and \
                not isinstance(self.get_focus(), (Gtk.Text, Gtk.SpinButton)):
            self._toggle_play()
            return True
        return False

    def reset(self) -> None:
        if self.dur:
            self._set("start", 0.0, also_end=self.dur)
        self.cut_out.set_active(False)

    def build(self):
        s, e = self.start, self.end
        remove = self.cut_out.get_active()
        if e - s < MIN_CLIP:
            raise ValueError("Selection is too short.")
        whole = s < 0.05 and e > self.dur - 0.05
        if whole and not remove:
            raise ValueError("The selection is the whole file: move the handles.")
        if whole and remove:
            raise ValueError("That would remove the whole file.")
        return (E.trim_op(self.op, s, e, self.fast.get_active(), remove),
                [self.path])

    def cleanup(self) -> None:
        self._stop()
        for f in (*self.frames.values(), self.keyframe):
            f.cancel()


# --------------------------------------------------------------------------
# Tamanho… (vídeo, em lote)
# --------------------------------------------------------------------------

TARGETS: list[tuple[str, float]] = [
    ("Quality only (CRF 26)", 0), ("8 MB", 8), ("10 MB", 10), ("25 MB", 25),
    ("50 MB", 50), ("100 MB", 100), ("Custom…", -1),
]
HEIGHTS: list[tuple[str, int]] = [
    ("Original", 0), ("1080p", 1080), ("720p", 720), ("480p", 480),
    ("360p", 360),
]


class VideoSizeWindow(EditorWindow):
    def __init__(self, app, op: Op, paths: list[Path]):
        n = len(paths)
        super().__init__(app, op, "Resize Video" + ("" if n == 1 else
                                                    f" · {n} videos"),
                         460, 330, primary="Save")
        self.paths = paths
        self.durs: list[float] = []

        box = self.body
        self.target_dd = dropdown([t[0] for t in TARGETS], 3)
        box.append(row("Fit into", self.target_dd))
        self.custom = Gtk.SpinButton.new_with_range(1, 4000, 1)
        self.custom.set_value(20)
        self.custom_row = row("Size (MB)", self.custom)
        self.custom_row.set_visible(False)
        box.append(self.custom_row)
        self.height_dd = dropdown([h[0] for h in HEIGHTS])
        box.append(row("Max resolution", self.height_dd))
        self.mute = Gtk.Switch(valign=Gtk.Align.CENTER)
        box.append(row("Remove audio", self.mute))
        self.result = Gtk.Label(xalign=0, wrap=True, label="Reading…")
        self.result.add_css_class("mx-label")
        box.append(self.result)

        self.target_dd.connect("notify::selected", lambda *_: self._changed())
        self.height_dd.connect("notify::selected", lambda *_: self._changed())
        self.custom.connect("value-changed", lambda *_: self._changed())
        self.mute.connect("notify::active", lambda *_: self._changed())
        bg(lambda: [E.duration(p) for p in paths],
            self.alive(self._got_durations))

    def _got_durations(self, res) -> None:
        if isinstance(res, Exception):
            self.result.set_text(f"Could not read the duration: {res}")
            return
        self.durs = res
        self.save_btn.set_sensitive(True)
        self._changed()

    def _target(self) -> float:
        mb = TARGETS[self.target_dd.get_selected()][1]
        return self.custom.get_value() if mb < 0 else mb

    def _changed(self) -> None:
        self.custom_row.set_visible(
            TARGETS[self.target_dd.get_selected()][1] < 0)
        if not self.durs:
            return
        mb = self._target()
        size = sum(p.stat().st_size for p in self.paths)
        shortest = min(self.durs)
        msg = (f"{len(self.paths)} file(s), {fmt_size(size)}, "
               f"{fmt_time(sum(self.durs))} total.")
        if mb:
            audio = 0 if self.mute.get_active() else 96
            kbps = mb * 8192 * 0.93 / max(max(self.durs), 0.1) - audio
            msg += f"\nVideo at ~{max(kbps, 60):.0f} kbps."
            if kbps < 350 and HEIGHTS[self.height_dd.get_selected()][1] in \
                    (0, 1080):
                msg += " Low for this resolution: pick 720p or 480p."
        else:
            msg += f"\nShortest: {fmt_time(shortest)}."
        self.result.set_text(msg)

    def reset(self) -> None:
        self.target_dd.set_selected(3)
        self.height_dd.set_selected(0)
        self.mute.set_active(False)

    def build(self):
        mb = self._target()
        height = HEIGHTS[self.height_dd.get_selected()][1]
        return (E.video_size_op(self.op, mb, height, self.mute.get_active()),
                self.paths)
