"""Palette, fonts and sizes shared by every scene."""

BG = "#080b10"
FG = "#e6eaf0"
MUTED = "#8793a3"
FAINT = "#2a323d"
L1 = "#4cc4c0"  # teal
L2 = "#f0a54e"  # amber
L3 = "#a991f0"  # purple
LAYER_COLORS = [L1, L2, L3]
Z_CHECK = "#00B4FF"  # Stim's convention: Z blue, X red
X_CHECK = "#FF2E4D"
BASIS_COLOR = {"Z": Z_CHECK, "X": X_CHECK}
EVENT = "#FFE066"  # fired detector
MWPM = "#FF4FD8"  # magenta: used for nothing else, stays visible on X plaquettes
MWPM_WIDTH = 6

# CMU Serif (SIL OFL), the Computer Modern of the LaTeX math; Pango falls back to the system serif
FONT = "CMU Serif, serif"
TITLE_SIZE = 40
CAPTION_SIZE = 26
SMALL_SIZE = 20

# diverging hidden-state colormap, centred at 0 on the background
STATE_NEG = "#6C8EBF"
STATE_POS = "#E8A07A"
# truth classes in state-space plots
FLIP = "#E07A5F"
NO_FLIP = "#81B29A"

# detection events: white-hot core inside a gold glow
EVENT_CORE = "#FFF8E8"
EVENT_GLOW = "#FFC94D"
DATA_DOT = "#DCE3EC"  # soft white

PX = 1 / 1.35  # stroke width per output pixel at 1080p (1 stroke unit = 0.01 scene units)
# lattice looks: plaquette fill opacity and neon edge layers as (pixels, opacity), widest first
LATTICE_LOOK = "A"  # default look for every lattice
LATTICE_LOOKS = {
    # saturated glow layers; the core only slightly toward white
    "A": dict(fill=0.16, neon=[(16, 0.14), (6, 0.42), (2.5, 1.0)], core_white=0.08),
    "B": dict(fill=0.20, neon=[(8, 0.06), (3, 0.2), (1.5, 1.0)]),
    "C": dict(fill=0.0, neon=[(14, 0.08), (6, 0.25), (2, 1.0)]),
}
