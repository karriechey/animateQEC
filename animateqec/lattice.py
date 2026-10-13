"""Surface-code lattice drawn from a viz dict."""
import numpy as np
from collections import Counter

from manimlib import Circle, DashedLine, Dot, Line, Polygon, VectorizedPoint, VGroup

from .style import BASIS_COLOR, EVENT, FG, MWPM, MWPM_WIDTH


class SurfaceCodeLattice(VGroup):
    """Plaquettes, data qubits and measure qubits, centred at the origin."""

    def __init__(self, viz, height=6.0, plaquette_opacity=0.35, show_ancillas=True, **kwargs):
        super().__init__(**kwargs)
        self.viz = viz
        data_xy = np.array([q["xy"] for q in viz["qubits"]["data"]])
        all_xy = np.array([q["xy"] for q in viz["qubits"]["ancilla"]] + data_xy.tolist())
        lo, hi = all_xy.min(0), all_xy.max(0)
        self._center = (lo + hi) / 2
        self._scale = height / (hi[1] - lo[1])
        # Stim's qubit spacing between data qubits is 2 coordinate units
        self.unit = 2 * self._scale

        self.plaquettes = VGroup()
        self.plaquette_of = {}
        for s in viz["stabilizers"]:
            pts = self._polygon_points(s)
            poly = Polygon(*pts)
            poly.set_fill(BASIS_COLOR[s["basis"]], opacity=plaquette_opacity)
            poly.set_stroke(BASIS_COLOR[s["basis"]], width=1.5, opacity=0.8)
            self.plaquettes.add(poly)
            self.plaquette_of[s["ancilla"]] = poly

        r = 0.11 * self.unit
        self.data_dots = VGroup(*(Dot(self._local(q["xy"]), radius=r, fill_color=FG)
                                  for q in viz["qubits"]["data"]))
        self.ancilla_dots = VGroup(*(
            Dot(self._local(a["xy"]), radius=0.6 * r, fill_color=BASIS_COLOR[a["basis"]])
            for a in viz["qubits"]["ancilla"]))
        self.qubit_xy = {q["q"]: q["xy"] for q in viz["qubits"]["data"] + viz["qubits"]["ancilla"]}
        # hidden Stim-frame anchors at (0,0), (1,0), (0,1); they move with the group, so
        # to_point stays right after shifts, scales and rotations
        self.anchors = VGroup(*(VectorizedPoint(self._local(p)) for p in ((0, 0), (1, 0), (0, 1))))
        self.add(self.plaquettes, self.data_dots, self.anchors)
        if show_ancillas:
            self.add(self.ancilla_dots)

    def _local(self, xy):
        x, y = (np.asarray(xy[:2], dtype=float) - self._center) * self._scale
        return np.array([x, -y, 0.0])

    def to_point(self, xy):
        """Stim (x, y) to the current scene point; Stim's y grows downward."""
        o, ex, ey = (a.get_center() for a in self.anchors)
        return o + xy[0] * (ex - o) + xy[1] * (ey - o)

    def _polygon_points(self, stab):
        anc = np.array(stab["xy"])
        pts = [np.array(p) for p in stab["data_xy"]]
        if len(pts) == 2:
            # boundary check: triangle out to the measure qubit
            pts = [pts[0], anc, pts[1]]
        else:
            pts.sort(key=lambda p: np.arctan2(p[1] - anc[1], p[0] - anc[0]))
        return [self._local(p) for p in pts]

    def detector_point(self, det_index):
        d = self.viz["detectors"][det_index]
        return self.to_point((d["x"], d["y"]))

    def event_glows(self, det_indices, color=EVENT):
        """One halo + core dot per fired position, plus an outer ring per repeat.

        Detectors from different rounds can share an (x, y); each extra occurrence there
        gets one more ring instead of a second dot drawn on top of the first.
        """
        o, ex, _ = (a.get_center() for a in self.anchors)
        r = 0.32 * np.linalg.norm(ex - o)
        det = self.viz["detectors"]
        counts = Counter((det[i]["x"], det[i]["y"]) for i in det_indices)
        glows = VGroup()
        for xy, n in counts.items():
            p = self.to_point(xy)
            g = VGroup(Dot(p, radius=2.4 * r, fill_color=color, fill_opacity=0.22),
                       Dot(p, radius=r, fill_color=color))
            for k in range(1, n):
                g.add(Circle(radius=(1.2 + 0.45 * k) * r).move_to(p)
                      .set_stroke(color, width=2.5).set_fill(opacity=0))
            glows.add(g)
        return glows

    def matching_edges(self, edges, color=MWPM, width=MWPM_WIDTH):
        """Thick dashed lines for matched detector pairs, projected onto the lattice.

        A boundary edge (-1) runs to the detector's boundary data qubit: one in its own
        check's support that no other check of the same basis covers. Pairs at the same
        (x, y) in different rounds (time-like edges) have no length here and are skipped;
        their count is kept in .n_timelike.
        """
        det = self.viz["detectors"]
        covered = Counter()
        for s in self.viz["stabilizers"]:
            for q in s["data"]:
                covered[(s["basis"], q)] += 1
        stab_of = {s["ancilla"]: s for s in self.viz["stabilizers"]}
        lines = VGroup()
        lines.n_timelike = 0
        for a, b in edges:
            if a < 0:
                a, b = b, a
            pa = np.array([det[a]["x"], det[a]["y"]])
            if b >= 0:
                pb = np.array([det[b]["x"], det[b]["y"]])
            else:
                s = stab_of[det[a]["ancilla"]]
                ends = [q for q in s["data"] if covered[(s["basis"], q)] == 1] or s["data"]
                pb = np.array(min((self.qubit_xy[q] for q in ends),
                                  key=lambda xy: np.linalg.norm(np.array(xy) - pa)))
            if np.allclose(pa, pb):
                lines.n_timelike += 1
                continue
            lines.add(DashedLine(self.to_point(pa), self.to_point(pb), dash_length=0.12)
                      .set_stroke(color, width))
        return lines

    def region_shape(self, qubits, color, opacity=0.35):
        """Filled convex hull over the given qubits, plus a dot on each."""
        pts = [self.to_point(self.qubit_xy[int(q)]) for q in qubits]
        o, ex, _ = (a.get_center() for a in self.anchors)
        r = 0.22 * np.linalg.norm(ex - o)
        shape = VGroup()
        hull = _convex_hull(pts)
        if len(hull) >= 3:
            shape.add(Polygon(*hull).set_fill(color, opacity).set_stroke(color, 3))
        elif len(hull) == 2:
            shape.add(Line(*hull).set_stroke(color, 10, opacity=0.6))
        shape.add(*(Dot(p, radius=r, fill_color=color).set_stroke(FG, 2) for p in pts))
        return shape


def _turn(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _convex_hull(pts):
    """Monotone-chain hull of 2-D points (z ignored), counter-clockwise."""
    pts = sorted({(round(p[0], 6), round(p[1], 6)) for p in pts})
    if len(pts) <= 2:
        return [np.array([*p, 0.0]) for p in pts]

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and _turn(h[-2], h[-1], p) <= 0:
                h.pop()
            h.append(p)
        return h[:-1]

    return [np.array([*p, 0.0]) for p in half(pts) + half(pts[::-1])]
