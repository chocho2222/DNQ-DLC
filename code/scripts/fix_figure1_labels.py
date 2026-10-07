"""Repair four label errors in the Fig. 1 schematic (figures/lct_9.16.jpg).

The schematic is a raster export with no vector source, so the corrections are
made in place: the affected glyphs are masked out, the hole is filled from the
nearest background pixels (which keeps the hard edges of the track graphics),
and the corrected string is re-drawn with a Times-metric font at the size and
baseline measured from the surrounding text.

Corrections
-----------
Sourrounding vehicles  ->  Surrounding vehicles
Self encoder (middle)  ->  Relation encoder
Self encoder (right)   ->  Action encoder
Actions fro other cars ->  Actions from other cars
soft geomrtry          ->  soft geometry
relation vector        ->  the symbols of Eq. (2) in the text
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be set first)
import matplotlib.patheffects as path_effects  # noqa: E402

FONT = "/usr/share/fonts/opentype/urw-base35/NimbusRoman-Regular.otf"
INK = (26, 30, 92)


def _load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB")).astype(np.int16)


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size)


def _text_size(text: str, size: int) -> tuple[int, int]:
    img = Image.new("L", (3000, 400), 0)
    ImageDraw.Draw(img).text((40, 40), text, font=_font(size), fill=255, anchor="ls")
    ys, xs = np.nonzero(np.asarray(img) > 60)
    return int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def _paint(arr: np.ndarray, box, colour) -> None:
    x0, y0, x1, y1 = box
    arr[y0:y1, x0:x1] = colour


def _inpaint(arr: np.ndarray, box, mask_fn) -> None:
    """Replace masked pixels with the colour of the nearest unmasked pixel."""
    x0, y0, x1, y1 = box
    sub = arr[y0:y1, x0:x1]
    mask = mask_fn(sub)
    mask = ndimage.binary_dilation(mask, iterations=2)
    if not mask.any():
        return
    _, indices = ndimage.distance_transform_edt(mask, return_indices=True)
    arr[y0:y1, x0:x1] = sub[indices[0], indices[1]]


def _inpaint_columns(arr: np.ndarray, box, mask_fn) -> None:
    """Column-wise inpainting, used where text sits on a horizontal edge.

    Filling each masked pixel from the nearest unmasked pixel of the same
    column keeps the straight edge of the track graphic underneath instead of
    regrowing it from the diagonal.
    """
    x0, y0, x1, y1 = box
    sub = arr[y0:y1, x0:x1]
    mask = ndimage.binary_dilation(mask_fn(sub), iterations=3)
    height, width = mask.shape[:2]
    rows = np.arange(height)[:, None]
    filled = sub.copy()
    spread = sub.max(axis=2) - sub.min(axis=2)
    clean = spread <= 14  # white paper and the neutral grey track graphic
    for x in range(width):
        column = mask[:, x]
        if not column.any():
            continue
        source = np.where(~column & clean[:, x])[0]
        if source.size == 0:
            source = np.where(~column)[0]
        if source.size == 0:
            continue
        target = np.where(column)[0]
        nearest = source[np.argmin(np.abs(source[None, :] - target[:, None]), axis=1)]
        filled[target, x] = sub[nearest, x]
    arr[y0:y1, x0:x1] = filled


def _draw(arr: np.ndarray, text: str, size: int, *, centre_x=None, left_x=None,
          baseline_y: int) -> None:
    if left_x is not None:
        origin_x, anchor = int(round(left_x)), "ls"
    else:
        origin_x, anchor = int(round(centre_x)), "ms"
    img = Image.fromarray(arr.astype(np.uint8))
    ImageDraw.Draw(img).text((origin_x, int(baseline_y)), text, font=_font(size),
                             fill=INK, anchor=anchor)
    arr[:, :] = np.asarray(img).astype(np.int16)


def _navy(sub: np.ndarray) -> np.ndarray:
    r, g, b = sub[:, :, 0], sub[:, :, 1], sub[:, :, 2]
    return (r < 120) & (g < 120) & (b < 190)


def _math_ink(tex: str, fontsize: float) -> np.ndarray:
    """Render a mathtext string to an RGBA array with the manuscript ink colour."""
    ink = [c / 255 for c in INK]
    with plt.rc_context({"mathtext.fontset": "stix", "font.family": "STIXGeneral"}):
        fig = plt.figure(figsize=(14, 2.4), dpi=100)
        fig.patch.set_alpha(0)
        # A hairline stroke matches the weight of the surrounding raster text.
        fig.text(0.01, 0.3, tex, fontsize=fontsize, color=ink,
                 path_effects=[path_effects.withStroke(linewidth=0.7, foreground=ink)])
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba()).copy()
        plt.close(fig)
    ys, xs = np.nonzero(buf[:, :, 3] > 40)
    return buf[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _paper(arr: np.ndarray, source: np.ndarray, *, bottom: int, left: int) -> None:
    """Paste an RGBA render so that its ink box sits at (left, bottom)."""
    h, w = source.shape[:2]
    y0, x0 = bottom - h + 1, left
    rgb = source[:, :, :3].astype(np.int16)
    alpha = source[:, :, 3:4].astype(np.float64) / 255.0
    region = arr[y0:y0 + h, x0:x0 + w].astype(np.float64)
    arr[y0:y0 + h, x0:x0 + w] = np.rint(
        region * (1 - alpha) + rgb * alpha).astype(np.int16)


def repair(src: Path, dst: Path) -> None:
    arr = _load(src)

    # 1. "Sourrounding vehicles" -> "Surrounding vehicles".
    #    The lower half of the label sits on a light-grey track graphic, so the
    #    clean area is filled flat and the descender is inpainted.
    _paint(arr, (94, 1146, 652, 1201), (255, 255, 255))
    _inpaint_columns(arr, (94, 1195, 652, 1216), _navy)
    _draw(arr, "Surrounding vehicles", 62, centre_x=372, baseline_y=1196)

    # 2. middle encoder: "Self" -> "Relation"
    _paint(arr, (2140, 658, 2468, 744), (255, 255, 255))
    _draw(arr, "Relation", 62, centre_x=2309, baseline_y=716)

    # 3. right encoder: "Self" -> "Action"
    _paint(arr, (2565, 658, 2892, 744), (255, 255, 255))
    _draw(arr, "Action", 62, centre_x=2729, baseline_y=716)

    # 4. "Actions fro other cars" -> "Actions from other cars"
    _paint(arr, (3990, 1152, 4302, 1218), (255, 255, 255))
    _draw(arr, "Actions from", 53, centre_x=4145, baseline_y=1203)

    # 5. "soft geomrtry" -> "soft geometry"
    _paint(arr, (4070, 1866, 4270, 1915), (252, 227, 232))
    border = np.median(arr[1916:1920, 3900:4050].reshape(-1, 3), axis=0)
    _paint(arr, (4070, 1916, 4270, 1920), tuple(int(v) for v in border))
    _draw(arr, "geometry", 53, left_x=4076, baseline_y=1906)

    # 6. the relation vector is re-typeset so that it reuses the symbols of
    #    Eq. (2) instead of the s/l/s/t naming of an earlier draft.
    fontsize = 46.07
    _paint(arr, (1098, 766, 1602, 852), (255, 255, 255))
    _paint(arr, (1098, 858, 1602, 942), (255, 255, 255))
    _paper(arr, _math_ink(r"$(\Delta f_b,\Delta l_b,\Delta v_x,\Delta v_y,$",
                          fontsize), bottom=841, left=1106)
    _paper(arr, _math_ink(r"$d,\sin\Delta\psi,\cos\Delta\psi)$", fontsize),
           bottom=931, left=1106)

    Image.fromarray(arr.astype(np.uint8)).save(dst, quality=95, subsampling=0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--dst", type=Path, required=True)
    parser.add_argument("--backup", type=Path, default=None)
    args = parser.parse_args()
    if args.backup is not None and not args.backup.exists():
        shutil.copy2(args.src, args.backup)
    repair(args.src, args.dst)
    print(f"wrote {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
