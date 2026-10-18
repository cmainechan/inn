#!/usr/bin/env python3
"""Turn the generator's raw PNGs into the yard's web art.

Reads inn/raw/ and writes:
  cats/<cat>/<pose>.webp         poses: sit, sleep, lie, head (head: peeking over an edge),
                                  full (eating at the food spot, see FOOD_CAT_SPOT in index.html),
                                  belly1, belly2 (two belly-up variants)
  cats/<cat>/<pose>-<n>.webp     optional extra frames, e.g. sleep-2.png -> sleep-2.webp
  objects/<item>.webp
  objects/<item>-front.webp      items listed in FRONT_WALLS
  scene/<name>.webp              backgrounds (from raw/scene/), 16:11
  scene/room-<id>.webp           room pictures (from raw/scene/room-<id>.png), 9:16
  polaroids/<dest>-bg.webp       day-trip destination plate (from raw/polaroids/bg-<dest>.png), square
  polaroids/<cat>-selfie<n>.webp day-trip cat cutout, pose <n> (from raw/polaroids/cat-<cat><n>.png),
                                  trimmed, NOT placed on a canvas -- composited over a destination
                                  plate at runtime. A cat can have several poses (n = 1, 2, ...); the
                                  game picks one at random when a trip's photo is taken (see
                                  SELFIE_POSES/randomPose in index.html).
  stamps/<dest>.webp             day-trip stamp badge (from raw/stamps/stamp-<dest>.png), trimmed and
                                  height-normalised like a selfie cutout -- a smaller bonus collectible
                                  alongside the polaroid, one per destination (see STAMP_CHANCE in
                                  index.html), not per cat.

Raw names:
  raw/cats/<cat>-<pose>[-<n>].png   e.g. tapuz-sit.png, tapuz-sleep-2.png
  raw/cats/<cat>-<pose>-notail.png, raw/cats/<cat>-<pose>-tail.png
                                     optional pair, body/tail split so the tail can sway at runtime
                                     (see process_cat_tail and CAT_TAILS in index.html). The notail
                                     art replaces <pose>.png for that cat; -tail.png is saved as its
                                     own cats/<cat>/<pose>-tail.webp, aligned pixel-for-pixel onto it.
  raw/objects/<item>.png            e.g. box.png
  raw/food/<item>.png               consumable food items, e.g. yakitori.png
  raw/scene/room-<id>.png           e.g. room-zashiki.png (see ROOM_IDS in index.html)
  raw/polaroids/bg-<dest>.png       day-trip background plate, e.g. bg-kawaguchiko.png
  raw/polaroids/cat-<cat><n>.png    day-trip cat cutout, pose n (1, 2, ...), e.g. cat-tapuz1.png
  raw/stamps/stamp-<dest>.png       day-trip stamp badge, e.g. stamp-kawaguchiko.png

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
POLA_OUT = YARD / 'polaroids'
STAMP_OUT = YARD / 'stamps'
STAMP_HEIGHT = 400        # px content height a stamp badge is normalised to, well above its ~16px
                            # display size in the book's chip corner (see .stamp-badge in index.html).
POLA_SIZE = (1200, 1200)   # square, like an instant-film photo. The cat cutout is NOT scaled to this --
                            # it's trimmed and height-normalised to SELFIE_HEIGHT, then positioned at
                            # runtime (its own x/y/scale per cat+destination), same idea as FLOATING items.
SELFIE_HEIGHT = 1400       # px. Shared content height every cat-<cat>.png cutout is normalised to,
                            # so one cat reads the same size as another before runtime placement scales it down.
POLA_RE = re.compile(r'^(?P<kind>bg|cat)-(?P<id>[a-z]+)(?P<n>\d+)?$')
SCENE_SIZE = (1280, 880)   # 16:11, the yard's shape
SCENE_QUALITY = 88
ROOM_SIZE = (1080, 1920)   # 9:16 portrait, one room of the ryokan (the rooms game in index.html)
ROOM_QUALITY = 88
ROOM_PREFIX = 'room-'      # raw/scene/room-<id>.png -> scene/room-<id>.webp
PANO_PREFIX = 'ryokan-pano'  # raw/scene/ryokan-pano[-<variant>].png -> scene/ryokan-pano[-<variant>].webp.
                              # All four rooms in one picture, 9:4, kept at its own size. -<variant> is a
                              # seasonal variant, e.g. ryokan-pano-spring.png (see PANO_SEASONS in index.html).
PANO_QUALITY = 88

W, H = 480, 400
BASELINE_PAD = 12     # px between the lowest cat/item pixel and the canvas bottom
SIT_HEIGHT = 250      # each cat's sitting pose is scaled to this content height;
                      # the same factor is used for that cat's other poses
CAT_SIZE = 0.85       # cats in the layers are drawn at this fraction of SIT_HEIGHT. Measured
                      # against the Tapuz combos (the reference): their cat is about 0.85 of
                      # the layer's sitting height, while the objects match the combos at 1.0
OBJECT_SIZE = {'ball': 0.8, 'yarn': 0.8, 'takoyaki': 0.7, 'onigiri': 1.2, 'taiyaki': 1.05, 'taiyaki-xl': 1.5, 'mochi': 1.35, 'sakura-toro': 0.95, 'mochibunny': 0.5}  # extra size factor per object, on top of the shared item scale (cats are unchanged).
# mochi: sized up so its silhouette is convincingly wider than the cat's "head" pose peeking over it
# (it was barely wider than the cat's own ears before -- compare taiyaki, which already reads right).
SHADOW_CUT = {'mochi': 0, 'taiyaki': 0, 'taiyaki-xl': 0, 'redpanda': 0.8}   # items whose ground shadow is removed, from this fraction of the height down (see drop_shadow)
OBJECT_SHIFT = {'ball': -60, 'yarn': -20, 'takoyaki': -28, 'taiyaki': 12, 'temari-ball': (10, 5), 'temari-ball-blue': (10, 5)}  # canvas px: a plain number is sideways only (+right), or (dx, dy) for both (+down). ball/yarn/takoyaki/taiyaki: keeps the toy out of the paw's reach (the cat sits to its right). temari-ball-blue: same shape as temari-ball, same shift
REF_CAT = 'tapuz'     # items use the same scale as this cat's sitting pose, so sizes carry over
BODY_BAND = 0.08      # the bottom 8% of a cat's content is where its body rests (see body_centre_x)
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

POSE_RE = re.compile(r'^(?P<cat>[a-z]+)-(?P<pose>sit|sleep|lie|head|ride|face|half|soak|peer|full|belly1|belly2)(?:-(?P<n>\d+))?$')
# A pose's body/tail split -- see process_cat_tail.
TAIL_RE = re.compile(r'^(?P<cat>[a-z]+)-(?P<pose>[a-z0-9]+)-(?P<part>notail|tail)$')
# A pose's own second pair of paws, drawn to sit in front of a held item -- see process_cat_paws.
PAWS_RE = re.compile(r'^(?P<cat>[a-z]+)-(?P<pose>[a-z0-9]+)-paws$')
# Items where the backdrop seen through gaps (e.g. between a stool's legs) should be transparent too.
CLEAR_HOLES = {'stool', 'mtchirashi', 'fan', 'gym', 'koinobori', 'koinobori-fish'}  # mtchirashi: the gap between the prawn's feelers; fan: the gap between the ribs where they meet the handle; gym: the triangular gaps inside each A-frame leg; koinobori: the gap between the pole and the string loop tied around it (processed from koinobori-stand.png -- see ITEM_RAW_NAME; koinobori-fish: the gap between the two cord struts where they converge to a single point, above the fish's mouth ring)
# Items with a soft, low-saturation contact shadow baked into the raw art right where the subject
# meets the backdrop (e.g. under the gym's feet). It's dark enough that cut_out()'s colour-distance
# test reads it as subject, leaving an opaque grey smudge once composited over a real room floor.
# Before cutting out, any near-greyscale pixel (max-min channel < DESHADOW_CHROMA) is flattened to
# the backdrop colour so the normal background flood-fill removes it like the rest of the backdrop.
DESHADOW = {'gym'}
DESHADOW_CHROMA = 20
# Items where cut_out() picks up a stray, disconnected generator artifact (a faint stray line, a
# speck) nowhere near the actual subject -- keep only the single largest connected blob of content.
MAIN_BLOB = {'koinobori'}
# Items made from another item's raw image, at their own size (e.g. the XL taiyaki the cat rides).
ITEM_SOURCE = {'taiyaki-xl': 'taiyaki'}
# Items whose raw file name is not a plain slug (spaces, or a name from the generator), under the name the game uses.
# koinobori-fish2.png is the current fish art (replaces koinobori-fish.png, kept in raw/objects/ but not used -- same pattern as yarn/yarn2).
ITEM_RAW_NAME = {'bath-stool': 'Japanese Wooden Bath Stool Illustration', 'kazaguruma': 'kazaguruma-stand', 'koinobori': 'koinobori-stand', 'gym': 'gym-stand', 'koinobori-fish': 'koinobori-fish2'}
# Free-floating overlay layers, like a bath's water: cut out and trimmed but NOT baseline-composed
# onto the shared 480x400 canvas, because they're positioned independently at runtime by their own
# x/y/w percent (see e.g. ITEMS.kazaguruma.wheel and ITEMS.koinobori.fish in index.html), not stood
# on the floor like an item. koinobori-fish: the fish sways on its own, separate from the static pole.
# gym-acc1/2/3: the gym's three hanging charms, each swaying independently off the crossbar.
FLOATING = {'kazaguruma-wheel', 'koinobori-fish', 'gym-acc1', 'gym-acc2', 'gym-acc3'}
# Items centred on their full bounding box, not the bottom band (see body_centre_x): a box drawn at
# an angle, like the kaiseki's two offset tiers, has its near-bottom corner off to one side, which
# throws off body-band centring in a way that never happens for a cat or a simple sitting object.
CENTER_BBOX = {'kaiseki'}
CENTER_BBOX_PREFIXES = ('tkt-',)   # every day-trip ticket is a tilted card -- its near-bottom corner
                                    # throws off body-band centring the same way kaiseki's does


# ---------- background removal ----------

def load(path):
    return np.asarray(Image.open(path).convert('RGB'), dtype=np.float32)


def pre_cut_rgba(path):
    """If the raw file already has real alpha transparency (an artist-cut PNG, not just an unused
    opaque alpha channel), return it as rgba (RGB 0..255, alpha 0..1) ready for trim/compose,
    skipping background removal entirely. Otherwise return None, meaning cut_out() should run as
    usual. Detected automatically per file, so no per-item list to maintain."""
    im = Image.open(path)
    if 'A' not in im.getbands():
        return None
    im = im.convert('RGBA')
    arr = np.asarray(im, dtype=np.float32)
    if arr[..., 3].min() > 250:   # fully opaque alpha channel: not actually cut out
        return None
    out = arr.copy()
    out[..., 3] /= 255.0
    return out


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


def largest_component(mask):
    """The single largest 4-connected blob of `mask`, dropping every smaller, disconnected speck
    (see MAIN_BLOB) -- e.g. a stray generator artifact nowhere near the actual subject."""
    remaining = mask.copy()
    best, best_size = np.zeros_like(mask), 0
    while remaining.any():
        ys, xs = np.where(remaining)
        reach = np.zeros_like(mask)
        reach[ys[0], xs[0]] = True
        while True:
            grow = reach.copy()
            grow[1:] |= reach[:-1]
            grow[:-1] |= reach[1:]
            grow[:, 1:] |= reach[:, :-1]
            grow[:, :-1] |= reach[:, 1:]
            grow &= remaining
            if np.array_equal(grow, reach):
                break
            reach = grow
        if reach.sum() > best_size:
            best, best_size = reach, reach.sum()
        remaining &= ~reach
    return best


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


def body_centre_x(rgba):
    """x of the middle of the bottom band of the content: where the body rests on the baseline.
    Using this, not the middle of the whole box, keeps cats with wider paws or tails in the same place."""
    ys, xs = np.where(rgba[..., 3] > TRIM_ALPHA)
    band = ys >= ys.max() - BODY_BAND * rgba.shape[0]
    return xs[band].mean()


def bbox_centre_x(rgba):
    """x of the middle of the full content box, ignoring height. See CENTER_BBOX."""
    xs = np.where(rgba[..., 3] > TRIM_ALPHA)[1]
    return (xs.min() + xs.max()) / 2


def compose(rgba, s, name, center='body'):
    """Scale, then stand the content on the shared baseline, horizontally centred (see `center`)."""
    im = scale_img(rgba, s)
    h, w = im.shape[:2]
    cx = bbox_centre_x(im) if center == 'bbox' else body_centre_x(im)
    x0, y0 = round(W / 2 - cx), H - BASELINE_PAD - h
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
# Poses where the per-cat sit-based scale alone isn't enough: measured across the roster (see the
# contact-sheet audit that found this), 'lie' varies +-23% in both width and height cat to cat, and
# 'belly1' varies +-22% in height -- in each case because the raw art for that pose happens to draw
# the cat filling more or less of its own frame, not because of any real difference in the pipeline's
# per-cat scale. Matches each cat's content on the given dimension to the roster's median for that
# pose, same idea as HEAD_MATCH but cross-cat instead of cross-pose. 'lie' matches width (it's a
# wide, compact pose where width and height move together); 'belly1' matches height (width was
# already tight at +-7% -- the real variance there is how far the paws reach up, i.e. height).
BODY_MATCH = {'lie': 'width', 'belly1': 'height'}


def head_width(rgba):
    """Width in pixels of the widest row in the top 45% of a trimmed cat: the head."""
    a = rgba[..., 3] > TRIM_ALPHA
    rows = np.where(a.any(axis=1))[0]
    top, bottom = rows.min(), rows.max()
    span = a[top:top + int(0.45 * (bottom - top))]
    widths = [np.ptp(np.where(r)[0]) for r in span if r.any()]
    return max(widths)


def prepare_cat(cat, frames, log):
    """frames: {(pose, n): raw path}. Cuts every frame and computes this cat's shared scale from its
    sit pose. Split from compose_cat (below) because BODY_MATCH needs every cat's cut content before
    any cat can be composed -- see main(). Returns (cut, s, sit_head), or None if there's no sit pose."""
    if ('sit', 1) not in frames:
        log(f'  SKIP {cat}: no sit pose (needed for the cat\'s scale)')
        return None
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
    return cut, s, sit_head


def compose_cat(cat, frames, cut, s, sit_head, pose_targets, log, tails=None, paws=None):
    """Compose+save every frame of one cat, using the (cut, s, sit_head) prepare_cat returned.
    pose_targets: {pose: target px} for BODY_MATCH poses (see main()), keyed by the same pose names.
    tails: optional {pose: (notail_path, tail_path)} -- see process_cat_tail. frames[(pose, 1)] is
    expected to already be the notail art for any pose listed here (see main()).
    paws: optional {pose: paws_path} -- see process_cat_paws. Uses frames[(pose, 1)] as the body
    as-is (no swap needed, unlike tails).
    Returns [(label, raw path, canvas)] for the contact sheet."""
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
        elif pose in BODY_MATCH and pose_targets.get(pose):
            dim = 1 if BODY_MATCH[pose] == 'width' else 0
            cur = cut[key].shape[dim] * s
            scale = s * pose_targets[pose] / cur
            log(f'  {cat} {name}: {BODY_MATCH[pose]} matched across the roster, scale x{pose_targets[pose] / cur:.3f}')
        canvas = compose(cut[key], scale, f'{cat}/{name}')
        save_webp(canvas, CATS_OUT / cat / f'{name}.webp')
        rows.append((f'{cat} {name}', frames[key], canvas))
        if tails and pose in tails and n == 1:
            notail_path, tail_path = tails[pose]
            process_cat_tail(cat, name, notail_path, tail_path, scale, log)
        if paws and pose in paws and n == 1:
            process_cat_paws(cat, name, frames[key], paws[pose], scale, log)
    return rows


def body_placement(body_path, scale):
    """The exact placement compose() would give this body art: its scaled size, its canvas position
    (x0, y0), and where its trimmed content starts in the raw image (x_raw, y_raw). Any overlay drawn
    on the SAME raw canvas as this body (a tail, a pair of paws -- anything split out so it can move
    independently at runtime) can be mapped onto the body's own cats/<cat>/<name>.webp pixel-for-pixel
    using this, via align_overlay() below -- see process_cat_tail, process_cat_paws."""
    body_rgba, *_ = cut_out(load(body_path))
    ys, xs = np.where(body_rgba[..., 3] > TRIM_ALPHA)
    x_raw, y_raw = xs.min(), ys.min()
    im_body = scale_img(trim(body_rgba), scale)
    h, w = im_body.shape[:2]
    cx = body_centre_x(im_body)
    x0, y0 = round(W / 2 - cx), H - BASELINE_PAD - h
    return x0, y0, x_raw, y_raw, (xs, ys)


def align_overlay(overlay_path, scale, placement):
    """An overlay sharing a body's raw canvas, placed on the shared 480x400 canvas using the body's
    own placement (see body_placement) -- same scale, offset by how far apart the two were in the raw
    art. Returns (canvas, raw xs/ys of the overlay's own content, placed x0/y0) for callers that also
    need the overlay's own position (see process_cat_paws's attach-point search)."""
    x0, y0, x_raw, y_raw, _ = placement
    ov_rgba, *_ = cut_out(load(overlay_path))
    ys, xs = np.where(ov_rgba[..., 3] > TRIM_ALPHA)
    x_raw_o, y_raw_o = xs.min(), ys.min()
    im_ov = scale_img(trim(ov_rgba), scale)
    h, w = im_ov.shape[:2]
    tx0 = x0 + (x_raw_o - x_raw) * scale
    ty0 = y0 + (y_raw_o - y_raw) * scale

    canvas = np.zeros((H, W, 4), np.float32)
    dx0, dy0 = max(0, round(tx0)), max(0, round(ty0))
    dx1, dy1 = min(W, round(tx0) + w), min(H, round(ty0) + h)
    canvas[dy0:dy1, dx0:dx1] = im_ov[dy0 - round(ty0):dy1 - round(ty0), dx0 - round(tx0):dx1 - round(tx0)]
    return canvas, (xs, ys), (tx0, ty0)


def process_cat_tail(cat, name, notail_path, tail_path, scale, log):
    """A tail drawn apart from its pose's body (see TAIL_RE: <cat>-<pose>-notail.png / -tail.png), so
    it can sway independently at runtime instead of being baked still into the pose art (same idea as
    the koinobori fish or gym charms -- see FLOATING -- but here the "body" half isn't floating, so it
    can't just reuse process_floating)."""
    placement = body_placement(notail_path, scale)
    x0, y0, x_raw, y_raw, (xs, ys) = placement
    canvas, (xs2, ys2), _ = align_overlay(tail_path, scale, placement)

    # Where the tail meets the body: the closest pair of pixels between the two raw cutouts (coarsely
    # subsampled -- only needs to land within a few px). Logged as a ready-to-paste sway transform-
    # origin (see CAT_TAILS in index.html). An earlier version also faded the tail's alpha in near this
    # point to hide the seam a rotation opens -- but the body's own cutout stops exactly at the seam (no
    # overlap to fade into), so that fade just opened a hole straight through to the floor, visible even
    # at rest. Left as a hard edge instead and relying on a small swing (see CSS) to keep it subtle.
    bxs, bys = xs[::7], ys[::7]
    best_d, attach = 1e18, (xs2[0], ys2[0])
    for txp, typ in zip(xs2[::3], ys2[::3]):
        d = (bxs - txp) ** 2 + (bys - typ) ** 2
        i = d.argmin()
        if d[i] < best_d:
            best_d, attach = d[i], (txp, typ)
    attach_x = x0 + (attach[0] - x_raw) * scale
    attach_y = y0 + (attach[1] - y_raw) * scale
    log(f'  {tail_path.name}: sway origin {attach_x / W * 100:.1f}% {attach_y / H * 100:.1f}% (see CAT_TAILS)')

    save_webp(canvas, CATS_OUT / cat / f'{name}-tail.webp')
    log(f'  {tail_path.name}: tail overlay aligned to {notail_path.name}, {canvas.shape[1]}x{canvas.shape[0]}')


def process_cat_paws(cat, name, body_path, paws_path, scale, log):
    """A second pair of paws drawn apart from their pose's body (see PAWS_RE: <cat>-<pose>-paws.png),
    meant to sit IN FRONT of a held item while the body's own paws stay behind it -- body, then the
    item, then this overlay, sandwiching the item between the two (see CAT_HUG in index.html). Unlike
    process_cat_tail, the body art isn't replaced -- its own paws are the resting pose underneath."""
    placement = body_placement(body_path, scale)
    canvas, _, _ = align_overlay(paws_path, scale, placement)
    save_webp(canvas, CATS_OUT / cat / f'{name}-paws.webp')
    log(f'  {paws_path.name}: paws overlay aligned to {body_path.name}, {canvas.shape[1]}x{canvas.shape[0]}')


def process_item(name, path, scale, log):
    """scale is shared by every item, so an object drawn at the reference cat's size
    comes out at the reference cat's size in the yard."""
    scale = scale * OBJECT_SIZE.get(name, 1.0)
    pre = pre_cut_rgba(path)
    if pre is not None:
        rgba, bg_note = pre, 'already transparent, no cutout needed'
    else:
        img = load(path)
        if name in DESHADOW:
            chroma = img[..., :3].max(-1) - img[..., :3].min(-1)
            img = img.copy()
            img[chroma < DESHADOW_CHROMA, :3] = border_colour(img)
        rgba, bg, _ = cut_out(img, clear_holes=name in CLEAR_HOLES)
        bg_note = f'backdrop {bg.round().astype(int).tolist()}'
    if name in MAIN_BLOB:
        rgba = rgba * largest_component(rgba[..., 3] > TRIM_ALPHA)[..., None]
    if name in SHADOW_CUT:
        rgba = drop_shadow(rgba, from_frac=SHADOW_CUT[name])
    ys, xs = np.where(rgba[..., 3] > TRIM_ALPHA)
    x_raw, y_raw = xs.min(), ys.min()          # where the trimmed content starts in the raw image
    rgba = trim(rgba)
    h, w = rgba.shape[:2]
    log(f'  {path.name}: {bg_note}, content {w}x{h}, '
        f'scale {scale:.4f} -> {round(h * scale)}x{round(w * scale)} px')
    center_bbox = name in CENTER_BBOX or name.startswith(CENTER_BBOX_PREFIXES)
    canvas = compose(rgba, scale, name, center='bbox' if center_bbox else 'body')
    shift = OBJECT_SHIFT.get(name, 0)
    dx, dy = shift if isinstance(shift, tuple) else (shift, 0)
    if dx or dy:
        moved = np.zeros_like(canvas)
        moved[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = \
            canvas[max(0, -dy):H - max(0, dy), max(0, -dx):W - max(0, dx)]
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


def process_floating(name, path, scale, log):
    """A free-floating overlay (see FLOATING): cut out, trim, scale to the shared item scale, and save
    as-is with no baseline placement -- same treatment as the bath water/steam layers."""
    pre = pre_cut_rgba(path)
    if pre is not None:
        rgba, bg_note = pre, 'already transparent, no cutout needed'
    else:
        rgba, bg, _ = cut_out(load(path), clear_holes=name in CLEAR_HOLES)
        bg_note = f'backdrop {bg.round().astype(int).tolist()}'
    rgba = trim(rgba)
    rgba = scale_img(rgba, scale * OBJECT_SIZE.get(name, 1.0))
    log(f'  {path.name}: {bg_note}, floating overlay {rgba.shape[1]}x{rgba.shape[0]}')
    out = OBJ_OUT / f'{name}.webp'
    save_webp(rgba, out)
    return out


def process_polaroid(kind, id_, n, path, log):
    """Trip art, from raw/polaroids/. Two kinds, told apart by filename prefix (see POLA_RE):
      bg-<dest>.png     a full-bleed destination plate, resize-only like a scene background. A
                        trailing digit (bg-<dest><n>.png) names one of several background VARIANTS
                        for that destination (see BG_VARIANTS in index.html) rather than a pose --
                        it's kept as part of the output id (e.g. bg-hirosaki2.png -> hirosaki2-bg.webp)
                        so each variant gets its own file instead of colliding on one.
      cat-<cat><n>.png  a cat cutout, pose n, on the usual gray backdrop, cut out and trimmed like
                        any other cat/item art, then height-normalised to SELFIE_HEIGHT. NOT
                        baseline-composed onto a canvas -- like FLOATING items, it's positioned
                        independently at runtime (its own x/y/scale per cat+destination pairing)."""
    if kind == 'bg':
        name = f'{id_}{n}' if n else id_
        img = Image.open(path).convert('RGB').resize(POLA_SIZE, Image.Resampling.LANCZOS)
        out = POLA_OUT / f'{name}-bg.webp'
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, 'WEBP', quality=SCENE_QUALITY, method=6)
        log(f'  {path.name}: background plate, resized to {POLA_SIZE[0]}x{POLA_SIZE[1]}')
        return out
    if n is None:
        raise SystemExit(f'{path}: cat cutouts need a pose number, e.g. cat-{id_}1.png')
    rgba, bg, _ = cut_out(load(path))
    rgba = trim(rgba)
    s = SELFIE_HEIGHT / rgba.shape[0]
    rgba = scale_img(rgba, s)
    out = POLA_OUT / f'{id_}-selfie{n}.webp'
    save_webp(rgba, out)
    log(f'  {path.name}: backdrop {bg.round().astype(int).tolist()}, cutout {rgba.shape[1]}x{rgba.shape[0]} '
        f'(scale {s:.4f} -> content height {SELFIE_HEIGHT})')
    return out


def process_stamp(dest, path, log):
    """A destination's day-trip stamp, from raw/stamps/stamp-<dest>.png -- a bonus collectible alongside
    the polaroid (see STAMP_CHANCE in index.html), one per destination rather than per cat. Cut out
    (or used as-is if already transparent -- see pre_cut_rgba), trimmed and height-normalised to
    STAMP_HEIGHT, same treatment as a selfie cutout: not baseline-composed, since it's displayed as
    a small badge rather than stood on a floor."""
    pre = pre_cut_rgba(path)
    if pre is not None:
        rgba, bg_note = pre, 'already transparent, no cutout needed'
    else:
        rgba, bg, _ = cut_out(load(path))
        bg_note = f'backdrop {bg.round().astype(int).tolist()}'
    rgba = trim(rgba)
    s = STAMP_HEIGHT / rgba.shape[0]
    rgba = scale_img(rgba, s)
    out = STAMP_OUT / f'{dest}.webp'
    save_webp(rgba, out)
    log(f'  {path.name}: {bg_note}, stamp {rgba.shape[1]}x{rgba.shape[0]} (scale {s:.4f} -> content height {STAMP_HEIGHT})')
    return out


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
    cat_tails = defaultdict(dict)   # {cat: {pose: {'notail': path, 'tail': path}}} -- see TAIL_RE
    cat_paws = defaultdict(dict)    # {cat: {pose: path}} -- see PAWS_RE
    items = {}
    for p in sorted((RAW / 'cats').glob('*.png')):
        m = POSE_RE.match(p.stem)
        if m:
            cat_frames[m['cat']][(m['pose'], int(m['n'] or 1))] = p
            continue
        m = TAIL_RE.match(p.stem)
        if m:
            cat_tails[m['cat']].setdefault(m['pose'], {})[m['part']] = p
            continue
        m = PAWS_RE.match(p.stem)
        if m:
            cat_paws[m['cat']][m['pose']] = p
            continue
        raise SystemExit(f'{p}: not a <cat>-<pose>[-<n>].png name, expected in raw/cats/')
    for p in sorted((RAW / 'objects').glob('*.png')):
        items[p.stem] = p
    # Food items live in their own subfolder, but process and output the same way as any other item.
    for p in sorted((RAW / 'food').glob('*.png')):
        items[p.stem] = p
    # yarn2.png is the current yarn (ball with the string toward the cat); yarn.png is kept in raw/objects/ but not used.
    if 'yarn2' in items:
        items['yarn'] = items.pop('yarn2')
    for alias, source in ITEM_SOURCE.items():
        if source in items:
            items[alias] = items[source]
    for alias, raw_name in ITEM_RAW_NAME.items():
        if raw_name in items:
            items[alias] = items.pop(raw_name)
    floating = {name: items.pop(name) for name in list(items) if name in FLOATING}

    log = print
    sheet_rows = []
    # Pass 1: cut every cat's frames and get its own sit-based scale. Needed in full before pass 2,
    # since BODY_MATCH's cross-cat targets (below) depend on every cat's cut content.
    prepared = {}
    for cat in sorted(cat_frames):
        log(f'cat {cat}')
        tails = {}
        for pose, parts in cat_tails.get(cat, {}).items():
            if 'notail' in parts and 'tail' in parts:
                cat_frames[cat][(pose, 1)] = parts['notail']
                tails[pose] = (parts['notail'], parts['tail'])
            else:
                log(f'  WARNING {cat}-{pose}: only -{next(iter(parts))}.png present, need both -notail and -tail')
        prep = prepare_cat(cat, cat_frames[cat], log)
        if prep:
            prepared[cat] = (prep, tails)

    # BODY_MATCH targets: the roster's median content size (on the pose's own matched dimension, at
    # each cat's own scale) for that pose, so the fix centres on the roster's existing look instead of
    # an arbitrary constant.
    pose_targets = {}
    for pose, dim_name in BODY_MATCH.items():
        dim = 1 if dim_name == 'width' else 0
        sizes = sorted(cut[(pose, 1)].shape[dim] * s for (cut, s, _sit_head), _tails in prepared.values() if (pose, 1) in cut)
        if sizes:
            pose_targets[pose] = sizes[len(sizes) // 2]
            log(f'{pose}: {dim_name} target {pose_targets[pose]:.1f}px (median of {len(sizes)} cats)')

    # Pass 2: compose+save, now that pose_targets is known.
    for cat in sorted(prepared):
        (cut, s, sit_head), tails = prepared[cat]
        sheet_rows.extend(compose_cat(cat, cat_frames[cat], cut, s, sit_head, pose_targets, log,
                                       tails=tails, paws=cat_paws.get(cat, {})))

    if items or floating:
        ref = cat_frames.get(REF_CAT, {}).get(('sit', 1))
        if ref is None:
            raise SystemExit(f'items need {REF_CAT} sit in raw/cats/ to set the shared scale')
        ref_h = trim(cut_out(load(ref))[0]).shape[0]
        item_scale = SIT_HEIGHT / ref_h
        log(f'shared item scale {item_scale:.4f} (from {REF_CAT} sit: {ref_h} px -> {SIT_HEIGHT} px)')
        for name in sorted(items):
            log(f'item {name}')
            _, canvas = process_item(name, items[name], item_scale, log)
            sheet_rows.append((name, items[name], canvas))
        for name in sorted(floating):
            log(f'floating {name}')
            process_floating(name, floating[name], item_scale, log)

    for path in sorted((RAW / 'scene').glob('*.png')):
        # Scenes are full-bleed backgrounds: resize only, no background removal.
        # Room pictures are 9:16 and get their own size below. The four-room panorama keeps its own size.
        if path.stem.startswith(ROOM_PREFIX):
            continue
        if path.stem == PANO_PREFIX or path.stem.startswith(PANO_PREFIX + '-'):
            log(f'panorama {path.name}')
            img = Image.open(path).convert('RGB')
            out = SCENE_OUT / f'{path.stem}.webp'
            img.save(out, 'WEBP', quality=PANO_QUALITY, method=6)
            log(f'  -> {out.relative_to(YARD)} {img.size[0]}x{img.size[1]}')
            continue
        log(f'scene {path.name}')
        img = Image.open(path).convert('RGB').resize(SCENE_SIZE, Image.Resampling.LANCZOS)
        out = SCENE_OUT / f'{path.stem}.webp'
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, 'WEBP', quality=SCENE_QUALITY, method=6)
        log(f'  -> {out.relative_to(YARD)} {SCENE_SIZE[0]}x{SCENE_SIZE[1]}')

    for p in sorted((RAW / 'polaroids').glob('*.png')):
        m = POLA_RE.match(p.stem)
        if not m:
            raise SystemExit(f'{p}: not a bg-<dest>.png or cat-<cat><n>.png name, expected in raw/polaroids/')
        log(f'polaroid {p.name}')
        process_polaroid(m['kind'], m['id'], m['n'], p, log)

    for p in sorted((RAW / 'stamps').glob('stamp-*.png')):
        dest = p.stem.removeprefix('stamp-')
        log(f'stamp {p.name}')
        process_stamp(dest, p, log)

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
