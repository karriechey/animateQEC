import json
from collections import namedtuple

from manimlib import *

from .style import *
from .lattice import SurfaceCodeLattice, fire
from .nn import (DetectorVector, GRUCell, HeadBox, PFlipGauge, StateHeatmap, StateStrip, caption,
                 diverging_color, flow_arrow, gate_color, particles_along, pulse_along)

StepBits = namedtuple("StepBits", "n_bits fired present")


def load_viz(path):
    with open(path) as f:
        return json.load(f)


def pick_sample(viz, prefer_mwpm_wrong=False, shot=None):
    samples = viz["samples"]
    if shot is not None:
        return next(s for s in samples if s["shot"] == shot)
    if prefer_mwpm_wrong:
        wrong = [s for s in samples if s.get("mwpm_wrong")]
        if wrong:
            return min(wrong, key=lambda s: s["n_events"])
    return next(s for s in samples if s.get("pick", "readable") == "readable")


def slot_order(viz):
    """Detector (x, y) positions in sorted order: slot j of every input vector."""
    return sorted({(d["x"], d["y"]) for d in viz["detectors"]})


def step_bits(viz, sample, step):
    """Measured slots and fired slots of GRU step `step` (= Stim detector time t)."""
    slot = {xy: j for j, xy in enumerate(slot_order(viz))}
    det = viz["detectors"]
    present = sorted(slot[(det[i]["x"], det[i]["y"])] for i in viz["rounds"][str(step)])
    fired = sorted(slot[(det[i]["x"], det[i]["y"])]
                   for i in sample["events_by_round"].get(str(step), []))
    return StepBits(len(present), fired, present)


def vignette(lift=0.045, width=1920, height=1080):
    """Full-frame backdrop, fixed in frame: BG lifted slightly at the centre, BG at the edges."""
    import os
    import tempfile

    from PIL import Image
    path = os.path.join(tempfile.gettempdir(), f"animateqec_vignette_{BG[1:]}_{lift}_{width}x{height}.png")
    if not os.path.exists(path):
        y, x = np.mgrid[0:height, 0:width]
        r = np.hypot((x - width / 2) / (width / 2), (y - height / 2) / (height / 2)) / np.sqrt(2)
        bg = np.array([int(BG[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
        img = bg + 255 * lift * (1 - np.clip(r, 0, 1) ** 1.6)[..., None]
        Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path)
    v = ImageMobject(path)
    v.set_height(FRAME_HEIGHT)
    return v.fix_in_frame()
