"""Write the vector content of a still scene to SVG (ManimGL renders only raster)."""
import numpy as np
from manimlib import FRAME_HEIGHT, FRAME_WIDTH
from manimlib.utils.color import color_to_hex

# ManimGL stroke widths are in units of 1/100 of a scene unit at the default frame
STROKE_SCALE = 0.01


def _path_d(vm, sx, sy):
    parts = []
    for sub in vm.get_subpaths():
        if len(sub) < 3:
            continue
        pts = [(sx(p[0]), sy(p[1])) for p in sub]
        d = [f"M{pts[0][0]:.2f},{pts[0][1]:.2f}"]
        for k in range(1, len(pts) - 1, 2):
            (hx, hy), (ax, ay) = pts[k], pts[k + 1]
            d.append(f"Q{hx:.2f},{hy:.2f} {ax:.2f},{ay:.2f}")
        if np.allclose(sub[0], sub[-1]):
            d.append("Z")
        parts.append(" ".join(d))
    return " ".join(parts)


def to_svg(mobjects, path, width=1920, height=1080, background=None):
    """Every VMobject with points, in drawing order, as one <path> each."""
    k = width / FRAME_WIDTH
    sx = lambda x: (x + FRAME_WIDTH / 2) * k
    sy = lambda y: (FRAME_HEIGHT / 2 - y) * k
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}">']
    if background:
        out.append(f'<rect width="100%" height="100%" fill="{background}"/>')
    for mob in mobjects:
        for vm in mob.family_members_with_points():
            if not hasattr(vm, "get_subpaths"):
                continue
            d = _path_d(vm, sx, sy)
            if not d:
                continue
            fo, so = vm.get_fill_opacity(), vm.get_stroke_opacity()
            sw = vm.get_stroke_width() * STROKE_SCALE * k
            fill = f'fill="{color_to_hex(vm.get_fill_color())}" fill-opacity="{fo:.3f}"' if fo > 0 else 'fill="none"'
            stroke = (f'stroke="{color_to_hex(vm.get_stroke_color())}" stroke-opacity="{so:.3f}" '
                      f'stroke-width="{sw:.2f}" stroke-linecap="round" stroke-linejoin="round"'
                      if so > 0 and sw > 0 else "")
            out.append(f'<path d="{d}" {fill} {stroke} fill-rule="evenodd"/>')
    out.append("</svg>")
    with open(path, "w") as f:
        f.write("\n".join(out))
