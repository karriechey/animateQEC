# animateQEC

3b1b-style animations of quantum error correction, from any Stim circuit.

## Install

```
pip install -e .
```

Requires Python 3.10+ (3.11 or 3.12 avoids the `audioop` issue; on 3.13 `audioop-lts` is installed automatically). `setuptools<81` is pinned because ManimGL still imports `pkg_resources`.

System dependencies:

- FFmpeg
- Pango (`brew install pango pkg-config` / `apt install libpango1.0-dev`)
- LaTeX with `dvisvgm` (macOS: `brew install --cask mactex-no-gui`). `custom_config.yml` uses the `basic` TeX template, so a small TeX install is enough.
- CMU Serif font (Computer Modern Unicode, SIL Open Font License), so captions match the LaTeX math. Without it, text falls back to the system serif font.
  - macOS with MacTeX: `cp "$(kpsewhich -var-value TEXMFDIST)"/fonts/opentype/public/cm-unicode/*.otf ~/Library/Fonts/`
  - Debian/Ubuntu: `apt install fonts-cmu`

Run scenes from the repo root so `custom_config.yml` is picked up:

```
manimgl examples/gru-decoder/scenes.py SyndromeHistory -w -l
```
