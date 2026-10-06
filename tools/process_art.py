#!/usr/bin/env python3
"""Turn the generator's raw PNGs into the yard's web art.

Reads inn/raw/ and writes:
  cats/<cat>/<pose>.webp         poses: sit, sleep, lie, head (head: peeking over an edge)
  cats/<cat>/<pose>-<n>.webp     optional extra frames, e.g. sleep-2.png -> sleep-2.webp
  objects/<item>.webp
  objects/<item>-front.webp      items listed in FRONT_WALLS
  combos/<cat>/<item>.webp       one image per cat on one object (from raw/combos/)
  scene/<name>.webp              backgrounds (from raw/scene/), 16:11
  scene/room-<id>.webp           room pictures (from raw/scene/room-<id>.png), 9:16

Raw names:
  raw/<cat>-<pose>[-<n>].png     e.g. tapuz-sit.png, tapuz-sleep-2.png
  raw/<item>.png                 e.g. box.png
  raw/scene/room-<id>.png        e.g. room-zashiki.png (see ROOM_IDS in index.html)

Usage (from anywhere):
  python3 inn/tools/process_art.py [--sheet PATH]

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
ROOM_SIZE = (1080, 1920)   # 9:16 portrait, one room of the ryokan (the rooms game in index.html)
ROOM_QUALITY = 88
ROOM_PREFIX = 'room-'      # raw/scene/room-<id>.png -> scene/room-<id>.webp
PANO_NAME = 'ryokan-pano'  # raw/scene/ryokan-pano.png: all four rooms in one picture, 9:4, kept at its own size
PANO_QUALITY = 88

W, H = 480, 400
BASELINE_PAD = 12     # px between the lowest cat/item pixel and the canvas bottom
SIT_HEIGHT = 250      # each cat's sitting pose is scaled to this content height;
                      # the same factor is used for that cat's other poses
CAT_SIZE = 0.85       # cats in the layers are drawn at this fraction of SIT_HEIGHT. Measured
                      # against the Tapuz combos (the reference): their cat is about 0.85 of
                      # the layer's sitting height, while the objects match the combos at 1.0
OBJECT_SIZE = {'ball': 0.8, 'yarn': 0.8, 'takoyaki': 0.7, 'onigiri': 1.2, 'taiyaki': 1.05, 'taiyaki-xl': 1.5}  # extra size factor per object, on top of the shared item scale (cats are unchanged)
SHADOW_CUT = {'mochi': 0, 'taiyaki': 0, 'taiyaki-xl': 0, 'redpanda': 0.8}   # items whose ground shadow is removed, from this fraction of the height down (see drop_shadow)
OBJECT_SHIFT = {'ball': -60, 'yarn': -20, 'takoyaki': -28, 'taiyaki': 12}  # canvas px, sideways. Keeps the ball out of the paw's reach (the cat sits to its right)
REF_CAT = 'tapuz'     # items use the same scale as this cat's sitting pose, so sizes carry over
TRIM_ALPHA = 0.1      # alpha below this is ignored when finding the content box
WEBP_QUALITY = 90
GRASS = np.array([0x9D, 0xCC, 0x6E], np.float32)

# Front walls, as polygons in canvas percent (x, y from top-left). The wall is
# the part a cat sits behind (box front, basket rim). It becomes the object's
# front layer; the back layer is the object with the wall cut away.
# Measured on the Tapuz combos: the box front starts at about y 310 of 400 and the
# basket rim at about y 280; both span x 27-73% (the object's front face).
# Curved front cuts, in RAW pixels (the raw image is 1254 px). For the basket, the cut is the top
# edge of the front rim, where the inside of the basket meets the rope, measured on raw/basket.png:
# it sits at about y 502 at the centre and rises to about y 430 at the handles. Everything below it
# (the rope and the front weave) is the front layer, so a cat inside the basket is hidden from there down.
FRONT_CURVES = {
    # The box's front face has a nearly straight top edge at about y 604 (its rim). A cat inside is
    # hidden below it, so the front layer is everything below that line.
    'box': [(222, 604), (400, 604), (627, 604), (850, 604), (1032, 604)],
    'basket': [(180, 430), (250, 455), (350, 475), (450, 490), (550, 498), (627, 502), (700, 498),
               (800, 490), (900, 478), (1000, 455), (1075, 430)],
}
FRONT_WALLS = {
}

POSE_RE = re.compile(r'^(?P<cat>[a-z]+)-(?P<pose>sit|sleep|lie|head|ride|face|half|soak)(?:-(?P<n>\d+))?$')
# Items where the backdrop seen through gaps (e.g. between a stool's legs) should be transparent too.
CLEAR_HOLES = {'stool'}
# Items made from another item's raw image, at their own size (e.g. the XL taiyaki the cat rides).
ITEM_SOURCE = {'taiyaki-xl': 'taiyaki'}
# Items whose raw file name is not a plain slug (spaces, or a name from the generator), under the name the game uses.
ITEM_RAW_NAME = {'bath-stool': 'Japanese Wooden Bath Stool Illustration'}


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


def cut_out(rgb, clear_holes=False):
    """Return (rgba float 0..255 / 0..1, background colour, was_green).
    clear_holes: make backdrop seen through gaps in the subject transparent too (for items like a stool)."""
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
    alpha = np.where(loose & ~outside, 0.0 if clear_holes else 1.0, alpha)  # holes inside the subject stay opaque unless cleared
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


def cut_head(rgb):
    """Cut-out for head poses. The pale fur at the edge left a grey halo with cut_out's soft
    alpha, because the faint edge pixels un-mix into noise. This uses a sharper alpha ramp and
    un-mixes with a floor, so the edge keeps the cat's own colour. Same return as cut_out."""
    bg = border_colour(rgb)
    dist = np.linalg.norm(rgb - bg, axis=-1)
    dsat = np.maximum(chroma(rgb) - chroma(bg), 0)
    score = np.maximum(dist, 1.6 * dsat)
    alpha = np.clip((score - 30) / 10, 0, 1)
    loose = alpha < 0.5
    outside = edge_connected(loose)
    alpha = np.where(outside, 0.0, alpha)
    alpha = np.where(loose & ~outside, 1.0, alpha)
    edge = (alpha > 0) & (alpha < 0.95)
    a = alpha[..., None]
    unmixed = np.clip((rgb - bg * (1 - a)) / np.maximum(a, 0.5), 0, 255)
    out = np.where(edge[..., None], unmixed, rgb)
    return np.dstack([out, alpha]), bg, False


def grow(mask, r):
    """Grow a boolean mask by r pixels in every direction."""
    m = mask.copy()
    for _ in range(r):
        g = m.copy()
        g[1:] |= m[:-1]
        g[:-1] |= m[1:]
        g[:, 1:] |= m[:, :-1]
        g[:, :-1] |= m[:, 1:]
        m = g
    return m


def drop_shadow(rgba, reach=4, from_frac=0.0):
    """Remove a grey ground shadow. It is low in colour and lies outside the object's coloured
    silhouette, so pixels that are grey and more than `reach` px from any coloured pixel go.
    from_frac limits the cut to rows below that fraction of the height, so pale parts higher
    up (ears, cheeks) are left alone."""
    a = rgba[..., 3]
    sat = chroma(rgba[..., :3])
    near = grow((a > 0.5) & (sat > 20), reach)
    low = (np.arange(a.shape[0]) >= from_frac * a.shape[0])[:, None]
    out = rgba.copy()
    out[..., 3] = np.where(~near & (sat < 12) & low, 0.0, a)
    return out


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


def wall_mask(points_px):
    """Polygon in canvas pixels -> 0..1 mask, supersampled for smooth edges."""
    S = 4
    m = Image.new('L', (W * S, H * S), 0)
    ImageDraw.Draw(m).polygon([(x * S, y * S) for x, y in points_px], fill=255)
    return np.asarray(m.resize((W, H), Image.Resampling.BOX), np.float32)[..., None] / 255


def percent_to_px(points):
    return [(x / 100 * W, y / 100 * H) for x, y in points]


def over_grass(canvas):
    a = canvas[..., 3:]
    return canvas[..., :3] * a + GRASS * (1 - a)


# ---------- the two kinds of art ----------

HEAD_MATCH = {'half', 'head'}   # cat poses whose head is matched to the sitting head (see process_cat)


def head_width(rgba):
    """Width in pixels of the widest row in the top 45% of a trimmed cat: the head."""
    a = rgba[..., 3] > TRIM_ALPHA
    rows = np.where(a.any(axis=1))[0]
    top, bottom = rows.min(), rows.max()
    span = a[top:top + int(0.45 * (bottom - top))]
    widths = [np.ptp(np.where(r)[0]) for r in span if r.any()]
    return max(widths)


def process_cat(cat, frames, log):
    """frames: {(pose, n): raw path}. Every frame of one cat shares one scale factor.
    Returns [(label, raw path, canvas)] for the contact sheet."""
    if ('sit', 1) not in frames:
        log(f'  SKIP {cat}: no sit pose (needed for the cat\'s scale)')
        return []
    cut = {}
    for key, path in sorted(frames.items()):
        cutter = cut_head if key[0] == 'head' else cut_out
        rgba, bg, green = cutter(load(path))
        cut[key] = trim(rgba)
        log(f'  {path.name}: backdrop {bg.round().astype(int).tolist()}{" (green spill fix)" if green else ""}, '
            f'content {cut[key].shape[1]}x{cut[key].shape[0]}')
    s = SIT_HEIGHT * CAT_SIZE / cut[('sit', 1)].shape[0]
    log(f'  {cat}: scale {s:.4f} (sit height {cut[("sit", 1)].shape[0]} px -> {SIT_HEIGHT * CAT_SIZE:.0f} px)')
    sit_head = head_width(cut[('sit', 1)])
    rows = []
    for key in sorted(frames):
        pose, n = key
        name = pose if n == 1 else f'{pose}-{n}'
        scale = s
        if pose in HEAD_MATCH:
            # The art draws this pose's head bigger than the sitting head. Scale it so the head
            # matches the sitting head, so every cat reads at the same size.
            scale = s * sit_head / head_width(cut[key])
            log(f'  {cat} {name}: head matched to sitting head, scale x{sit_head / head_width(cut[key]):.3f}')
        canvas = compose(cut[key], scale, f'{cat}/{name}')
        save_webp(canvas, CATS_OUT / cat / f'{name}.webp')
        rows.append((f'{cat} {name}', frames[key], canvas))
    return rows


def process_item(name, path, scale, log):
    """scale is shared by every item, so an object drawn at the reference cat's size
    comes out at the reference cat's size in the yard."""
    scale = scale * OBJECT_SIZE.get(name, 1.0)
    rgba, bg, green = cut_out(load(path), clear_holes=name in CLEAR_HOLES)
    if name in SHADOW_CUT:
        rgba = drop_shadow(rgba, from_frac=SHADOW_CUT[name])
    ys, xs = np.where(rgba[..., 3] > TRIM_ALPHA)
    x_raw, y_raw = xs.min(), ys.min()          # where the trimmed content starts in the raw image
    rgba = trim(rgba)
    h, w = rgba.shape[:2]
    log(f'  {path.name}: backdrop {bg.round().astype(int).tolist()}, content {w}x{h}, '
        f'scale {scale:.4f} -> {round(h * scale)}x{round(w * scale)} px')
    canvas = compose(rgba, scale, name)
    dx = OBJECT_SHIFT.get(name, 0)
    if dx:
        moved = np.zeros_like(canvas)
        moved[:, max(0, dx):W + min(0, dx)] = canvas[:, max(0, -dx):W - max(0, dx)]
        canvas = moved
    outputs = [OBJ_OUT / f'{name}.webp']
    if name not in FRONT_WALLS and name not in FRONT_CURVES:
        save_webp(canvas, outputs[0])
        return outputs, canvas
    if name in FRONT_CURVES:
        # Raw-pixel points -> canvas pixels, using the same placement compose() gives the content.
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        x0, y0 = round(W / 2 - nw / 2), H - BASELINE_PAD - nh
        sx, sy = nw / w, nh / h
        pts = [(x0 + (x - x_raw) * sx, y0 + (y - y_raw) * sy) for x, y in FRONT_CURVES[name]]
        pts += [(pts[-1][0], H + 20), (pts[0][0], H + 20)]     # close the cut below the canvas
        wall = wall_mask(pts)
    else:
        wall = wall_mask(percent_to_px(FRONT_WALLS[name]))
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
    # yarn2.png is the current yarn (ball with the string toward the cat); yarn.png is kept in raw/ but not used.
    if 'yarn2' in items:
        items['yarn'] = items.pop('yarn2')
    for alias, source in ITEM_SOURCE.items():
        if source in items:
            items[alias] = items[source]
    for alias, raw_name in ITEM_RAW_NAME.items():
        if raw_name in items:
            items[alias] = items.pop(raw_name)

    log = print
    sheet_rows = []
    for cat in sorted(cat_frames):
        log(f'cat {cat}')
        sheet_rows.extend(process_cat(cat, cat_frames[cat], log))

    # Only the reference cat's combos are kept; the layered art covers every other cat.
    combos = sorted(p for p in (RAW / 'combos').glob('*.png') if p.stem.split('-', 1)[0] == REF_CAT)
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
        # Room pictures are 9:16 and get their own size below. The four-room panorama keeps its own size.
        if path.stem.startswith(ROOM_PREFIX):
            continue
        if path.stem == PANO_NAME:
            log(f'panorama {path.name}')
            img = Image.open(path).convert('RGB')
            out = SCENE_OUT / f'{PANO_NAME}.webp'
            img.save(out, 'WEBP', quality=PANO_QUALITY, method=6)
            log(f'  -> {out.relative_to(YARD)} {img.size[0]}x{img.size[1]}')
            continue
        log(f'scene {path.name}')
        img = Image.open(path).convert('RGB').resize(SCENE_SIZE, Image.Resampling.LANCZOS)
        out = SCENE_OUT / f'{path.stem}.webp'
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, 'WEBP', quality=SCENE_QUALITY, method=6)
        log(f'  -> {out.relative_to(YARD)} {SCENE_SIZE[0]}x{SCENE_SIZE[1]}')

    for path in sorted((RAW / 'scene').glob(f'{ROOM_PREFIX}*.png')):
        # Each room is a 9:16 portrait picture. The generator gives 941 x 1672, so 1080 x 1920 is an upscale.
        log(f'room {path.name}')
        img = Image.open(path).convert('RGB').resize(ROOM_SIZE, Image.Resampling.LANCZOS)
        out = SCENE_OUT / f'{path.stem}.webp'
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, 'WEBP', quality=ROOM_QUALITY, method=6)
        log(f'  -> {out.relative_to(YARD)} {ROOM_SIZE[0]}x{ROOM_SIZE[1]}')

    if sheet_rows:
        contact_sheet(sheet_rows, Path(args.sheet))
        log(f'contact sheet: {args.sheet}')


if __name__ == '__main__':
    main()
