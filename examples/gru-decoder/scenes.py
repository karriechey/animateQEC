from pathlib import Path

from animateqec import *

DATA = Path(__file__).parent / "data"
VIZ = load_viz(DATA / "viz_data.json")
SHOT = 281049  # fewest-event MWPM failure in 1M shots; a display shot, not RealShot's
SAMPLE = pick_sample(VIZ, shot=SHOT)
STEPS = sorted(int(t) for t in VIZ["rounds"])  # Stim detector time t = GRU step
D = VIZ["meta"]["distance"]
N_SLOTS = len(slot_order(VIZ))

LAT_H = 5.6
STACK_DZ = 0.55
STACK_CENTER = OUT * STACK_DZ * STEPS[-1] / 2
STACK_HEIGHT = 12
STACK_PHI = 62
STACK_THETA = (-30, -50)  # start and end of the slow turn; FlattenToVectors starts at the end


def events(t):
    return SAMPLE["events_by_round"].get(str(t), [])


def hud_text(text, size=CAPTION_SIZE, color=FG):
    return caption(text, size, color).fix_in_frame()


def backed(m, opacity=0.85):
    """Caption on a dark panel, for text drawn over a busy lattice."""
    bg = BackgroundRectangle(m, fill_color=BG, fill_opacity=opacity, buff=0.12)
    return VGroup(bg, m).fix_in_frame()


def stack_slices():
    """One faint lattice per round, with that round's events, shifted along OUT."""
    slices = Group()
    for t in STEPS:
        lat = SurfaceCodeLattice(VIZ, height=LAT_H, plaquette_opacity=0.05, show_ancillas=False)
        lat.plaquettes.set_stroke(width=1, opacity=0.18)
        lat.data_dots.set_opacity(0.12)
        glows = lat.event_glows(events(t))
        s = Group(lat, glows).shift(OUT * STACK_DZ * t)
        s.lat, s.glows = lat, glows
        slices.add(s)
    return slices


def set_stack_view(frame, theta):
    frame.reorient(theta, STACK_PHI, 0).move_to(STACK_CENTER).set_height(STACK_HEIGHT)


class SyndromeHistory(Scene):
    def construct(self):
        n_data, n_anc = len(VIZ["qubits"]["data"]), len(VIZ["qubits"]["ancilla"])
        title = hud_text(f"A distance-{D} surface code", TITLE_SIZE).to_corner(UL)
        sub = hud_text(f"{n_data} data qubits · {n_anc} measure qubits", CAPTION_SIZE, MUTED)
        sub.next_to(title, DOWN, aligned_edge=LEFT)
        lat = SurfaceCodeLattice(VIZ, height=LAT_H).shift(DOWN * 0.4)

        self.play(FadeIn(title, shift=0.2 * DOWN), FadeIn(sub))
        self.play(LaggedStartMap(FadeIn, lat.data_dots, lag_ratio=0.01), run_time=1.2)
        self.play(LaggedStartMap(DrawBorderThenFill, lat.plaquettes, lag_ratio=0.01),
                  FadeIn(lat.ancilla_dots), run_time=2)

        legend = self.legend(lat).fix_in_frame()
        counter_label = Tex("t =", font_size=40).fix_in_frame()
        counter = Integer(0, font_size=40).fix_in_frame()
        counter_grp = VGroup(counter_label, counter).arrange(RIGHT, buff=0.15)
        counter_grp.next_to(legend, DOWN, buff=0.7, aligned_edge=LEFT)
        shot_tag = hud_text(f"detection events of one sampled shot (#{SHOT})", SMALL_SIZE, MUTED)
        shot_tag.to_corner(DR)
        self.play(FadeIn(legend), FadeIn(counter_grp), FadeIn(shot_tag))

        for t in STEPS:
            glows = lat.event_glows(events(t))
            self.play(counter.animate.set_value(t), run_time=0.2)
            if len(glows):
                self.play(LaggedStartMap(GrowFromCenter, glows, lag_ratio=0.1), run_time=0.5)
                self.wait(0.35)
                self.play(FadeOut(glows), run_time=0.25)
            else:
                self.wait(0.6)

        slices = stack_slices()
        stack_cap = hud_text(f"all {len(STEPS)} rounds stacked; time runs upward", CAPTION_SIZE)
        stack_cap.next_to(sub, DOWN, buff=0.35, aligned_edge=LEFT)
        self.play(
            FadeOut(lat), FadeOut(counter_grp), FadeOut(legend[:2]),
            legend[2].animate.to_corner(UR),
            LaggedStartMap(FadeIn, slices, lag_ratio=0.12),
            self.frame.animate.reorient(STACK_THETA[0], STACK_PHI, 0)
                .move_to(STACK_CENTER).set_height(STACK_HEIGHT),
            FadeIn(stack_cap),
            run_time=3,
        )
        self.play(self.frame.animate.increment_theta((STACK_THETA[1] - STACK_THETA[0]) * DEGREES),
                  run_time=5, rate_func=linear)
        self.wait(0.5)

    def legend(self, lat):
        s = 0.28
        rows = [
            (Square(s).set_fill(Z_CHECK, 0.6).set_stroke(Z_CHECK, 1.5), "Z check"),
            (Square(s).set_fill(X_CHECK, 0.6).set_stroke(X_CHECK, 1.5), "X check"),
            (VGroup(Dot(radius=0.2, fill_color=EVENT, fill_opacity=0.22),
                    Dot(radius=0.085, fill_color=EVENT)), "detector fired"),
        ]
        g = VGroup(*(VGroup(icon, caption(text, CAPTION_SIZE)).arrange(RIGHT, buff=0.25)
                     for icon, text in rows))
        g.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        return g.next_to(lat, RIGHT, buff=0.8).align_to(lat, UP)


# ---- shared layout of the input row and the GRU grid ---------------------------------
SHOWN = [0, 1, 2, 3, STEPS[-1]]  # steps drawn as columns; the rest sit in the ellipsis
XS = [-5.0, -2.9, -0.8, 1.3, 4.6]
ELLIPSIS_X = (XS[3] + XS[4]) / 2
HIDDEN = SHOWN[3] + 1, STEPS[-1] - 1  # first and last step inside the ellipsis
VEC_Y, VEC_H = -2.75, 1.9
ROW0_Y, ROW_DY = -0.35, 1.75
OPEN_FRAME = dict(height=6.9, center=DOWN * 1.0)
UNITS = 280  # hidden units per layer of the f2280 / f3280 decoders (GRU_all_runs csv)


def input_vector(t):
    b = step_bits(VIZ, SAMPLE, t)
    return DetectorVector(N_SLOTS, b.fired, f"x_{{{t}}}", present=b.present, height=VEC_H)


def input_row():
    """The StackedGRU opening layout: x_0 x_1 x_2 x_3 ... x_9."""
    vecs = VGroup(*(input_vector(t) for t in SHOWN))
    for v, x in zip(vecs, XS):
        v.move_to([x, VEC_Y, 0], coor_mask=[1, 0, 0]).shift((VEC_Y - v.cells.get_y()) * UP)
    dots = Tex(r"\cdots", font_size=48, color=FG).move_to([ELLIPSIS_X, VEC_Y, 0])
    dots_label = caption(f"rounds {HIDDEN[0]}–{HIDDEN[1]}", SMALL_SIZE, MUTED)
    dots_label.next_to(dots, DOWN, buff=0.35)
    return vecs, VGroup(dots, dots_label)


def set_open_frame(frame):
    frame.reorient(0, 0, 0).set_height(OPEN_FRAME["height"]).move_to(OPEN_FRAME["center"])


class FlattenToVectors(Scene):
    def construct(self):
        slices = stack_slices()
        set_stack_view(self.frame, STACK_THETA[1])
        self.add(slices)

        slot = {xy: j for j, xy in enumerate(slot_order(VIZ))}
        det = VIZ["detectors"]
        xs = np.linspace(-5.6, 5.6, len(STEPS))
        vecs = VGroup(*(input_vector(t).move_to([x, VEC_Y - 0.1, 0]) for t, x in zip(STEPS, xs)))
        cap1 = hud_text(f"each round becomes one {N_SLOTS}-slot vector xₜ").to_edge(UP)
        n_edge = len(VIZ["rounds"][str(STEPS[0])])
        sub = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
        cap2 = hud_text(f"x₀ and x{str(STEPS[-1]).translate(sub)}: only the {n_edge} Z checks are measured "
                        "(hollow slots stay zero)", SMALL_SIZE, MUTED).next_to(cap1, DOWN)

        moves = []
        for s, v, t in zip(slices, vecs, STEPS):
            for g, i in zip(s.glows, events(t)):
                cell = v.cells[slot[(det[i]["x"], det[i]["y"])]]
                moves.append(g.animate.move_to(cell).set_width(cell.get_width()).set_opacity(0))
        target = self.frame.copy()
        set_open_frame(target)
        self.play(
            *(FadeOut(s.lat) for s in slices), *moves,
            LaggedStartMap(FadeIn, vecs, lag_ratio=0.06),
            self.frame.animate.reorient(0, 0, 0).set_height(OPEN_FRAME["height"])
                .move_to(OPEN_FRAME["center"]),
            FadeIn(cap1), run_time=3,
        )
        self.remove(slices)
        self.play(FadeIn(cap2), run_time=0.6)
        self.wait(1.2)

        row, dots = input_row()
        keep = [STEPS.index(t) for t in SHOWN]
        hidden = VGroup(*(v for i, v in enumerate(vecs) if i not in keep))
        self.play(
            *(ReplacementTransform(vecs[i], r) for i, r in zip(keep, row)),
            hidden.animate.arrange(RIGHT, buff=0.02).scale(0.3).move_to(dots[0]).set_opacity(0),
            FadeIn(dots), FadeOut(cap1), FadeOut(cap2), run_time=1.8,
        )
        self.remove(hidden)
        self.wait(0.5)


class StackedGRU(Scene):
    N_LAYERS = 2

    def construct(self):
        self.rng = np.random.default_rng(0)
        set_open_frame(self.frame)
        self.row, self.dots = input_row()
        self.add(self.row, self.dots)

        title = hud_text(f"A {self.N_LAYERS}-layer stacked GRU", TITLE_SIZE)
        note = hud_text(f"state strips are illustrative ({UNITS} units per layer)",
                        SMALL_SIZE, MUTED)
        self.hud = VGroup(VGroup(title, note).arrange(DOWN, aligned_edge=LEFT, buff=0.12))
        self.hud.to_corner(UL)
        self.play(FadeIn(self.hud))

        self.layers = []  # per layer: dict of cells, up arrows, side arrows, dots
        for l in range(self.N_LAYERS):
            eq = self.equation(l)
            parts = self.build_layer(l)
            extra = []
            if l == self.N_LAYERS - 1:
                head, gauge = self.readout(parts["cells"][-1])
                extra = [head, gauge]
            if l == 1:
                beat = hud_text("Layer 2 never sees the detectors, only layer 1's running summary",
                                CAPTION_SIZE, L2)
                eq = VGroup(eq, beat).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
            self.hud.add(eq)
            self.hud.arrange(DOWN, aligned_edge=LEFT, buff=0.25).to_corner(UL)
            if l > 0:
                self.fit_camera(parts, extra)
            self.play(FadeIn(eq if l != 1 else eq[0]), run_time=0.6)
            self.animate_layer(l, parts)
            self.layers.append(parts)
            if l == 0:
                self.fit_camera(None, list(self.readout(parts["cells"][-1])))
                self.show_readout(parts["cells"][-1], keep=False)
            if l == 1:
                self.layer2_beat(eq[1])
                # drop the caption so later fits only dodge the narrow equation lines
                self.play(FadeOut(eq[1]), run_time=0.5)
                self.hud.replace_submobject(len(self.hud) - 1, eq[0])
                self.hud.arrange(DOWN, aligned_edge=LEFT, buff=0.25).to_corner(UL)
        self.show_readout(self.layers[-1]["cells"][-1], keep=True)
        self.wait(1.5)

    # ---- pieces ----
    def equation(self, l):
        color = LAYER_COLORS[l]
        inp = "x_t" if l == 0 else f"h^{{{l}}}_t"
        return Tex(rf"h^{{{l + 1}}}_t = \mathrm{{GRU}}_{{{l + 1}}}({inp},\, h^{{{l + 1}}}_{{t-1}})",
                   font_size=34, color=color).fix_in_frame()

    def build_layer(self, l):
        color, y = LAYER_COLORS[l], ROW0_Y + l * ROW_DY
        below = self.row if l == 0 else self.layers[l - 1]["cells"]
        cells = VGroup(*(GRUCell(f"h^{{{l + 1}}}_{{{t}}}", color).move_to([x, y, 0])
                         for t, x in zip(SHOWN, XS)))
        up_color = FG if l == 0 else LAYER_COLORS[l - 1]
        ups = VGroup(*(flow_arrow(b.get_top() if l else b.cells.get_top(), c.get_bottom(), up_color)
                       for b, c in zip(below, cells)))
        dots = Tex(r"\cdots", font_size=48, color=color).move_to([ELLIPSIS_X, y, 0])
        sides = VGroup()
        for a, b in zip(cells[:3], cells[1:4]):
            sides.add(flow_arrow(a.get_right(), b.get_left(), color))
        sides.add(flow_arrow(cells[3].get_right(), dots.get_left(), color),
                  flow_arrow(dots.get_right(), cells[4].get_left(), color))
        return dict(cells=cells, ups=ups, sides=sides, dots=dots, color=color)

    def animate_layer(self, l, p):
        cells, ups, sides, color = p["cells"], p["ups"], p["sides"], p["color"]
        fast = l > 0
        rt = 0.35 if fast else 0.6
        for k, cell in enumerate(cells):
            anims = [GrowArrow(ups[k]), FadeIn(cell, shift=0.1 * UP)]
            if k == 4:
                self.play(FadeIn(p["dots"]), GrowArrow(sides[3]), run_time=rt)
                anims.append(GrowArrow(sides[4]))
            elif k > 0:
                anims.append(GrowArrow(sides[k - 1]))
            self.play(*anims, run_time=rt)
            pulses = [pulse_along(ups[k], color=LAYER_COLORS[l - 1] if l else FG)]
            if k > 0:
                pulses.append(pulse_along(sides[4 if k == 4 else k - 1], color=color))
            self.play(*pulses, cell.update_state(self.rng), run_time=rt)

    def readout(self, cell):
        head = HeadBox().next_to(cell, UP, buff=0.55)
        gauge = PFlipGauge().next_to(head, UP, buff=0.35)
        gauge_cap = caption("illustrative output", SMALL_SIZE, MUTED).next_to(gauge, UP, buff=0.15)
        arrow = flow_arrow(cell.get_top(), head.get_bottom(), cell.layer_color)
        return VGroup(head, arrow), VGroup(gauge, gauge_cap)

    def show_readout(self, cell, keep):
        (head, arrow), (gauge, gauge_cap) = self.readout(cell)
        value = 0.9 if SAMPLE["logical_flip"] else 0.08
        self.play(GrowArrow(arrow), FadeIn(head), FadeIn(gauge), FadeIn(gauge_cap), run_time=0.6)
        self.play(pulse_along(arrow, color=cell.layer_color), gauge.fill_to(value, run_time=1.2))
        self.wait(0.6)
        if not keep:
            self.play(FadeOut(VGroup(head, arrow, gauge, gauge_cap)), run_time=0.5)

    def layer2_beat(self, beat):
        l1, l2 = self.layers[0], self.layers[1]
        dim = VGroup(self.row, self.dots, l1["ups"])
        self.play(FadeIn(beat), dim.animate.set_opacity(0.2), run_time=0.8)
        self.play(LaggedStart(*(pulse_along(a, color=L1, time_width=0.8) for a in l2["ups"]),
                              lag_ratio=0.15), run_time=1.6)
        self.wait(0.6)
        self.play(dim.animate.set_opacity(1), run_time=0.6)
        # set_opacity(1) also fills hollow input slots; rebuild the row as it was
        row, dots = input_row()
        self.remove(self.row, self.dots)
        self.row, self.dots = row, dots
        self.add(row, dots)

    def fit_camera(self, parts, extra):
        """Smallest frame, flush bottom-right on the network, whose HUD box misses it."""
        boxes = [*self.row, self.dots]
        for p in [*self.layers, parts] if parts else self.layers:
            boxes += [*p["cells"], p["dots"]]
        boxes += extra
        net = VGroup(*boxes)
        m = 0.5
        hud_box = self.hud.get_bounding_box()
        h = self.frame.get_height()
        while True:
            w = h * FRAME_WIDTH / FRAME_HEIGHT
            c = np.array([net.get_right()[0] + m - w / 2, net.get_bottom()[1] - m + h / 2, 0])
            k = h / FRAME_HEIGHT
            hb = c + hud_box * k + np.array([[-1, -1, 0], [0, 0, 0], [1, 1, 0]]) * 0.25 * k
            fits = net.get_left()[0] >= c[0] - w / 2 + m and net.get_top()[1] <= c[1] + h / 2 - m
            clear = all(not self._overlap(b.get_bounding_box(), hb) for b in boxes)
            if fits and clear:
                break
            h += 0.1
        self.play(self.frame.animate.set_height(h).move_to(c), run_time=1.2)

    @staticmethod
    def _overlap(a, b):
        return (a[0][0] < b[2][0] and b[0][0] < a[2][0] and
                a[0][1] < b[2][1] and b[0][1] < a[2][1])


class StackedGRU3(StackedGRU):
    N_LAYERS = 3


OP_NAMES = {"R": "reset", "H": "Hadamard on X-type measure qubits", "CX": "CNOT layer",
            "MR": "measure and reset measure qubits"}


class DetectorRegion(Scene):
    def construct(self):
        det_i = VIZ["meta"]["detslice_Z"]
        det = VIZ["detectors"][det_i]
        region = VIZ["regions"][str(det_i)]
        lat = SurfaceCodeLattice(VIZ, height=LAT_H, plaquette_opacity=0.12)
        lat.plaquettes.set_stroke(opacity=0.35)
        anchor = lat.detector_point(det_i)
        self.frame.set_height(4.6).move_to(anchor)
        self.add(lat)

        title = VGroup(
            hud_text("a detector compares one check across two rounds", CAPTION_SIZE),
            hud_text(f"Stim detecting region of one Z detector (t = {det['t']})", SMALL_SIZE, MUTED),
        ).arrange(DOWN, buff=0.12)
        title = backed(title).to_edge(UP)
        tick_lbl = backed(hud_text(" ", CAPTION_SIZE)).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(title), Flash(anchor, color=Z_CHECK), run_time=1)

        # which measurement each MR tick is, for this detector: first m0, then m1
        mr_ticks = [r["tick"] for r in region if "MR" in r["ops"]]
        n_cx, shape = 0, None
        for r in region:
            if "R" in r["ops"] or "MR" in r["ops"]:
                n_cx = 0
            if "CX" in r["ops"]:
                n_cx += 1
            text = ", ".join(OP_NAMES.get(o, o) + (f" {n_cx}" if o == "CX" else "") for o in r["ops"])
            if r["tick"] in mr_ticks:
                text = "measure: m₀ recorded; region now sits on the full plaquette"
            new_lbl = backed(hud_text(f"tick {r['tick']}: {text or 'idle'}", CAPTION_SIZE))
            new_lbl.move_to(tick_lbl)
            new_shape = lat.region_shape(r["qubits"].keys(), Z_CHECK)
            anims = [FadeTransform(tick_lbl, new_lbl)]
            anims.append(FadeIn(new_shape) if shape is None else ReplacementTransform(shape, new_shape))
            self.play(*anims, run_time=0.45)
            self.wait(0.35 if r["tick"] not in mr_ticks else 1.0)
            tick_lbl, shape = new_lbl, new_shape

        end = r["tick"] + 1
        final = backed(VGroup(
            hud_text(f"tick {end}: measure: m₁ recorded; detector =", CAPTION_SIZE),
            Tex(r"m_0 \oplus m_1", font_size=34, color=FG).fix_in_frame(),
        ).arrange(RIGHT, buff=0.15))
        final.move_to(tick_lbl)
        glow = lat.event_glows([det_i])
        self.play(FadeTransform(tick_lbl, final), ShrinkToCenter(shape), run_time=0.6)
        self.play(GrowFromCenter(glow), run_time=0.5)
        self.wait(1.5)
