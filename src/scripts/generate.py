#!/usr/bin/env python3
"""Convert headspin.mov into colored-ASCII animation frames for the hero.

Each frame becomes a grid of monospace glyphs. One hysteretic luminance
quantization per cell picks *both* the glyph and its tint,
so a cell can only change when its level changes -- glyph and color can
never flicker independently.

Output is a compact frames.json the AsciiHead.astro component animates in a
<pre>. Re-run this whenever the source video changes:

    python3 src/scripts/generate.py \
        --input src/assets/headspin.mov \
        --out src/components/hero-ascii/frames.json

Two things matter for smooth playback, both handled by the defaults:

  * --fps must divide the source frame rate evenly;
    otherwise ffmpeg's nearest-frame resampling makes the spin hitch
    periodically.
  * --smooth and --hysteresis damp the glyph churn on anti-aliased edges. The
    source is a flat-shaded cartoon, so almost all frame-to-frame change is
    edge cells crossing a quantization boundary; left undamped it reads as the
    symbols crawling even when the head is barely moving.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

# Dark -> light. Index 0 is background; 1..N are the glyph levels.
RAMP = " .:-=+*#%@"
TINTS = ["#33210f", "#5a4133", "#9c7d6a", "#e3c4b5"]  # hair -> face
SHINE = "w"  # sunglasses shine
BLANK = " "  # background spaces
SEP = "|"    # separator


def ffbin(name: str) -> str:
    return os.environ.get(name.upper(), name)


def probe(path: str) -> tuple[int, int, float]:
    out = (
        subprocess.check_output(
            [
                ffbin("ffprobe"), "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,avg_frame_rate",
                "-of", "csv=p=0:s=x",
                path,
            ]
        )
        .decode()
        .strip()
    )
    w, h, rate = out.split("x")
    num, den = (rate.split("/") + ["1"])[:2]
    return int(w), int(h), int(num) / int(den)


def extract_rgb(path: str, cols: int, rows: int, fps: int) -> bytes:
    """Decode the video to a raw rgb24 stream at the target character grid."""
    with tempfile.NamedTemporaryFile(suffix=".rgb", delete=False) as tmp:
        tmp_path = tmp.name
    subprocess.check_call(
        [
            ffbin("ffmpeg"), "-y", "-loglevel", "error",
            "-i", path,
            "-vf", f"fps={fps},scale={cols}:{rows}:flags=area,format=rgb24",
            "-f", "rawvideo",
            tmp_path,
        ]
    )
    data = open(tmp_path, "rb").read()
    os.unlink(tmp_path)
    return data


def luminance(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=120)
    ap.add_argument("--fps", type=int, default=30, help="must divide the source rate evenly")
    ap.add_argument("--bg", type=int, default=24, help="luminance below this = background")
    ap.add_argument("--shine-lum", type=int, default=185, help="bright + neutral = white shine")
    ap.add_argument("--shine-chroma", type=int, default=35, help="max (maxRGB-minRGB) to be neutral")
    ap.add_argument("--char-aspect", type=float, default=0.6, help="glyph width / height")
    ap.add_argument("--pad", type=int, default=1, help="blank cells kept around the crop")
    ap.add_argument("--skin-lum", type=int, default=110, help="luminance above this = lit skin (chin finder)")
    ap.add_argument("--smooth", type=float, default=0.45,
                    help="per-cell luminance EMA, 0..1; lower = steadier, 0 disables")
    ap.add_argument("--hysteresis", type=float, default=18.0,
                    help="luminance a cell must overshoot a level boundary before it switches")
    ap.add_argument("--ramp", default=RAMP, help="glyphs dark -> light; index 0 is the background")
    ap.add_argument("--loop-passes", type=int, default=3,
                    help="times to run the temporal filters around the clip, keeping only the last. "
                         "The animation loops, so >1 makes the filter state entering frame 0 the same "
                         "state that left the final frame; at 1 the loop point visibly pops")
    ap.add_argument("--coverage", type=float, default=0.0005,
                    help="ignore columns/rows holding less than this share of all ink when sizing the crop")
    args = ap.parse_args()

    src_w, src_h, src_fps = probe(args.input)
    if src_fps and abs(round(src_fps / args.fps) - src_fps / args.fps) > 1e-6:
        divisors = [f for f in range(12, int(src_fps) + 1) if abs(src_fps / f - round(src_fps / f)) < 1e-6]
        print(
            f"warning: --fps {args.fps} does not divide the {src_fps:g}fps source; "
            f"playback will judder. Use one of: {divisors}",
            file=sys.stderr,
        )

    cols = args.cols
    rows = max(1, round(cols * (src_h / src_w) * args.char_aspect))
    data = extract_rgb(args.input, cols, rows, args.fps)
    stride = cols * rows * 3
    n = len(data) // stride
    print(f"{src_w}x{src_h} -> grid {cols}x{rows}, {n} frames @ {args.fps}fps", file=sys.stderr)

    ramp = args.ramp
    nlev = len(ramp) - 1  # non-blank glyph levels
    span = 256 - args.bg
    hyst = args.hysteresis
    a = args.smooth

    if hyst >= span / nlev:
        print(
            f"warning: --hysteresis {hyst:g} is >= the {span / nlev:.1f} luminance width of one "
            f"of the {nlev} levels; cells will stick and the animation will freeze",
            file=sys.stderr,
        )

    def level_of(lum: float) -> int:
        """Un-damped level for a luminance: 0 = background, 1..nlev = glyphs."""
        if lum < args.bg:
            return 0
        return min(nlev, 1 + int((lum - args.bg) * nlev / span))

    def boundary(lv: int) -> float:
        """Luminance at which level `lv` becomes level `lv + 1`."""
        return args.bg + lv * span / nlev if lv else args.bg

    def sticky(lum: float, prev: int) -> int:
        """level_of(), but a cell holds its previous level until the luminance
        clears the boundary it would cross by `hyst`. Cells parked on a boundary
        (every anti-aliased edge) stop dithering; real motion still passes
        straight through, since it overshoots by far more than the margin."""
        lv = level_of(lum)
        if prev < 0 or lv == prev:
            return lv
        if lv > prev:
            return lv if lum >= boundary(prev) + hyst else prev
        return lv if lum <= boundary(lv) - hyst else prev

    ncell = cols * rows
    lums = []
    chromas = []
    for f in range(n):
        base = f * stride
        lum = [0.0] * ncell
        chroma = [0] * ncell
        for i in range(ncell):
            o = base + i * 3
            r, g, b = data[o], data[o + 1], data[o + 2]
            lum[i] = luminance(r, g, b)
            chroma[i] = max(r, g, b) - min(r, g, b)
        lums.append(lum)
        chromas.append(chroma)

    # Pass 1: EMA the luminance down the time axis, then quantize + add hysteresis
    levels: list[list[list[int]]] = []
    shines: list[list[list[bool]]] = []
    chins: list[float] = []
    smoothed: list[float] | None = None
    prev_lv = [-1] * ncell
    prev_shine = [False] * ncell
    for lap in range(max(1, args.loop_passes)):
        keep = lap == max(1, args.loop_passes) - 1
        if keep:
            levels, shines, chins = [], [], []
        for f in range(n):
            lum, chroma = lums[f], chromas[f]
            if a > 0:
                if smoothed is None:
                    smoothed = lum[:]
                else:
                    smoothed = [a * lum[i] + (1 - a) * smoothed[i] for i in range(ncell)]
                v = smoothed
            else:
                v = lum
            lv_frame = []
            sh_frame = []
            lit = []  # (y, x) of lit-skin cells, for the chin finder below
            for y in range(rows):
                lv_row = []
                sh_row = []
                for x in range(cols):
                    i = y * cols + x
                    lv = sticky(v[i], prev_lv[i]) # type: ignore
                    # Shine gets the same margin so lenses can't strobe on the
                    # edge of the threshold.
                    on = args.shine_lum - (hyst if prev_shine[i] else 0)
                    sh = lv > 0 and v[i] >= on and chroma[i] <= args.shine_chroma # type: ignore
                    prev_lv[i], prev_shine[i] = lv, sh
                    lv_row.append(lv)
                    sh_row.append(sh)
                    if lv and v[i] > args.skin_lum: # type: ignore
                        lit.append((y, x))
                lv_frame.append(lv_row)
                sh_frame.append(sh_row)
            if keep:
                levels.append(lv_frame)
                shines.append(sh_frame)
                if lit:
                    bottom = max(y for y, _ in lit)
                    band = [x for y, x in lit if y >= bottom - 2]
                    chins.append((min(band) + max(band)) / 2)

    # Pass 2: crop geometry. Columns/rows holding a negligible share of the ink
    # (a stray cell or two over the whole clip) are excluded so one outlier can't
    # inflate the window.
    col_ink = [0] * cols
    row_ink = [0] * rows
    total = 0
    for lv_frame in levels:
        for y in range(rows):
            for x in range(cols):
                if lv_frame[y][x]:
                    col_ink[x] += 1
                    row_ink[y] += 1
                    total += 1
    floor = total * args.coverage
    xs = [x for x in range(cols) if col_ink[x] > floor]
    ys = [y for y in range(rows) if row_ink[y] > floor]
    x0, x1 = xs[0], xs[-1]
    y0, y1 = ys[0], ys[-1]

    # Horizontal centre is the median of the chin x's, so the head stays centred
    chins.sort()
    cx = chins[len(chins) // 2] if chins else (x0 + x1) / 2

    # Vertical centre stays the ink centroid -- there is no equivalent landmark
    # and the head's vertical extent is already symmetric about it.
    sy = sw = 0.0
    for lv_frame in levels:
        for y in range(rows):
            for x in range(cols):
                if lv_frame[y][x]:
                    sy += y
                    sw += 1
    cy = sy / sw

    # ONE fixed crop window for every frame, sized to hold the head and centered
    # on (chin x, centroid y). A single shared window means the head keeps its
    # natural spin but the grid never shifts under it.
    x0, x1 = max(0, x0 - args.pad), min(cols - 1, x1 + args.pad)
    y0, y1 = max(0, y0 - args.pad), min(rows - 1, y1 + args.pad)
    hx = max(cx - x0, x1 - cx)
    hy = max(cy - y0, y1 - cy)
    wx0, wx1 = round(cx - hx), round(cx + hx)
    wy0, wy1 = round(cy - hy), round(cy + hy)
    cw, ch_ = wx1 - wx0 + 1, wy1 - wy0 + 1
    print(f"chin x {cx:.1f}, centroid y {cy:.1f} -> window {cw}x{ch_}", file=sys.stderr)

    def cell(f: int, x: int, y: int) -> tuple[str, str]:
        """(colour tag, glyph) for one grid cell. See the wire format below."""
        if not (0 <= x < cols and 0 <= y < rows):
            return BLANK, " "
        lv = levels[f][y][x]
        if not lv:
            return BLANK, " "
        if shines[f][y][x]:
            return SHINE, "@"  # solid glyph -> a crisp white highlight
        return str(min(len(TINTS) - 1, (lv - 1) * len(TINTS) // nlev)), ramp[lv]

    # One string
    # per frame, rows joined by "\n"; within a row, colour runs joined by SEP,
    # each run a one-char tag followed by its glyphs. Storing runs as text
    # rather than as [index, chars] pairs halves the file and saves the browser
    # tens of thousands of small array allocations when the bundle loads.
    frames = []
    for f in range(n):
        frame_rows = []
        for y in range(wy0, wy1 + 1):
            runs: list[list[str]] = []
            for x in range(wx0, wx1 + 1):
                ci, ch = cell(f, x, y)
                if runs and runs[-1][0] == ci:
                    runs[-1][1] += ch
                else:
                    runs.append([ci, ch])
            if runs and runs[-1][0] == BLANK:  # trailing blanks are invisible
                runs.pop()
            frame_rows.append(SEP.join(tag + chs for tag, chs in runs))
        frames.append("\n".join(frame_rows))

    out = {"cols": cw, "rows": ch_, "fps": args.fps, "palette": TINTS, "frames": frames}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(f"wrote {args.out} ({os.path.getsize(args.out)} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
