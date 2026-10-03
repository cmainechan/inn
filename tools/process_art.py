#!/usr/bin/env python3
"""Turn the generator's raw PNGs into the yard's web art.

Reads yard/raw/ and writes:
  cats/<cat>/<pose>.webp         poses: sit, sleep, lie
  cats/<cat>/<pose>-<n>.webp     optional extra frames, e.g. sleep-2.png -> sleep-2.webp
  objects/<item>.webp
  objects/<item>-front.webp      items listed in FRONT_WALLS
  combos/<cat>/<item>.webp       one image per cat on one object (from raw/combos/)
  scene/<name>.webp              backgrounds (from raw/scene/)

Raw names:
  raw/<cat>-<pose>[-<n>].png     e.g. tapuz-sit.png, tapuz-sleep-2.png
  raw/<item>.png                 e.g. box.png

Usage (from anywhere):
  python3 yard/tools/process_art.py [--sheet PATH]

Needs Pillow and numpy. Every output is W x H (480 x 400), the same aspect
as the 120:100 spot box in index.html, so one set of percentage anchors works
for cats and items alike.
"""
import argparse
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
YARD = TOOLS.parent
RAW, CATS_OUT, OBJ_OUT = YARD / 'raw', YARD / 'cats', YARD / 'objects'
SCENE_OUT = YARD / 'scene'
COMBO_OUT = YARD / 'combos'
SCENE_SIZE = (1280, 880)   # 16:11, the yard's shape
SCENE_QUALITY = 88

W, H = 480, 400
BASELINE_PAD = 12     # px between the lowest cat/item pixel and the canvas bottom
SIT_HEIGHT = 250      # each cat's sitting pose is scaled to this content height;
                      # the same factor is used for that cat's other poses
REF_CAT = 'tapuz'     # items use the same scale as this cat's sitting pose, so sizes carry over
TRIM_ALPHA = 0.1      # alpha below this is ignored when finding the content box
WEBP_QUALITY = 90
GRASS = np.array([0x9D, 0xCC, 0x6E], np.float32)

# Front walls, as polygons in canvas percent (x, y from top-left). The wall is
# the part a cat sits behind (box front, basket rim). It becomes the object's
# front layer; the back layer is the object with the wall cut away.
# PLACEHOLDER coordinates: tune by eye once the box and basket art exists.
FRONT_WALLS = {
    'box':    [(15, 60), (85, 60), (85, 98), (15, 98)],
    'basket': [(15, 55), (85, 55), (85, 98), (15, 98)],
}

POSE_RE = re.compile(r'^(?P<cat>[a-z]+)-(?P<pose>sit|sleep|lie)(?:-(?P<n>\d+))?$')


# ---------- background removal ----------

def load(path):
    return np.asarray(Image.open(path).convert('RGB'), dtype=np.float32)


def border_colour(rgb, n=8):
    ring = np.concatenate([rgb[:n].reshape(-1, 3), rgb[-n:].reshape(-1, 3),
                           rgb[:, :n].reshape(-1, 3), rgb[:, -n:].reshape(-1, 3)])
    return np.median(ring, axis=0)


def chroma(c):
    """max - min per pixel (0..255). Works on a single colour too."""
    return c.max(axis=-1) - c.min(axis=-1)


def edge_connected(mask):
    """The pixels of `mask` that reach the image border through other mask pixels."""
    reach = np.zeros_like(mask)
    reach[0], reach[-1] = mask[0], mask[-1]
    reach[:, 0], reach[:, -1] = mask[:, 0], mask[:, -1]
    while True:
        grow = reach.copy()
        grow[1:] |= reach[:-1]
        grow[:-1] |= reach[1:]
        grow[:, 1:] |= reach[:, :-1]
        grow[:, :-1] |= reach[:, 1:]
        grow &= mask
        if np.array_equal(grow, reach):
            return reach
        reach = grow


def cut_out(rgb):
    """Return (rgba float 0..255 / 0..1, background colour, was_green)."""
    bg = border_colour(rgb)
    dist = np.linalg.norm(rgb - bg, axis=-1)
    # Only pixels MORE saturated than the backdrop count as colourful subject.
    # Measuring any difference fails on a saturated green backdrop, where a
    # slightly duller green reads as subject. On gray this is the plain test.
    dsat = np.maximum(chroma(rgb) - chroma(bg), 0)
    score = np.maximum(dist, 1.6 * dsat)
    alpha = np.clip((score - 10) / 28, 0, 1)

    loose = alpha < 0.5
    outside = edge_connected(loose)                       # backdrop touching the edge
    alpha = np.where(outside, 0.0, alpha)
    alpha = np.where(loose & ~outside, 1.0, alpha)        # holes inside the subject stay opaque
    alpha = np.where(alpha < 0.05, 0.0, alpha)

    # De-fringe: un-mix the backdrop from partly transparent edge pixels.
    edge = (alpha > 0) & (alpha < 0.95)
    a = alpha[..., None]
    unmixed = (rgb - bg * (1 - a)) / np.maximum(a, 0.05)
    out = np.clip(np.where(edge[..., None], unmixed, rgb), 0, 255)

    was_green = bg[1] - max(bg[0], bg[2]) > 40
    if was_green:
        # Green spill survives un-mixing; pull green down to the red/blue level on edges.
        rb = np.maximum(out[..., 0], out[..., 2])
        out[..., 1] = np.where(edge, np.minimum(out[..., 1], rb + 6), out[..., 1])

    return np.dstack([out, alpha]), bg, was_green


def trim(rgba):
    ys, xs = np.where(rgba[..., 3] > TRIM_ALPHA)
    return rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


# ---------- scaling and placement ----------

def scale_img(rgba, s):
    """Resize with premultiplied alpha, so edges don't darken or pick up colour."""
    h, w = rgba.shape[:2]
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    a = rgba[..., 3:4]
    prem = Image.fromarray(np.clip(rgba[..., :3] * a, 0, 255).astype(np.uint8))
    prem = np.asarray(prem.resize((nw, nh), Image.Resampling.LANCZOS), np.float32)
    alpha = Image.fromarray(np.clip(rgba[..., 3] * 255, 0, 255).astype(np.uint8))
    alpha = np.asarray(alpha.resize((nw, nh), Image.Resampling.LANCZOS), np.float32)[..., None] / 255
    rgb = np.where(alpha > 0, prem / np.maximum(alpha, 1e-3), 0)
    return np.dstack([np.clip(rgb, 0, 255), alpha])


def compose(rgba, s, name):
    """Scale, then stand the content on the shared baseline, centred horizontally."""
    im = scale_img(rgba, s)
    h, w = im.shape[:2]
    x0, y0 = round(W / 2 - w / 2), H - BASELINE_PAD - h
    if x0 < 0 or y0 < 0 or x0 + w > W:
        print(f'  WARNING {name}: content {w}x{h} at x={x0}, y={y0} does not fit the {W}x{H} canvas; it will be cropped')
    canvas = np.zeros((H, W, 4), np.float32)
    dx0, dy0 = max(0, x0), max(0, y0)
    dx1, dy1 = min(W, x0 + w), min(H, y0 + h)
    canvas[dy0:dy1, dx0:dx1] = im[dy0 - y0:dy1 - y0, dx0 - x0:dx1 - x0]
    return canvas


def save_webp(canvas, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba = np.dstack([canvas[..., :3], canvas[..., 3:] * 255])
    Image.fromarray(np.clip(np.round(rgba), 0, 255).astype(np.uint8)).save(
        path, 'WEBP', quality=WEBP_QUALITY, method=6)


def wall_mask(points):
    S = 4  # supersample for smooth polygon edges
    m = Image.new('L', (W * S, H * S), 0)
    ImageDraw.Draw(m).polygon([(x / 100 * W * S, y / 100 * H * S) for x, y in points], fill=255)
    return np.asarray(m.resize((W, H), Image.Resampling.BOX), np.float32)[..., None] / 255


def over_grass(canvas):
    a = canvas[..., 3:]
    return canvas[..., :3] * a + GRASS * (1 - a)


# ---------- the two kinds of art ----------

def process_cat(cat, frames, log):
    """frames: {(pose, n): raw path}. Every frame of one cat shares one scale factor.
    Returns [(label, raw path, canvas)] for the contact sheet."""
    if ('sit', 1) not in frames:
        log(f'  SKIP {cat}: no sit pose (needed for the cat\'s scale)')
        return []
    cut = {}
    for key, path in sorted(frames.items()):
        rgba, bg, green = cut_out(load(path))
        cut[key] = trim(rgba)
        log(f'  {path.name}: backdrop {bg.round().astype(int).tolist()}{" (green spill fix)" if green else ""}, '
            f'content {cut[key].shape[1]}x{cut[key].shape[0]}')
    s = SIT_HEIGHT / cut[('sit', 1)].shape[0]
    log(f'  {cat}: scale {s:.4f} (sit height {cut[("sit", 1)].shape[0]} px -> {SIT_HEIGHT} px)')
    rows = []
    for key in sorted(frames):
        pose, n = key
        name = pose if n == 1 else f'{pose}-{n}'
        canvas = compose(cut[key], s, f'{cat}/{name}')
        save_webp(canvas, CATS_OUT / cat / f'{name}.webp')
        rows.append((f'{cat} {name}', frames[key], canvas))
    return rows


def process_item(name, path, scale, log):
    """scale is shared by every item, so an object drawn at the reference cat's size
    comes out at the reference cat's size in the yard."""
    rgba, bg, green = cut_out(load(path))
    rgba = trim(rgba)
    h, w = rgba.shape[:2]
    log(f'  {path.name}: backdrop {bg.round().astype(int).tolist()}, content {w}x{h}, '
        f'scale {scale:.4f} -> {round(h * scale)}x{round(w * scale)} px')
    canvas = compose(rgba, scale, name)
    outputs = [OBJ_OUT / f'{name}.webp']
    if name not in FRONT_WALLS:
        save_webp(canvas, outputs[0])
        return outputs, canvas
    wall = wall_mask(FRONT_WALLS[name])
    back, front = canvas.copy(), canvas.copy()
    back[..., 3:] *= 1 - wall      # back: the object without the wall
    front[..., 3:] *= wall         # front: only the wall
    save_webp(back, OBJ_OUT / f'{name}.webp')
    save_webp(front, OBJ_OUT / f'{name}-front.webp')
    outputs.append(OBJ_OUT / f'{name}-front.webp')
    return outputs, canvas


# ---------- contact sheet ----------

def contact_sheet(rows, path):
    """rows: [(label, raw path, composed canvas)]. Each row shows the raw image
    beside the result on grass, with the baseline marked."""
    cell_w, cell_h = W // 2, H // 2
    pad, label_h = 12, 18
    sheet = Image.new('RGB', (2 * cell_w + 3 * pad, len(rows) * (cell_h + label_h + pad) + pad), (250, 249, 244))
    draw = ImageDraw.Draw(sheet)
    for i, (label, raw_path, canvas) in enumerate(rows):
        y = pad + i * (cell_h + label_h + pad)
        draw.text((pad, y), label, fill=(40, 40, 40))
        y += label_h
        raw = Image.open(raw_path).convert('RGB').resize((cell_h, cell_h), Image.Resampling.LANCZOS)
        sheet.paste(raw, (pad + (cell_w - cell_h) // 2, y))   # the raw is square, so centre it
        grass = over_grass(canvas)
        small = Image.fromarray(np.clip(np.round(grass), 0, 255).astype(np.uint8)).resize(
            (cell_w, cell_h), Image.Resampling.LANCZOS)
        sheet.paste(small, (2 * pad + cell_w, y))
        base_y = y + round((H - BASELINE_PAD) / 2)
        draw.line([(2 * pad + cell_w, base_y), (2 * pad + 2 * cell_w, base_y)], fill=(200, 40, 40), width=1)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sheet', default=str(TOOLS / 'contact-sheet.png'), help='where to write the contact sheet')
    args = ap.parse_args()

    cat_frames = defaultdict(dict)
    items = {}
    for p in sorted(RAW.glob('*.png')):
        m = POSE_RE.match(p.stem)
        if m:
            cat_frames[m['cat']][(m['pose'], int(m['n'] or 1))] = p
        else:
            items[p.stem] = p

    log = print
    sheet_rows = []
    for cat in sorted(cat_frames):
        log(f'cat {cat}')
        sheet_rows.extend(process_cat(cat, cat_frames[cat], log))

    combos = sorted((RAW / 'combos').glob('*.png'))
    if items or combos:
        ref = cat_frames.get(REF_CAT, {}).get(('sit', 1))
        if ref is None:
            raise SystemExit(f'items need {REF_CAT} sit in raw/ to set the shared scale')
        ref_h = trim(cut_out(load(ref))[0]).shape[0]
        item_scale = SIT_HEIGHT / ref_h
        log(f'shared item scale {item_scale:.4f} (from {REF_CAT} sit: {ref_h} px -> {SIT_HEIGHT} px)')
        for name in sorted(items):
            log(f'item {name}')
            _, canvas = process_item(name, items[name], item_scale, log)
            sheet_rows.append((name, items[name], canvas))

    for path in combos:
        # Combos are one image per cat and object, already with the cat in place.
        # Same shared scale, so the cat's size matches the rest of the set.
        cat, item = path.stem.split('-', 1)
        log(f'combo {cat} + {item}')
        rgba, bg, green = cut_out(load(path))
        rgba = trim(rgba)
        h, w = rgba.shape[:2]
        log(f'  {path.name}: backdrop {bg.round().astype(int).tolist()}, content {w}x{h}, '
            f'scale {item_scale:.4f} -> {round(h * item_scale)}x{round(w * item_scale)} px')
        canvas = compose(rgba, item_scale, f'{cat}+{item}')
        save_webp(canvas, COMBO_OUT / cat / f'{item}.webp')
        sheet_rows.append((f'{cat} + {item}', path, canvas))

    for path in sorted((RAW / 'scene').glob('*.png')):
        # Scenes are full-bleed backgrounds: resize only, no background removal.
        log(f'scene {path.name}')
        img = Image.open(path).convert('RGB').resize(SCENE_SIZE, Image.Resampling.LANCZOS)
        out = SCENE_OUT / f'{path.stem}.webp'
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, 'WEBP', quality=SCENE_QUALITY, method=6)
        log(f'  -> {out.relative_to(YARD)} {SCENE_SIZE[0]}x{SCENE_SIZE[1]}')

    if sheet_rows:
        contact_sheet(sheet_rows, Path(args.sheet))
        log(f'contact sheet: {args.sheet}')


if __name__ == '__main__':
    main()
