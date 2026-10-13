import json
from collections import namedtuple

from manimlib import *

from .style import *
from .lattice import SurfaceCodeLattice
from .nn import (DetectorVector, GRUCell, HeadBox, PFlipGauge, StateHeatmap, caption,
                 diverging_color, flow_arrow, pulse_along)

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
