"""Palette, fonts and sizes shared by every scene."""

BG = "#0f1419"
FG = "#e6eaf0"
MUTED = "#8793a3"
FAINT = "#2a323d"
L1 = "#4cc4c0"  # teal
L2 = "#f0a54e"  # amber
L3 = "#a991f0"  # purple
LAYER_COLORS = [L1, L2, L3]
Z_CHECK = "#4DA6FF"  # Stim's convention
X_CHECK = "#FF4040"
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
