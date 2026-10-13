"""Neural-network pieces: input vectors, recurrent cells, readout."""
import numpy as np
from manimlib import (DOWN, LEFT, RIGHT, UP, AnimationGroup, Arrow, DecimalNumber, Line,
                      Rectangle, interpolate_color, RoundedRectangle, ShowPassingFlash, Square, Tex, Text,
                      ValueTracker, VGroup)

from .style import BG, EVENT, FAINT, FG, FONT, MUTED, STATE_NEG, STATE_POS


class DetectorVector(VGroup):
    """Column of n_bits slots; unmeasured slots hollow, fired slots in EVENT."""

    def __init__(self, n_bits, fired=(), label=None, present=None, height=4.0, width=0.22,
                 **kwargs):
        super().__init__(**kwargs)
        fired, present = set(fired), set(range(n_bits) if present is None else present)
        h = height / n_bits
        self.cells = VGroup()
        for j in range(n_bits):
            c = Rectangle(width=width, height=h * 0.8)
            c.move_to(DOWN * j * h)
            if j in fired:
                c.set_fill(EVENT, 1).set_stroke(width=0)
            elif j in present:
                c.set_fill(MUTED, 0.6).set_stroke(width=0)
            else:
                c.set_fill(BG, 0).set_stroke(MUTED, width=0.6, opacity=0.35)
            self.cells.add(c)
        self.cells.center()
        self.add(self.cells)
        self.label = None
        if label is not None:
            self.label = Tex(label, font_size=30, color=FG).next_to(self.cells, DOWN, buff=0.15)
            self.add(self.label)


class GRUCell(VGroup):
    """Rounded box with a label and a strip standing in for the hidden state."""

    def __init__(self, label, color, n_state=10, width=1.6, height=1.0, **kwargs):
        super().__init__(**kwargs)
        self.layer_color = color
        self.box = RoundedRectangle(width=width, height=height, corner_radius=0.15)
        self.box.set_stroke(color, width=2.5).set_fill(BG, 1)
        self.label = Tex(label, font_size=28, color=color)
        self.label.move_to(self.box.get_center() + UP * height * 0.2)
        side = min(0.11, 0.85 * width / (n_state * 1.25))
        self.state = VGroup(*(Square(side).set_stroke(color, 0.6, 0.6).set_fill(color, 0.12)
                              for _ in range(n_state)))
        self.state.arrange(RIGHT, buff=side * 0.25)
        self.state.move_to(self.box.get_center() + DOWN * height * 0.22)
        self.add(self.box, self.label, self.state)

    def update_state(self, rng, values=None, **kwargs):
        """Animate new state intensities (random unless values are given)."""
        values = rng.uniform(0.1, 1.0, len(self.state)) if values is None else values
        return AnimationGroup(*(sq.animate.set_fill(self.layer_color, float(v))
                                for sq, v in zip(self.state, values)), **kwargs)


def diverging_color(v, vmax=1.0):
    """BG at 0, STATE_POS at +vmax, STATE_NEG at -vmax."""
    a = float(np.clip(v / vmax, -1, 1))
    return interpolate_color(BG, STATE_POS if a >= 0 else STATE_NEG, abs(a))


class StateHeatmap(VGroup):
    """A hidden-state vector reshaped to a grid, on a fixed diverging scale."""

    def __init__(self, values, shape=(14, 20), cell=0.045, vmax=1.0, **kwargs):
        super().__init__(**kwargs)
        grid = np.asarray(values, dtype=float).reshape(shape)
        for i, row in enumerate(grid):
            for j, v in enumerate(row):
                sq = Square(cell).set_stroke(width=0).set_fill(diverging_color(v, vmax), 1)
                self.add(sq.move_to([j * cell, -i * cell, 0]))
        self.center()


class HeadBox(VGroup):
    def __init__(self, color=FG, **kwargs):
        super().__init__(**kwargs)
        self.text = Tex(r"\text{head} \to P(\text{flip})", font_size=28, color=color)
        self.box = RoundedRectangle(width=self.text.get_width() + 0.4,
                                    height=self.text.get_height() + 0.3, corner_radius=0.12)
        self.box.set_stroke(color, width=2).set_fill(BG, 1).move_to(self.text)
        self.add(self.box, self.text)


class PFlipGauge(VGroup):
    """Horizontal bar with a P(flip) readout; fill_to(v) animates it."""

    def __init__(self, color=EVENT, width=2.4, height=0.26, **kwargs):
        super().__init__(**kwargs)
        self.tracker = ValueTracker(0.0)
        self.outline = Rectangle(width=width, height=height).set_stroke(MUTED, 1.5)
        self.bar = Rectangle(width=width, height=height).set_stroke(width=0).set_fill(color, 1)
        self.name = Tex(r"P(\text{flip})", font_size=26, color=FG)
        self.name.next_to(self.outline, LEFT, buff=0.2)
        self.number = DecimalNumber(0, num_decimal_places=2, font_size=26, color=FG)
        self.number.next_to(self.outline, RIGHT, buff=0.2)

        def track(bar):
            v = max(self.tracker.get_value(), 1e-3)
            bar.set_width(width * v, stretch=True).align_to(self.outline, LEFT)
            bar.set_y(self.outline.get_y())

        self.bar.add_updater(track)
        self.number.add_updater(lambda m: m.set_value(self.tracker.get_value()))
        track(self.bar)
        self.add(self.outline, self.bar, self.name, self.number)

    def fill_to(self, v, **kwargs):
        return self.tracker.animate.set_value(v).set_anim_args(**kwargs)


def _ends(a, b):
    a = a.get_center() if hasattr(a, "get_center") else np.asarray(a)
    b = b.get_center() if hasattr(b, "get_center") else np.asarray(b)
    return a, b


def flow_arrow(a, b, color=MUTED, buff=0.08, thickness=2.5):
    a, b = _ends(a, b)
    return Arrow(a, b, buff=buff, thickness=thickness, fill_color=color)


def pulse_along(a, b=None, color=FG, width=7, time_width=0.5, **kwargs):
    """Flash of light travelling from a to b (or along an arrow passed as a)."""
    if b is None:
        a, b = a.get_start(), a.get_end()
    else:
        a, b = _ends(a, b)
    return ShowPassingFlash(Line(a, b).set_stroke(color, width), time_width=time_width,
                            **kwargs)


def caption(text, size=26, color=FG):
    return Text(text, font=FONT, font_size=size, color=color)
