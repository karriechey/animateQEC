"""Sound for animateQEC: synthesized cues and a continuous pad bed, driven by the scene's visuals.

A scene records a cue sheet while it renders (CueSheet): one-shot cues stamped with the scene
clock, each with a gain curve copied frame by frame from its mobject's opacity, plus named
automation curves (bed level, bed brightness, camera swell). `mix` reads a concat list of
rendered scenes, joins their cue sheets on one timeline and renders one continuous bed under
all cues, optionally ducked under a narration WAV.

    python animateqec/sound.py examples/gru-decoder/team_cut.txt --out videos/team_cut [--narration voice.wav]
"""
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48_000
CTRL = 200  # control rate (Hz) for automation curves
PENTATONIC = [0, 2, 4, 7, 9]
BED_FLOOR_DB = -30.0  # the bed never goes fully silent


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-12))


def undb(x):
    return 10 ** (np.asarray(x) / 20)


def _t(dur):
    return np.arange(int(dur * SR)) / SR


# ---- one-shot sounds ------------------------------------------------------------------

def envelope(n, attack=0.005, release=0.02, decay=8.0):
    """Raised-cosine attack, exponential decay, raised-cosine release to exactly zero."""
    env = np.exp(-decay * np.arange(n) / SR)
    a, r = max(1, int(attack * SR)), max(1, int(release * SR))
    env[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    env[-r:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(r) / r)
    return env


def tone(freq, dur, partials=(1.0,), decay=8.0, attack=0.005, release=0.02):
    t = _t(dur)
    w = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(partials))
    return w * envelope(len(t), attack, release, decay)


def pentatonic(i, base=196.0):
    octave, deg = divmod(int(i), len(PENTATONIC))
    return base * 2 ** ((PENTATONIC[deg] + 12 * octave) / 12)


def blip(freq, dur=0.25):
    return 0.6 * tone(freq, dur, (1.0, 0.22, 0.06), decay=14)


def tick():
    t = _t(0.035)
    click = np.sin(2 * np.pi * 2300 * t) + 0.4 * np.sin(2 * np.pi * 3400 * t)
    return 0.35 * click * envelope(len(t), 0.001, 0.01, decay=110)


def soft_chord(freqs, dur=1.0, brightness=0.5):
    b = 0.15 + 0.75 * float(np.clip(brightness, 0, 1))
    return sum(0.22 * tone(f, dur, tuple(b ** k for k in range(6)), decay=2.5, attack=0.06, release=0.15)
               for f in freqs)


def resolve(root=261.63):
    """Suspended chord settling onto the major triad."""
    sus = soft_chord([root, root * 4 / 3, root * 3 / 2], 0.6, 0.6)
    maj = soft_chord([root, root * 5 / 4, root * 3 / 2, root * 2], 2.2, 0.75)
    out = np.zeros(len(sus) // 2 + len(maj))
    out[:len(sus)] += sus
    out[len(sus) // 2:] += maj
    return out


def dissonant(freq=98.0, dur=1.3):
    return sum(0.4 * tone(f, dur, (1.0, 0.3), decay=1.8, attack=0.04, release=0.2)
               for f in (freq, freq * 2 ** (1 / 12)))


SOUNDS = {"blip": blip, "tick": tick, "soft_chord": soft_chord, "resolve": resolve,
          "dissonant": dissonant}


# ---- recording in the scene -------------------------------------------------------------

def visibility(mob):
    """Largest opacity over the mobject's family (fill, stroke or dot opacity)."""
    vals = [0.0]
    for m in mob.get_family():
        if hasattr(m, "get_fill_opacity"):
            vals += [m.get_fill_opacity(), m.get_stroke_opacity()]
        elif m.has_points():
            vals.append(m.get_opacity())
    return float(max(vals))


class CueSheet:
    """Cues and automation recorded from a scene as it renders.

    at(): a cue at the current scene time (plus offset). With follow=mob, its gain curve is
    mob's visibility sampled every frame for the cue's length, 0 while mob is off screen, so
    fades, dims (0.2 -> -14 dB) and the animation's own rate function carry over exactly.
    track(): a named automation curve sampled every frame from a function of the scene.
    point(): a breakpoint written directly into an automation curve.
    """

    def __init__(self, scene):
        from manimlib import Mobject
        self.scene, self.cues, self.curves, self._tracks, self._follows = scene, [], {}, {}, []
        # the probe samples every frame; scenes must not fade or remove it
        self.probe = Mobject()
        self.probe.add_updater(lambda m, dt: self._sample())
        scene.add(self.probe)

    def _on_screen(self):
        return {id(m) for top in self.scene.mobjects for m in top.get_family()}

    def _sample(self):
        t = self.scene.time
        for name, fn in self._tracks.items():
            self.curves.setdefault(name, []).append((t, float(fn())))
        if self._follows:
            live = self._on_screen()
            for cue, mob, until in self._follows:
                if t <= until:
                    cue["gain"].append((t, visibility(mob) if id(mob) in live else 0.0))
            self._follows = [f for f in self._follows if t <= f[2]]

    def at(self, kind, offset=0.0, velocity=1.0, follow=None, **params):
        t = self.scene.time + offset
        length = len(SOUNDS[kind](**params)) / SR
        cue = {"t": t, "kind": kind, "params": params, "velocity": float(velocity), "gain": []}
        if follow is not None:
            self._follows.append((cue, follow, t + length))
        self.cues.append(cue)
        return cue

    def group(self, anim, kinds, **common):
        """One cue per sub-animation of an AnimationGroup, at its own start time.

        kinds: list of dicts (kind, params, velocity, follow) or None. run_time must be set on
        anim itself; AnimationGroup applies alpha linearly, so these times are exact.
        """
        scale = anim.get_run_time() / anim.max_end_time
        for (_, start, _), spec in zip(anim.anims_with_timings, kinds):
            if spec:
                self.at(offset=start * scale, **{**common, **spec})

    def track(self, name, fn):
        self._tracks[name] = fn

    def untrack(self, name):
        self._tracks.pop(name, None)

    def point(self, name, value, offset=0.0):
        self.curves.setdefault(name, []).append((self.scene.time + offset, float(value)))

    def write(self, path):
        data = {"scene": type(self.scene).__name__, "duration": self.scene.time,
                "fps": self.scene.camera.fps, "cues": self.cues,
                "curves": {k: sorted(v) for k, v in self.curves.items()}}
        Path(path).write_text(json.dumps(data))
        return path


# ---- the bed ------------------------------------------------------------------------------

def _curve(points, n, default):
    """Breakpoints (t, v) to a control-rate array of length n, held at the ends."""
    if not points:
        return np.full(n, default, dtype=float)
    t, v = np.array(points, dtype=float).T
    return np.interp(np.arange(n) / CTRL, t, v)


# Pad presets, one per kind of passage. chord: Hz; detune: cents per voice; shimmer: Hz range of
# the slow amplitude wobble; pulse: (Hz, depth) tremolo; tilt: brightness offset; rolloff: how
# fast upper partials fall (higher = rounder).
PADS = {
    # the physical system: open, airy, suspended
    "air": dict(chord=[146.83, 220.0, 293.66, 329.63, 440.0], detune=(-5, 0, 6), shimmer=(0.04, 0.1),
                pulse=(0.0, 0.0), tilt=0.12, rolloff=1.4),
    # detectors becoming data: glassy, a light shimmer
    "data": dict(chord=[164.81, 246.94, 293.66, 369.99, 493.88], detune=(-4, 0, 5), shimmer=(0.15, 0.3),
                 pulse=(4.0, 0.12), tilt=0.18, rolloff=1.6),
    # the machine: warm and low, with a slow heartbeat
    "machine": dict(chord=[110.0, 164.81, 196.0, 261.63], detune=(-6, 0, 7), shimmer=(0.03, 0.08),
                    pulse=(1.0, 0.22), tilt=-0.08, rolloff=1.2),
    # depth: the same harmony doubled an octave down, fuller
    "depth": dict(chord=[55.0, 110.0, 220.0, 261.63, 329.63, 493.88], detune=(-7, 0, 8), shimmer=(0.03, 0.07),
                  pulse=(0.5, 0.15), tilt=0.0, rolloff=1.1),
    # one hard shot: darker minor with a sixth, wider beating
    "tension": dict(chord=[110.0, 164.81, 220.0, 261.63, 349.23], detune=(-11, 0, 12), shimmer=(0.05, 0.12),
                    pulse=(0.0, 0.0), tilt=-0.1, rolloff=1.2),
    # the results: settled, open major
    "settle": dict(chord=[130.81, 196.0, 261.63, 329.63, 392.0], detune=(-4, 0, 5), shimmer=(0.02, 0.05),
                   pulse=(0.0, 0.0), tilt=0.05, rolloff=1.3),
}


def bed(t0, t1, level_db, bright, swell_db, pad="tension", seed=0):
    """Soft evolving pad over [t0, t1) of the cut: detuned sines through a moving low-pass
    (per-partial 1-pole response). level_db, bright (0..1), swell_db are control-rate arrays
    over the whole cut; time t0 is sample 0 of the result."""
    p = PADS[pad]
    rng = np.random.default_rng(seed)
    t = t0 + np.arange(int((t1 - t0) * SR)) / SR
    up = lambda c: np.interp(t, np.arange(len(c)) / CTRL, c)
    # brightness drives the cutoff; a 0.04 Hz drift keeps the pad moving when nothing else does
    b = np.clip(up(bright) + p["tilt"] + 0.08 * np.sin(2 * np.pi * 0.04 * t), 0, 1)
    cutoff = 250 * 2 ** (4.5 * b)
    out = np.zeros(len(t))
    for f0 in p["chord"]:
        for cents in p["detune"]:
            f = f0 * 2 ** (cents / 1200)
            phase = rng.uniform(0, 2 * np.pi)
            wob = 1 + 0.25 * np.sin(2 * np.pi * rng.uniform(*p["shimmer"]) * t + phase)
            for k in range(1, 7):
                fk = f * k
                gain = (1 / k ** p["rolloff"]) / np.sqrt(1 + (fk / cutoff) ** 2)
                out += gain * wob * np.sin(2 * np.pi * fk * t + phase * k)
    rate, depth = p["pulse"]
    if depth:
        out *= 1 - depth * (0.5 - 0.5 * np.cos(2 * np.pi * rate * t))
    out /= np.sqrt(np.mean(out ** 2)) + 1e-12
    return out * up(undb(np.maximum(level_db, BED_FLOOR_DB) + swell_db))


def pad_track(starts, durs, pads, level, bright, swell, xfade=1.5):
    """One bed for the whole cut: each scene's pad, equal-power crossfaded across every cut."""
    total = starts[-1] + durs[-1]
    n = int(total * SR)
    out = np.zeros(n)
    for i, (t0, d, pad) in enumerate(zip(starts, durs, pads)):
        a, b = max(0.0, t0 - xfade / 2), min(total, t0 + d + xfade / 2)
        seg = bed(a, b, level, bright, swell, pad, seed=i)
        tt = a + np.arange(len(seg)) / SR
        w = np.ones(len(seg))
        if i > 0:  # fade in across the cut at t0
            u = np.clip((tt - (t0 - xfade / 2)) / xfade, 0, 1)
            w *= np.sin(0.5 * np.pi * u)
        if i < len(starts) - 1:  # fade out across the next cut
            u = np.clip((tt - (t0 + d - xfade / 2)) / xfade, 0, 1)
            w *= np.cos(0.5 * np.pi * u)
        i0 = int(round(a * SR))
        m = min(len(seg), n - i0)
        out[i0:i0 + m] += (seg * w)[:m]
    edge = int(0.5 * SR)
    out[:edge] *= np.linspace(0, 1, edge)
    out[-edge:] *= np.linspace(1, 0, edge)
    return out


# ---- mixing a cut ------------------------------------------------------------------------

def duration_of(mp4):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "csv=p=0", str(mp4)], capture_output=True, text=True).stdout
    return float(out)


def read_wav(path):
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32767
        if w.getnchannels() > 1:
            x = x.reshape(-1, w.getnchannels()).mean(1)
        if w.getframerate() != SR:
            x = np.interp(np.arange(int(len(x) * SR / w.getframerate())) * w.getframerate() / SR,
                          np.arange(len(x)), x)
    return x


def write_wav(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def duck_gain(narration, n, depth_db=8.0, attack=0.05, release=0.4):
    """Gain (linear) that dips depth_db under the voice: peak envelope with 50 ms attack and
    400 ms release; any voice within 10 dB of its typical level gives the full dip."""
    x = np.zeros(n)
    x[:min(n, len(narration))] = np.abs(narration[:n])
    hop = SR // CTRL
    frames = x[:n // hop * hop].reshape(-1, hop).max(1)
    a, r = np.exp(-1 / (attack * CTRL)), np.exp(-1 / (release * CTRL))
    env = np.zeros(len(frames))
    e = 0.0
    for i, v in enumerate(frames):
        e = a * e + (1 - a) * v if v > e else r * e + (1 - r) * v
        env[i] = e
    # full dip once the voice is within 10 dB of its typical level
    ref = 0.3 * np.percentile(env[env > 1e-4], 90) if (env > 1e-4).any() else 1.0
    g_db = -depth_db * np.clip(env / ref, 0, 1)
    return np.interp(np.arange(n), np.arange(len(g_db)) * hop, undb(g_db))


def mix(concat_list, out, narration=None, bed_db=-6.0, cue_db=0.0, target_rms_dbfs=-38.0,
        stems_dir=None, video=True, xfade=1.5):
    """Render one continuous bed plus every scene's cues for a concat list of rendered scenes.

    Scenes without a cue sheet get the bed at its default level. Writes <out>.wav,
    <out>.cues.json (the joined cue sheet) and, with video, <out>.mp4 (videos joined, audio muxed).
    With stems_dir, also writes per-scene stems for an editor, at the mix's own gain so they sum
    to the mix: NN_<scene>.mp4 (silent), NN_<scene>_cues.wav (scene length), NN_<scene>_pad-<name>.wav
    (starts xfade/2 before the scene and ends xfade/2 after it, for crossfades), and
    pad_bed_continuous.wav (the crossfaded bed for the whole list).
    Returns a dict of levels for the report.
    """
    concat_list = Path(concat_list)
    # "# pad <name>" on the line before a file sets that scene's pad (ffmpeg ignores # lines)
    files, pads, pad = [], [], "tension"
    for line in concat_list.read_text().splitlines():
        if line.startswith("# pad "):
            pad = line.split()[2]
            assert pad in PADS, f"unknown pad {pad!r}"
        elif line.startswith("file"):
            files.append(concat_list.parent / line.split("'")[1])
            pads.append(pad)
    durs = [duration_of(f) for f in files]
    total = sum(durs)
    n, nc = int(total * SR), int(total * CTRL) + 1
    level, bright, swell = np.full(nc, bed_db), np.full(nc, 0.35), np.zeros(nc)
    cues, starts = [], np.concatenate([[0], np.cumsum(durs)[:-1]])
    for f, t0, dur in zip(files, starts, durs):
        sheet = f.with_suffix(".cues.json")
        if not sheet.exists():
            continue
        s = json.loads(sheet.read_text())
        i0, i1 = int(t0 * CTRL), min(nc, int((t0 + dur) * CTRL))
        seg = i1 - i0
        for name, arr, dflt in (("bed_level", level, bed_db), ("bed_bright", bright, 0.35),
                                ("swell", swell, 0.0)):
            pts = s["curves"].get(name)
            if pts:
                arr[i0:i1] = _curve(pts, seg, dflt)
        for c in s["cues"]:
            cues.append({**c, "t": c["t"] + t0, "gain": [(g[0] + t0, g[1]) for g in c["gain"]]})
    # smooth only around scene joins, so a cut never steps the bed but in-scene moves stay sharp
    k = np.ones(int(0.25 * CTRL)) / int(0.25 * CTRL)
    for arr in (level, bright):
        sm = np.convolve(arr, k, "same")
        for t0 in starts[1:]:
            i = int(t0 * CTRL)
            arr[max(0, i - CTRL // 4):i + CTRL // 4] = sm[max(0, i - CTRL // 4):i + CTRL // 4]

    pad = pad_track(starts, durs, pads, level, bright, swell, xfade)
    fx = np.zeros(n + 3 * SR)
    for c in cues:
        snd = SOUNDS[c["kind"]](**c["params"]) * c["velocity"]
        i = int(round(c["t"] * SR))
        if c["gain"]:
            gt, gv = np.array(c["gain"]).T
            snd = snd * np.interp(c["t"] + np.arange(len(snd)) / SR, gt, gv, left=gv[0], right=gv[-1])
        fx[i:i + len(snd)] += snd[:max(0, len(fx) - i)]
    fx = fx[:n]
    pad, fx = undb(-12) * pad, undb(cue_db) * fx
    y = pad + fx
    # level (set before ducking, so the duck stays a real dip): sounding parts at
    # target_rms_dbfs, peak capped at -6 dBFS
    win = SR // 20
    fr = y[:n // win * win].reshape(-1, win)
    rms = np.sqrt((fr ** 2).mean(1))
    gain = undb(target_rms_dbfs) / np.sqrt(np.mean(rms[rms > rms.max() * undb(-50)] ** 2))
    gain = min(gain, undb(-6) / np.abs(y).max())
    y *= gain
    if narration is not None:
        y *= duck_gain(read_wav(narration), n)
    if stems_dir:
        sd = Path(stems_dir)
        sd.mkdir(parents=True, exist_ok=True)
        write_wav(sd / "pad_bed_continuous.wav", gain * pad)
        for i, (f, t0, d, name) in enumerate(zip(files, starts, durs, pads)):
            stem = f"{i + 1:02d}_{f.stem}"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(f), "-c", "copy", "-an",
                            str(sd / f"{stem}.mp4")], check=True)
            i0, i1 = int(t0 * SR), int((t0 + d) * SR)
            if np.abs(fx[i0:i1]).max() > 0:
                write_wav(sd / f"{stem}_cues.wav", gain * fx[i0:i1])
            a, b = max(0.0, t0 - xfade / 2), t0 + d + xfade / 2
            # the same segment pad_track crossfades, without its crossfade window
            write_wav(sd / f"{stem}_pad-{name}.wav", gain * undb(-12) * bed(a, b, level, bright, swell, name, seed=i))
    out = Path(out)
    write_wav(out.with_suffix(".wav"), y)
    out.with_suffix(".cues.json").write_text(json.dumps({"files": [f.name for f in files], "pads": pads,
                                                         "starts": starts.tolist(), "cues": cues}))
    if video:
        joined = out.with_name(out.name + "_video.mp4")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                        str(concat_list), "-c", "copy", str(joined)], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(joined), "-i", str(out.with_suffix(".wav")),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out.with_suffix(".mp4"))],
                       check=True)
        joined.unlink()
    fr = y[:n // win * win].reshape(-1, win)
    loud = np.sqrt((fr ** 2).mean(1))
    peak_t = np.argmax(np.abs(y)) / SR
    return {"duration": total, "cues": len(cues), "rms_dbfs": float(db(np.sqrt(np.mean(loud[loud > loud.max() * undb(-50)] ** 2)))),
            "peak_dbfs": float(db(np.abs(y).max())), "peak_at": float(peak_t),
            "bed_min_dbfs": float(db(np.min(loud[int(0.6 * 20):-int(0.6 * 20)])))}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("concat_list")
    ap.add_argument("--out", required=True)
    ap.add_argument("--narration")
    ap.add_argument("--stems", help="directory for per-scene stems (videos, cue and pad WAVs) for an editor")
    ap.add_argument("--no-video", action="store_true", help="skip the joined, muxed mp4")
    a = ap.parse_args()
    print(mix(a.concat_list, a.out, a.narration, stems_dir=a.stems, video=not a.no_video))
