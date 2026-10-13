from pathlib import Path

from animateqec import *
from animateqec import sound

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


def hud_math(text, size=CAPTION_SIZE, color=FG):
    """Caption with inline $math$, set by LaTeX; CMU Serif lacks most Unicode subscripts."""
    return TexText(text, font_size=size, color=color).fix_in_frame()


def backed(m, opacity=0.85):
    """Caption on a dark panel, for text drawn over a busy lattice."""
    bg = BackgroundRectangle(m, fill_color=BG, fill_opacity=opacity, buff=0.12)
    return VGroup(bg, m).fix_in_frame()


def stack_slices():
    """One faint lattice per round, with that round's events, shifted along OUT."""
    slices = Group()
    for t in STEPS:
        lat = SurfaceCodeLattice(VIZ, height=LAT_H, show_ancillas=False)
        lat.plaquettes.set_fill(opacity=0.04)
        for e in lat.edges:  # faint neon, so ten stacked slices stay readable
            e.set_stroke(opacity=float(e.get_stroke_opacity()) * 0.3)
        lat.data_dots.set_opacity(0.15)
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
            (Group(GlowDot(radius=0.22, color=EVENT_GLOW, glow_factor=2.2),
                   Dot(radius=0.05, fill_color=EVENT_CORE)), "detector fired"),
        ]
        g = Group(*(Group(icon, caption(text, CAPTION_SIZE)).arrange(RIGHT, buff=0.25)
                    for icon, text in rows))
        g.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        return g.next_to(lat, RIGHT, buff=0.8).align_to(lat, UP)


class SyndromeStackOnly(Scene):
    """Opener: the 3D syndrome history of one shot; ends on FlattenToVectors' first frame."""

    def construct(self):
        slices = stack_slices()
        set_stack_view(self.frame, STACK_THETA[0])
        title = hud_text(f"A distance-{D} surface code: {len(STEPS)} rounds of one shot", TITLE_SIZE)
        title.to_corner(UL)
        sub = hud_text("each slice is one round; dots are detectors that fired; time runs upward",
                       CAPTION_SIZE, MUTED).next_to(title, DOWN, aligned_edge=LEFT)
        self.play(LaggedStartMap(FadeIn, slices, lag_ratio=0.1), FadeIn(title), FadeIn(sub), run_time=2)
        self.play(self.frame.animate.increment_theta((STACK_THETA[1] - STACK_THETA[0]) * DEGREES),
                  run_time=5, rate_func=linear)
        self.play(FadeOut(title), FadeOut(sub), run_time=0.8)


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
        cap1 = hud_math(f"each round becomes one {N_SLOTS}-slot vector $x_t$").to_edge(UP)
        n_edge = len(VIZ["rounds"][str(STEPS[0])])
        cap2 = hud_math(f"$x_0$ and $x_{{{STEPS[-1]}}}$: only the {n_edge} Z checks are measured "
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
    DEPTH_NOTE = None

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
                if self.DEPTH_NOTE:
                    beat = VGroup(beat, hud_text(self.DEPTH_NOTE, CAPTION_SIZE, L2))
                    beat.arrange(DOWN, aligned_edge=LEFT, buff=0.12)
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
    DEPTH_NOTE = f"more nonlinear depth per round, same width (u{UNITS})"


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
                text = "measure: $m_0$ recorded; region now sits on the full plaquette"
            new_lbl = backed(hud_math(f"tick {r['tick']}: {text or 'idle'}", CAPTION_SIZE))
            new_lbl.move_to(tick_lbl)
            new_shape = lat.region_shape(r["qubits"].keys(), Z_CHECK)
            anims = [FadeTransform(tick_lbl, new_lbl)]
            anims.append(FadeIn(new_shape) if shape is None else ReplacementTransform(shape, new_shape))
            self.play(*anims, run_time=0.45)
            self.wait(0.35 if r["tick"] not in mr_ticks else 1.0)
            tick_lbl, shape = new_lbl, new_shape

        end = r["tick"] + 1
        final = backed(hud_math(f"tick {end}: measure: $m_1$ recorded; "
                                r"detector $= m_0 \oplus m_1$", CAPTION_SIZE))
        final.move_to(tick_lbl)
        glow = lat.event_glows([det_i])
        self.play(FadeTransform(tick_lbl, final), ShrinkToCenter(shape), run_time=0.6)
        self.play(GrowFromCenter(glow), run_time=0.5)
        self.wait(1.5)


# ---- RealShot: one real eval-block shot through the trained f3280 checkpoint ------------
TRACE = load_viz(DATA / "shot_trace.json")
RS = TRACE["shots"][0]
RS_META = TRACE["meta"]
assert (RS_META["d"], RS_META["rounds"], RS_META["p"]) == (D, VIZ["meta"]["rounds"], VIZ["meta"]["p"])
RUN_LABEL = "f3280"  # run name in GRU_all_runs (three GRU layers of 280, fresh shots)
RS_XS = np.linspace(-5.0, 6.2, len(STEPS))
RS_VEC_Y, RS_ROWS = -2.9, [-1.3, 0.05, 1.4]
RS_CELL = (1.1, 0.8)


def rs_events(t):
    return RS["events_by_round"].get(str(t), [])


CHORD = [220.0, 261.63, 329.63, 493.88]  # A minor add9


def det_pitch(xy):
    """Lattice (x, y) onto two octaves of the pentatonic scale: low at bottom-left."""
    from animateqec.sound import pentatonic
    return pentatonic(round((xy[0] + (2 * D - xy[1])) / 4))


def start_drift(frame, zoom=0.002, pan=0.004):
    """Very slow push-in and pan; stop_drift returns the frame to its default."""
    frame.add_updater(lambda f, dt: f.set_height(f.get_height() * (1 - zoom * dt)).shift(pan * dt * LEFT))


def stop_drift(frame):
    frame.clear_updaters()
    return frame.animate.to_default_state()


class RealShot(Scene):
    def construct(self):
        self.cues = sound.CueSheet(self)
        # camera push-in -> slight swell of the bed (dB), sampled every frame
        self.cues.track("swell", lambda: 60 * max(0.0, 1 - self.frame.get_height() / FRAME_HEIGHT))
        n_layers = len(RS["hidden"])
        # tick velocity follows the number of fired detectors at each step
        n_fired = np.array([len(rs_events(t)) for t in STEPS])
        self.tick_vel = 0.3 + 0.7 * n_fired / max(n_fired.max(), 1)
        # chord brightness follows the real mean |h| over all layers, min-max scaled over the steps
        mean_h = np.array([np.mean([np.abs(RS["hidden"][l][k]).mean() for l in range(n_layers)])
                           for k in range(len(STEPS))])
        bright = (mean_h - mean_h.min()) / max(np.ptp(mean_h), 1e-9)
        title = hud_text("One real shot, behind the scenes", TITLE_SIZE).to_corner(UL)
        assert not RS_META["held_out_test_set"] and RS["mwpm_pred"] != RS["truth"]
        tag = hud_text(f"shot #{RS['pool_shot']} · {RS['block']} block (not the held-out test set) · "
                       f"{RUN_LABEL}, epoch {RS_META['best']['best_epoch']}",
                       SMALL_SIZE, MUTED).to_corner(DR)
        picked = hud_text("selected as a shot where MWPM fails", CAPTION_SIZE, MUTED)
        picked.next_to(title, DOWN, aligned_edge=LEFT)
        self.play(FadeIn(title), FadeIn(tag), FadeIn(picked))

        # 1. the shot's real detection events, round by round
        lat = SurfaceCodeLattice(VIZ, height=LAT_H).shift(DOWN * 0.3)
        counter = VGroup(Tex("t =", font_size=40), Integer(0, font_size=40)).arrange(RIGHT, buff=0.15)
        counter.fix_in_frame().next_to(lat, RIGHT, buff=0.8).align_to(lat, UP)
        self.play(FadeIn(lat), FadeIn(counter), run_time=1)
        start_drift(self.frame)
        beat0 = self.time
        for t in STEPS:
            glows = lat.event_glows(rs_events(t), glow=True)
            self.play(counter[1].animate.set_value(t), run_time=0.15)
            if len(glows):
                grow = LaggedStart(*(fire(g) for g in glows), lag_ratio=0.4, run_time=0.45)
                self.cues.group(grow, [dict(kind="blip", freq=det_pitch(xy), follow=g)
                                       for xy, g in zip(glows.xys, glows)])
                self.play(grow)
                self.wait(0.2)
                self.play(FadeOut(glows), run_time=0.2)
            else:
                self.wait(0.3)
        self.play(FadeOut(lat), FadeOut(counter), FadeOut(picked), stop_drift(self.frame), run_time=0.6)
        self.density_level(beat0, self.time)

        # 2. the real hidden states, step by step
        vecs = VGroup()
        for t, x in zip(STEPS, RS_XS):
            bits = step_bits(VIZ, {"events_by_round": RS["events_by_round"]}, t)
            v = DetectorVector(N_SLOTS, bits.fired, f"x_{{{t}}}", present=bits.present, height=1.4)
            vecs.add(v.shift([x, RS_VEC_Y, 0] - v.cells.get_center()))
        labels = VGroup(*(caption(f"layer {l + 1}", SMALL_SIZE, LAYER_COLORS[l])
                          .move_to([RS_XS[0] - 1.2, y, 0]) for l, y in enumerate(RS_ROWS)))
        cells, ups, sides = [], [], []
        for l, y in enumerate(RS_ROWS):
            row_cells, row_ups, row_sides = VGroup(), VGroup(), VGroup()
            for k, x in enumerate(RS_XS):
                box = RoundedRectangle(width=RS_CELL[0], height=RS_CELL[1], corner_radius=0.08)
                box.set_stroke(LAYER_COLORS[l], 2).set_fill(BG, 1).move_to([x, y, 0])
                heat = StateHeatmap(RS["hidden"][l][k]).move_to(box)
                row_cells.add(VGroup(box, heat))
                below = vecs[k].cells if l == 0 else cells[l - 1][k]
                row_ups.add(flow_arrow(below.get_top(), box.get_bottom(),
                                       FG if l == 0 else LAYER_COLORS[l - 1], thickness=2))
                if k:
                    row_sides.add(Line(row_cells[k - 1].get_right(), box.get_left())
                                  .set_stroke(LAYER_COLORS[l], 2))
            cells.append(row_cells), ups.append(row_ups), sides.append(row_sides)
        note = hud_text("real hidden states of the trained model: 280 values per layer, "
                        "shown as 14 × 20", SMALL_SIZE, MUTED).next_to(title, DOWN, aligned_edge=LEFT)
        scale = self.state_scale().next_to(note, DOWN, buff=0.15, aligned_edge=LEFT)
        self.play(FadeOut(tag), LaggedStartMap(FadeIn, vecs, lag_ratio=0.05), FadeIn(labels),
                  FadeIn(scale), FadeIn(note), run_time=1.2)
        for k in range(len(STEPS)):
            anims = []
            for l in range(n_layers):
                a = [GrowArrow(ups[l][k]), FadeIn(cells[l][k]),
                     particles_along(ups[l][k], color=FG if l == 0 else LAYER_COLORS[l - 1], n=2, radius=0.26)]
                if k:
                    a.append(ShowCreation(sides[l][k - 1]))
                anims.append(AnimationGroup(*a))
            stack = LaggedStart(*anims, lag_ratio=0.45, run_time=0.9)
            self.cues.at("tick", velocity=self.tick_vel[k])
            self.cues.point("bed_level", -6)
            self.cues.point("bed_bright", 0.15 + 0.75 * bright[k])  # bed cutoff follows mean |h|
            self.cues.group(stack, [None] * (n_layers - 1)
                            + [dict(kind="soft_chord", freqs=CHORD, dur=0.9, brightness=float(bright[k]),
                                    follow=cells[-1][k][0])])
            self.play(Indicate(vecs[k].cells, color=EVENT, scale_factor=1.05, run_time=0.9), stack)
        last = cells[-1][-1]
        head = HeadBox().scale(0.8).next_to(last, UP, buff=0.4)
        head_arrow = flow_arrow(last.get_top(), head.get_bottom(), LAYER_COLORS[n_layers - 1])
        gauge = PFlipGauge(width=1.8).scale(0.8).next_to(head, UP, buff=0.25)
        gauge.to_edge(RIGHT, buff=0.3)
        self.play(GrowArrow(head_arrow), particles_along(head_arrow, color=LAYER_COLORS[n_layers - 1]),
                  FadeIn(head), FadeIn(gauge), run_time=0.6)
        self.play(gauge.fill_to(RS["p_flip"], run_time=1.2))
        self.wait(1)
        network = VGroup(vecs, labels, *cells, *ups, *sides, head, head_arrow, scale, note)
        self.play(FadeOut(network), FadeOut(gauge), run_time=0.8)

        # 3. the path through state space (PCA fit on 2,000 other eval-block shots)
        self.state_space()

        # 4. the verdict on the lattice
        self.verdict()
        self.cues.point("bed_level", -10)
        Path("videos").mkdir(exist_ok=True)
        self.cues.write(Path("videos") / "RealShot.cues.json")

    def density_level(self, t0, t1, sigma=0.5, lo=-16, hi=-4):
        """Bed level over [t0, t1] from the smoothed density of the blips cued in it."""
        ts = np.array([c["t"] for c in self.cues.cues if c["kind"] == "blip" and t0 <= c["t"] <= t1])
        grid = np.arange(t0, t1, 0.05)
        dens = np.exp(-0.5 * ((grid[:, None] - ts[None]) / sigma) ** 2).sum(1) if len(ts) else 0 * grid
        dens = dens / max(dens.max(), 1e-9)
        self.cues.curves.setdefault("bed_level", []).extend(zip(grid, lo + (hi - lo) * dens))

    def state_scale(self):
        n = 21
        bar = VGroup(*(Square(0.12).set_stroke(width=0).set_fill(diverging_color(v), 1)
                       for v in np.linspace(-1, 1, n))).arrange(RIGHT, buff=0)
        lo = Tex("-1", font_size=24, color=FG).next_to(bar, LEFT, buff=0.1)
        hi = Tex("+1", font_size=24, color=FG).next_to(bar, RIGHT, buff=0.1)
        lbl = caption("hidden-state value (fixed scale)", SMALL_SIZE, MUTED).next_to(bar, UP, buff=0.1)
        return VGroup(bar, lo, hi, lbl).fix_in_frame()

    def pca_panel(self, pc, size, color, show_cloud_legend=False):
        var = pc["explained_variance_ratio"]
        cloud = np.array(pc["cloud_final"])
        path = np.array(pc["trajectories"][str(RS["pool_shot"])])
        pts = np.vstack([cloud, path])
        lo, hi = pts.min(0), pts.max(0)
        pad = 0.08 * (hi - lo)
        axes = Axes(x_range=[lo[0] - pad[0], hi[0] + pad[0]], y_range=[lo[1] - pad[1], hi[1] + pad[1]],
                    width=size, height=size, axis_config=dict(include_ticks=False, stroke_color=MUTED,
                                                               stroke_width=1.5))
        xl = caption(f"PC1 ({100 * var[0]:.0f}%)", SMALL_SIZE, MUTED).next_to(axes, DOWN, buff=0.1)
        yl = caption(f"PC2 ({100 * var[1]:.0f}%)", SMALL_SIZE, MUTED).rotate(PI / 2)
        yl.next_to(axes, LEFT, buff=0.1)
        dots = VGroup(*(Dot(axes.c2p(*c), radius=0.022 * size / 5,
                            fill_color=FLIP if f else NO_FLIP, fill_opacity=0.45)
                        for c, f in zip(cloud, pc["cloud_truth"])))
        steps = VGroup(*(Dot(axes.c2p(*c), radius=0.05 * size / 5, fill_color=color)
                         .set_stroke(FG, 1) for c in path))
        segs = VGroup(*(Line(axes.c2p(*a), axes.c2p(*b)).set_stroke(color, 3)
                        for a, b in zip(path[:-1], path[1:])))
        return VGroup(axes, xl, yl), dots, steps, segs

    def state_space(self):
        pcs = TRACE["pca"]
        main_frame, main_cloud, main_steps, main_segs = self.pca_panel(pcs[-1], 5.4, LAYER_COLORS[len(pcs) - 1])
        VGroup(main_frame, main_cloud, main_steps, main_segs).move_to(LEFT * 1.6 + DOWN * 0.5)
        head = hud_text(f"layer {len(pcs)} state, step by step, in 2-D (PCA)", CAPTION_SIZE,
                        LAYER_COLORS[len(pcs) - 1])
        head.next_to(main_frame, UP, buff=0.25)
        legend = VGroup(*(VGroup(Dot(radius=0.06, fill_color=c), caption(s, SMALL_SIZE))
                          .arrange(RIGHT, buff=0.15)
                          for c, s in ((FLIP, "final state of another shot: truth flip"),
                                       (NO_FLIP, "final state of another shot: truth no flip"))))
        legend.arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        n = len(pcs[-1]["cloud_truth"])
        fit = caption(f"PCA fit on {n:,} other evaluation-block shots", SMALL_SIZE, MUTED)
        side = VGroup(legend, fit).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        side.next_to(main_frame, RIGHT, buff=0.6).align_to(main_frame, UP)
        self.play(FadeIn(main_frame), FadeIn(head), FadeIn(main_cloud, lag_ratio=0.002),
                  FadeIn(side), run_time=1.5)
        # bed builds as the layer-3 path closes on the flip cluster (distance in this PCA plane)
        path = np.array(pcs[-1]["trajectories"][str(RS["pool_shot"])])
        cloud = np.array(pcs[-1]["cloud_final"])
        target = cloud[np.array(pcs[-1]["cloud_truth"]) == RS["truth"]].mean(0)
        dist = np.linalg.norm(path - target, axis=1)
        close = np.clip((dist.max() - dist) / max(np.ptp(dist), 1e-9), 0, 1)
        self.build_db = -10 + 10 * close
        for k in range(len(main_steps)):
            self.cues.at("tick", velocity=self.tick_vel[k], follow=main_steps[k])
            self.cues.point("bed_level", self.build_db[k])
            anims = [GrowFromCenter(main_steps[k])]
            if k:
                anims.append(ShowCreation(main_segs[k - 1]))
            self.play(*anims, run_time=0.3)
        lab = caption(f"t = {STEPS[-1]}", SMALL_SIZE, FG).next_to(main_steps[-1], UR, buff=0.05)
        truth = "flip" if RS["truth"] else "no flip"
        end_cap = caption(f"it ends among shots whose truth is {truth}", CAPTION_SIZE)
        end_cap.next_to(fit, DOWN, buff=0.5, aligned_edge=LEFT)
        self.play(FadeIn(lab), FadeIn(end_cap), Flash(main_steps[-1], color=FG))
        self.wait(1)

        small = VGroup()
        for l, pc in enumerate(pcs[:-1]):
            fr, cl, st, sg = self.pca_panel(pc, 1.9, LAYER_COLORS[l])
            p = VGroup(fr, cl, sg, st)
            p.add(caption(f"layer {l + 1}", SMALL_SIZE, LAYER_COLORS[l]).next_to(fr, UP, buff=0.08))
            small.add(p)
        small.arrange(RIGHT, buff=0.6).next_to(end_cap, DOWN, buff=0.5, aligned_edge=LEFT)
        pct = " / ".join(f"{100 * sum(pc['explained_variance_ratio']):.0f}%" for pc in pcs[:-1])
        weak = caption(f"layers 1–{len(pcs) - 1}: two PCs explain only {pct};\nlittle structure visible",
                       SMALL_SIZE, MUTED).next_to(small, DOWN, buff=0.2, aligned_edge=LEFT)
        self.play(FadeIn(small), FadeIn(weak), run_time=1)
        self.wait(1.5)
        self.play(*(FadeOut(m) for m in self.mobjects if m is not self.cues.probe and (
                    not getattr(m, "fixed_in_frame", False) or m in (head, legend, fit, end_cap, weak))),
                  run_time=0.8)
        self.play(FadeOut(VGroup(head, side, end_cap, weak, lab)), run_time=0.1)

    def verdict(self):
        lat = SurfaceCodeLattice(VIZ, height=LAT_H).to_edge(LEFT, buff=0.8).shift(DOWN * 0.3)
        all_events = [i for t in STEPS for i in rs_events(t)]
        glows = lat.event_glows(all_events, glow=True)
        ev_cap = caption(f"all {RS['n_events']} detection events; rings mark a check\n"
                         "that fired in more than one round", SMALL_SIZE, MUTED)
        ev_cap.next_to(lat, DOWN, buff=0.15)
        self.play(FadeIn(lat), FadeIn(glows), FadeIn(ev_cap), run_time=1)
        start_drift(self.frame, zoom=0.0015, pan=0.003)

        col_x = lat.get_right()[0] + 0.8
        say = lambda name, flip: f"{name}: {'flip' if flip else 'no flip'}"
        gru_l = caption(f"GRU: P(flip) = {RS['p_flip']:.3f}  →  {'flip' if RS['gru_pred'] else 'no flip'}",
                        CAPTION_SIZE, LAYER_COLORS[len(RS['hidden']) - 1])
        gru_l.move_to([0, 1.6, 0]).align_to([col_x, 0, 0], LEFT)
        self.play(FadeIn(gru_l), run_time=0.6)

        chains = lat.matching_edges(RS["mwpm_edges"])
        mwpm_l = caption(say("MWPM", RS["mwpm_pred"]), CAPTION_SIZE, MWPM)
        mwpm_l.next_to(gru_l, DOWN, buff=0.45, aligned_edge=LEFT)
        mwpm_note = caption(f"MWPM matching (dashed); {chains.n_timelike} time-like matches\n"
                            "(same check, different rounds) have no length here",
                            SMALL_SIZE, MUTED).next_to(mwpm_l, DOWN, buff=0.15, aligned_edge=LEFT)
        self.play(LaggedStartMap(ShowCreation, chains, lag_ratio=0.15), FadeIn(mwpm_l),
                  FadeIn(mwpm_note), run_time=2)
        self.wait(0.8)

        truth_l = caption(say("truth", RS["truth"]), CAPTION_SIZE, FG)
        truth_l.next_to(mwpm_note, DOWN, buff=0.5, aligned_edge=LEFT)
        self.play(FadeIn(truth_l, scale=1.2), run_time=0.6)
        ok = lambda pred: "right" if pred == RS["truth"] else "wrong"
        mark_x = max(gru_l.get_right()[0], mwpm_l.get_right()[0]) + 0.5
        g_mark = caption(f"GRU: {ok(RS['gru_pred'])}", CAPTION_SIZE, FG).next_to(gru_l, RIGHT)
        m_mark = caption(f"MWPM: {ok(RS['mwpm_pred'])}", CAPTION_SIZE, FG).next_to(mwpm_l, RIGHT)
        for m in (g_mark, m_mark):
            m.set_x(mark_x + m.get_width() / 2)
        if RS["mwpm_pred"] != RS["truth"]:
            self.cues.at("dissonant", velocity=0.8, follow=m_mark, dur=0.7)
        self.play(FadeIn(m_mark), run_time=0.6)
        # hold the build, drop to near-silence 0.5 s before the GRU's answer, then resolve
        pause = 1.1
        self.cues.point("bed_level", self.build_db[-1])
        self.cues.point("bed_level", self.build_db[-1], offset=pause - 0.9)
        self.cues.point("bed_level", sound.BED_FLOOR_DB, offset=pause - 0.5)
        self.wait(pause)
        self.cues.point("bed_level", sound.BED_FLOOR_DB)
        if RS["gru_pred"] == RS["truth"]:
            self.cues.at("resolve", velocity=2.0, follow=g_mark)
        self.cues.point("bed_level", -16, offset=1.0)
        self.play(FadeIn(g_mark), run_time=0.6)
        self.wait(1.2)

        # optional beat: gradient attribution
        attr = RS["attribution"]["per_detector"]
        top = sorted(attr, key=lambda i: -abs(attr[i]))[:5]
        o, ex, _ = (a.get_center() for a in lat.anchors)
        rr = 0.75 * np.linalg.norm(ex - o)
        rings = VGroup(*(Circle(radius=rr).move_to(lat.detector_point(int(i)))
                         .set_stroke(FG, 4) for i in top))
        a_cap = caption("gradient attribution (integrated gradients):\n"
                        "the 5 detectors that most moved the GRU's logit", SMALL_SIZE, FG)
        a_cap.next_to(truth_l, DOWN, buff=0.6, aligned_edge=LEFT)
        self.play(FadeOut(chains), LaggedStartMap(ShowCreation, rings, lag_ratio=0.2),
                  FadeIn(a_cap), run_time=1.5)
        self.wait(1.5)

        close = caption("This is one shot. The headline numbers come from the held-out test set.",
                        CAPTION_SIZE, FG).to_edge(DOWN, buff=0.35)
        self.play(FadeOut(ev_cap), FadeIn(close), run_time=0.8)
        self.wait(2)


# ---- Results: swap RESULTS for the held-out file when those numbers exist ----------------
RESULTS = DATA / "results_eval_preliminary.csv"


def load_results(path):
    import csv
    if not path.exists():
        return []
    num = lambda v: float(v) if v not in ("", None) else None
    return [{**r, "ler": num(r["ler"]), "ci_low": num(r["ci_low"]), "ci_high": num(r["ci_high"]),
             "ratio_to_mwpm": num(r["ratio_to_mwpm"])} for r in csv.DictReader(open(path))]


class Results(Scene):
    def construct(self):
        rows = load_results(RESULTS)
        title = hud_text(f"Logical error rate per shot, d = {D}, p = {VIZ['meta']['p']}", TITLE_SIZE)
        title.to_corner(UL)
        if not rows:
            card = VGroup(RoundedRectangle(width=6, height=2, corner_radius=0.2).set_stroke(MUTED, 2),
                          caption("RESULTS PENDING", TITLE_SIZE, MUTED))
            self.play(FadeIn(title), FadeIn(card))
            self.wait(3)
            return
        label = hud_text(rows[0]["block_label"], CAPTION_SIZE, EVENT).next_to(title, DOWN, aligned_edge=LEFT)
        mwpm = next(r for r in rows if r["kind"] == "mwpm")

        bar_w, bar_h, gap = 7.0, 0.55, 1.15
        x0 = -2.6
        top = max(r["ci_high"] or r["ler"] for r in rows) * 1.15
        to_x = lambda v: x0 + bar_w * v / top
        bars, extras = VGroup(), VGroup()
        for k, r in enumerate(rows):
            y = 1.0 - k * gap
            color = MWPM if r["kind"] == "mwpm" else L1
            bar = Rectangle(width=to_x(r["ler"]) - x0, height=bar_h).set_stroke(width=0)
            bar.set_fill(color, 0.85).move_to([x0, y, 0], aligned_edge=LEFT)
            name = r["label"] if r["kind"] == "mwpm" else f"{r['label']} · {r['model'].replace('xu', ' × ')} GRU"
            name_m = caption(name, CAPTION_SIZE).next_to(bar, LEFT, buff=0.3)
            val = caption(f"{r['ler']:.6f}".rstrip("0"), SMALL_SIZE).next_to(bar, RIGHT, buff=0.3)
            row = VGroup(bar, name_m, val)
            if r["ci_low"] is not None:
                ci = Line([to_x(r["ci_low"]), y, 0], [to_x(r["ci_high"]), y, 0]).set_stroke(FG, 3)
                row.add(ci, *(Line([x, y - 0.15, 0], [x, y + 0.15, 0]).set_stroke(FG, 3)
                              for x in (to_x(r["ci_low"]), to_x(r["ci_high"]))))
            if r["kind"] == "gru":
                ratio = caption(f"{r['ratio_to_mwpm']:.3f} × MWPM", CAPTION_SIZE, FG)
                ratio.move_to([to_x(top) + 1.45, y, 0])
                extras.add(ratio)
                if r["mcnemar_b"]:
                    mc = caption(f"paired on the same shots: GRU right & MWPM wrong b = {int(r['mcnemar_b']):,}, "
                                 f"reverse c = {int(r['mcnemar_c']):,}; McNemar p = {r['mcnemar_p']}",
                                 SMALL_SIZE, MUTED)
                    mc.next_to(bar, DOWN, buff=0.1).align_to([x0, 0, 0], LEFT)
                    extras.add(mc)
            bars.add(row)
        ref = DashedLine([to_x(mwpm["ler"]), 1.0 + bar_h, 0],
                         [to_x(mwpm["ler"]), 1.0 - (len(rows) - 1) * gap - bar_h, 0],
                         dash_length=0.12).set_stroke(MWPM, MWPM_WIDTH / 2)
        axis = Line([x0, -2.2, 0], [to_x(top), -2.2, 0]).set_stroke(MUTED, 1.5)
        ticks = VGroup()
        step = 0.0005
        for v in np.arange(0, top, step):
            if round(v / step) % 2 == 0:
                ticks.add(VGroup(Line([to_x(v), -2.2, 0], [to_x(v), -2.3, 0]).set_stroke(MUTED, 1.5),
                                 caption(f"{v:g}", SMALL_SIZE, MUTED).move_to([to_x(v), -2.55, 0])))
        axis_lbl = caption("logical error rate (errors per shot)", SMALL_SIZE, MUTED)
        axis_lbl.next_to(axis, DOWN, buff=0.6)
        notes = [f"{rows[0]['source']} · {rows[0]['block']} block"]
        if all(r["ci_low"] is None for r in rows):
            notes.append("no confidence intervals: the runs CSV has no error counts")
        foot = caption(" · ".join(notes), SMALL_SIZE, MUTED).to_corner(DR)

        self.play(FadeIn(title), FadeIn(label), run_time=0.8)
        self.play(ShowCreation(axis), FadeIn(ticks), FadeIn(axis_lbl), run_time=0.6)
        for row in bars:
            self.play(GrowFromEdge(row[0], LEFT), FadeIn(VGroup(*row[1:])), run_time=0.7)
        self.play(ShowCreation(ref), run_time=0.6)
        self.play(LaggedStartMap(FadeIn, extras, lag_ratio=0.3), FadeIn(foot), run_time=1.5)
        self.wait(3)


# ---- model config (scripts/export_model_config.py on grace1) ----------------------------
MODEL_DIR = DATA


def load_model_cfg(run):
    path = MODEL_DIR / f"model_{run}.json"
    return load_viz(path) if path.exists() else None


def pending_card(text):
    return VGroup(RoundedRectangle(width=7, height=2, corner_radius=0.2).set_stroke(MUTED, 2),
                  caption(text, TITLE_SIZE, MUTED))


def gru_params(n_in, u):
    """Keras GRU, reset_after=False: three gates, each W (n_in x u), U (u x u), b (u)."""
    return 3 * (u * (n_in + u) + u)


def architecture(cfg):
    """Folded network diagram built from the exported model config."""
    grus = [l for l in cfg["layers"] if l["class"] == "GRU"]
    heads = [l for l in cfg["layers"] if l["class"] == "Dense"]
    assert len(heads) == 1 and heads[0]["units"] == 1, "expected one Dense(1) head"
    head = heads[0]
    n_t, n_in = cfg["input_shape"][1:]
    shape = lambda l: "(" + ", ".join(str(v) for v in l["output_shape"][1:]) + ")"
    cols = [dict(name="input", size=n_in, color=FG, label=r"x_t", lines=[f"{n_in} detector slots",
                                                                        f"in ({n_t}, {n_in})"])]
    for i, g in enumerate(grus):
        cols.append(dict(name=f"GRU {i + 1}", size=g["units"], color=LAYER_COLORS[i], label=None,
                         lines=[f"{g['units']} units", f"out {shape(g)}", f"{g['params']:,} params"],
                         layer=g))
    cols.append(dict(name="head", size=head["units"], color=FG, label=None,
                     lines=[f"Dense, {head['activation']}", f"out {shape(head)}", f"{head['params']:,} params"]))
    cols.append(dict(name=r"P(flip)", size=1, color=EVENT, label=None, lines=["sigmoid of the logit"]))

    xs = np.linspace(-5.4, 5.4, len(cols))
    y0, dy, rad = 0.55, 0.42, 0.15
    columns, conns, loops, texts = VGroup(), VGroup(), VGroup(), VGroup()
    for c, x in zip(cols, xs):
        n_draw = min(6, c["size"])
        ys = (np.arange(n_draw) - (n_draw - 1) / 2) * -dy
        if c["size"] > 6:
            ys = np.concatenate([ys[:3] + dy / 2, ys[3:] - dy / 2])
        dots = VGroup(*(Circle(radius=rad).set_stroke(c["color"], 2).set_fill(c["color"], 0.25)
                        .move_to([x, y0 + yy, 0]) for yy in ys))
        col = VGroup(dots)
        if c["size"] > 6:
            col.add(Tex(r"\vdots", font_size=30, color=c["color"]).move_to([x, y0, 0]))
        col.dots = dots
        columns.add(col)
        name = caption(c["name"], CAPTION_SIZE, c["color"])
        name.move_to([x, y0 - 1.75, 0])
        info = VGroup(*(caption(t, SMALL_SIZE, MUTED) for t in c["lines"])).arrange(DOWN, buff=0.08)
        info.next_to(name, DOWN, buff=0.15)
        texts.add(VGroup(name, info))
    for a, b in zip(columns[:-1], columns[1:]):
        conns.add(VGroup(*(Line(p.get_center(), q.get_center(), buff=rad).set_stroke(MUTED, 1, 0.22)
                           for p in a.dots for q in b.dots)))
    for i, (c, col) in enumerate(zip(cols, columns)):
        if "layer" not in c:
            continue
        top = col.get_top()
        arc = Arc(start_angle=-PI / 6, angle=4 * PI / 3, radius=0.32).move_to(top + UP * 0.38)
        arc.set_stroke(c["color"], 2.5)
        arc.add_tip(width=0.14, length=0.14)
        arc.get_tips().set_color(c["color"])
        lbl = Tex(rf"h^{{{i}}}_{{t-1}}", font_size=26, color=c["color"]).next_to(arc, UP, buff=0.05)
        loop = VGroup(arc, lbl)
        loop.pivot = top + UP * 0.38
        loops.add(loop)
    inp_info = texts[0][1]
    brace = Brace(inp_info, DOWN, buff=0.12).set_color(MUTED)
    same = caption(f"same weights, applied for t = 0…{n_t - 1}", SMALL_SIZE, FG).next_to(brace, DOWN, buff=0.1)
    best = cfg.get("best") or {}
    title = caption(f"{cfg['run']}: {len(grus)}-layer stacked GRU decoder (folded view)", TITLE_SIZE)
    title.to_corner(UL)
    foot = caption(f"Keras GRU, reset_after = {grus[0]['reset_after']}, recurrent activation "
                   f"{grus[0]['recurrent_activation']} · {cfg['total_params']:,} parameters in total · "
                   f"checkpoint epoch {best.get('best_epoch', '?')}", SMALL_SIZE, MUTED).to_corner(DR)
    return dict(columns=columns, conns=conns, loops=loops, texts=texts, brace=VGroup(brace, same),
                title=title, foot=foot, centres=[col.get_center() for col in columns])


class ArchitectureDiagram(Scene):
    """Still diagram for slides: -s writes the PNG; the SVG goes to videos/<Scene>.svg."""
    RUN = "f3280"

    def construct(self):
        cfg = load_model_cfg(self.RUN)
        if cfg is None:
            self.add(pending_card("MODEL CONFIG PENDING"))
            return
        a = architecture(cfg)
        parts = [a["conns"], a["columns"], a["loops"], a["texts"], a["brace"], a["title"], a["foot"]]
        self.add(*parts)
        from animateqec.svg import to_svg
        out = Path("videos")
        out.mkdir(exist_ok=True)
        to_svg(parts, out / f"{type(self).__name__}.svg", background=BG)


class ArchitectureDiagram2(ArchitectureDiagram):
    RUN = "f2280"


class ArchitectureBuild(Scene):
    """Animated diagram for the team cut: columns left to right, then one pass input to output."""
    RUN = "f3280"

    def construct(self):
        cfg = load_model_cfg(self.RUN)
        if cfg is None:
            self.add(pending_card("MODEL CONFIG PENDING"))
            self.wait(2)
            return
        a = architecture(cfg)
        self.play(FadeIn(a["title"]), run_time=0.5)
        for k, (col, txt) in enumerate(zip(a["columns"], a["texts"])):
            anims = [FadeIn(col, lag_ratio=0.1), FadeIn(txt)]
            if k:
                anims.append(ShowCreation(a["conns"][k - 1], lag_ratio=0.01))
            if k == 0:
                anims.append(FadeIn(a["brace"]))
            self.play(*anims, run_time=0.6)
        self.play(*(FadeIn(l) for l in a["loops"]), FadeIn(a["foot"]), run_time=0.6)
        path = VMobject().set_points_as_corners(a["centres"]).set_stroke(EVENT, 5)
        self.play(ShowPassingFlash(path, time_width=0.35),
                  *(Rotate(l[0], TAU, about_point=l.pivot) for l in a["loops"]),
                  run_time=2.5, rate_func=linear)
        self.wait(2.8)


class GRUCellInside(Scene):
    """One layer-1 cell at one step, with the real values from the RealShot trace."""
    LAYER, STEP = 0, 4

    def construct(self):
        l, k = self.LAYER, self.STEP
        h_prev = np.array(RS["hidden"][l][k - 1])
        h = np.array(RS["hidden"][l][k])
        z = np.array(RS["gates"][l]["z"][k])
        r = np.array(RS["gates"][l]["r"][k])
        ok = (1 - z) > 0.02
        h_tilde = np.where(ok, (h - z * h_prev) / np.where(ok, 1 - z, 1), 0)
        bits = step_bits(VIZ, {"events_by_round": RS["events_by_round"]}, k)
        x = np.zeros(N_SLOTS)
        x[bits.fired] = 1

        title = hud_text("Inside one GRU cell", TITLE_SIZE).to_corner(UL)
        sub = hud_text("Keras GRU with reset_after = False, as in our model", CAPTION_SIZE, MUTED)
        sub.next_to(title, DOWN, aligned_edge=LEFT)
        self.play(FadeIn(title), FadeIn(sub), run_time=0.8)

        sx, sw = 3.1, 7.0
        rows = [
            (r"x_t", x, lambda v: EVENT if v else FAINT, None, f"input: {N_SLOTS} detector slots"),
            (r"h_{t-1}", h_prev, diverging_color, None, f"previous state: {len(h)} units"),
            (r"z_t = \sigma(x_t W_z + h_{t-1} U_z + b_z)", z, gate_color, None, "update gate"),
            (r"r_t = \sigma(x_t W_r + h_{t-1} U_r + b_r)", r, gate_color, None, "reset gate"),
            (r"\tilde h_t = \tanh\!\big(x_t W_h + (r_t \odot h_{t-1})\, U_h + b_h\big)", h_tilde,
             diverging_color, ok, "candidate state"),
            (r"h_t = z_t \odot h_{t-1} + (1 - z_t) \odot \tilde h_t", h, diverging_color, None,
             "new state: z near 1 keeps the old value, z near 0 takes the candidate"),
        ]
        mobs = []
        for i, (eq, vals, cfn, mask, note) in enumerate(rows):
            y = 1.75 - i * 0.78
            e = Tex(eq, font_size=30, color=FG).move_to([0, y, 0]).to_edge(LEFT, buff=0.5)
            width = sw * len(vals) / len(h) if len(vals) < len(h) else sw
            strip = StateStrip(vals, width=width, height=0.3, color_fn=cfn, mask=mask)
            strip.move_to([sx - sw / 2 + width / 2, y, 0])
            n = caption(note, SMALL_SIZE, MUTED).next_to(strip, DOWN, buff=0.06).align_to(strip, LEFT)
            mobs.append((e, strip, n))

        keys = VGroup(self.key(diverging_color, -1, 1, "state"), self.key(gate_color, 0, 1, "gate"))
        keys.arrange(RIGHT, buff=0.6).to_corner(UR)
        self.play(FadeIn(keys), *(FadeIn(m) for m in mobs[0] + mobs[1]), run_time=1.2)
        self.wait(1)
        src = {2: (0, 1), 3: (0, 1), 4: (0, 1, 3), 5: (1, 2, 4)}
        for i in range(2, len(mobs)):
            e, strip, n = mobs[i]
            boxes = [SurroundingRectangle(mobs[j][1], buff=0.05).set_stroke(FG, 1.5) for j in src[i]]
            self.play(*(ShowCreationThenFadeOut(b) for b in boxes), run_time=0.9)
            self.play(Write(e), FadeIn(strip, shift=0.1 * DOWN), FadeIn(n), run_time=1.6)
            self.wait(1.4)

        real = hud_math(f"real values: layer {l + 1}, step $t = {k}$ of shot \\#{RS['pool_shot']}\\\\"
                        r"candidate recovered from $h_t$, $z_t$, $h_{t-1}$ (hollow where $1 - z_t < 0.02$)",
                        SMALL_SIZE, MUTED).to_corner(DL)
        params = self.param_lines().to_corner(DR)
        self.play(FadeIn(real), FadeIn(params), run_time=0.8)
        self.wait(4)

    def key(self, cfn, lo, hi, name):
        bar = VGroup(*(Square(0.1).set_stroke(width=0).set_fill(cfn(v), 1)
                       for v in np.linspace(lo, hi, 21))).arrange(RIGHT, buff=0)
        lbl = VGroup(caption(name, SMALL_SIZE, MUTED), Tex(str(lo), font_size=22), bar,
                     Tex(f"{hi:+d}" if lo < 0 else str(hi), font_size=22)).arrange(RIGHT, buff=0.1)
        return lbl.fix_in_frame()

    def param_lines(self):
        lines = []
        for run in ("f2280", "f3280"):
            cfg = load_model_cfg(run)
            if cfg is None:
                lines.append(f"{run}: parameter counts pending (model config)")
                continue
            grus = [g for g in cfg["layers"] if g["class"] == "GRU"]
            head = next(l for l in cfg["layers"] if l["class"] == "Dense")
            for g in grus:
                assert g["params"] == gru_params(g["input_shape"][-1], g["units"]), g["name"]
            per = " + ".join(f"{g['params']:,}" for g in grus)
            lines.append(f"{run}: {per} + head {head['params']:,} = {cfg['total_params']:,}")
        txt = VGroup(hud_math(r"parameters per layer: $3\,(u\,(n_\mathrm{in} + u) + u)$", SMALL_SIZE, FG),
                     *(caption(s, SMALL_SIZE, MUTED) for s in lines)).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        return txt.fix_in_frame()


class RealShotLook(Scene):
    """Still of RealShot's setup at t = 2, in one lattice look, for choosing the look."""
    LOOK = "A"

    def construct(self):
        self.add(vignette())
        title = hud_text("One real shot, behind the scenes", TITLE_SIZE).to_corner(UL)
        picked = hud_text("selected as a shot where MWPM fails", CAPTION_SIZE, MUTED)
        picked.next_to(title, DOWN, aligned_edge=LEFT)
        tag = hud_text(f"shot #{RS['pool_shot']} · {RS['block']} block (not the held-out test set) · "
                       f"{RUN_LABEL}, epoch {RS_META['best']['best_epoch']}", SMALL_SIZE, MUTED).to_corner(DR)
        lat = SurfaceCodeLattice(VIZ, height=LAT_H, look=self.LOOK).shift(DOWN * 0.3)
        counter = VGroup(Tex("t =", font_size=40), Integer(2, font_size=40)).arrange(RIGHT, buff=0.15)
        counter.fix_in_frame().next_to(lat, RIGHT, buff=0.8).align_to(lat, UP)
        label = caption(f"look {self.LOOK}", TITLE_SIZE, FG).to_corner(UR)
        self.add(lat, lat.event_glows(rs_events(2), glow=True), title, picked, tag, counter, label)


class RealShotLookB(RealShotLook):
    LOOK = "B"


class RealShotLookC(RealShotLook):
    LOOK = "C"
