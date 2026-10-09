# Yard art specs

Specs for every image to generate. Save raw files to `inn/raw/` and run `python3 tools/process_art.py` to produce the web files.

## Common to all cats and objects

- Flat light gray background, `#D0D0D0`. No backdrop shadows, no text, no frame.
- Soft picture-book style, matching the Tapuz images.
- Square, 1254×1254 PNG.
- Whole subject visible with about 10% margin. Side-on or front-on, eye level, centred.
  (Superseded for room items by the shared camera in `ART-PERSPECTIVE-SPEC.md` --
  that doc's wording is what actually matches the room backgrounds' perspective.)
- Filenames:
  - Cats: `<cat>-<pose>.png`, for example `sheleg-sit.png`
  - Extra frames: `<cat>-sleep-2.png`
  - Objects: `<item>.png`, for example `box.png`

## Cats (remaining 6 cats × sit, sleep, lie)

- **Sit:** feet and tail visible, body upright.
- **Sleep:** curled, head and body in frame.
- **Lie:** faces left, paws at the front-left.
- Keep framing and scale consistent across cats, so each cat is roughly the same size in its own frame.

## Objects

Draw all objects to one shared scale. The reference is a sitting Tapuz in the same frame.

| Item | Pose on it | Size relative to a sitting cat | Notes |
|---|---|---|---|
| `cushion` | sleep | about 1.5× cat width, flat | Low and soft, cat lies on top |
| `ball` | lie | about one-third of cat head height | Lie cat sits to its right, so the ball is on the left |
| `box` | sit | about one cat tall | **Front wall** visible in the lower part, open top |
| `yarn` | lie | similar to ball, with loose thread | Same lie-left rule as ball |
| `basket` | sleep | about one cat tall | **Front rim** visible in the lower band, dark interior at the top |
| `tent` | sit | about 1.5× cat height | Doorway centred at the bottom, large enough for a cat in front |

For box and basket, the front wall or rim must be a clear, separate band, so it can be cut into the front layer.

## Combined images (one cat on one object)

These are now the preferred art. Each one replaces the separate cat and object layers on that spot, so the generator sets the size and the overlap.

- Filename: `raw/combos/<cat>-<item>.png`, for example `raw/combos/sheleg-cushion.png`.
- Same backdrop, square 1254×1254 PNG, and common-style rules as above.
- The cat is in the pose that item uses: sleep on the cushion and basket, sit in the box and tent, lie for ball and yarn.
- The cat and object share one ground line. The cat is drawn at the reference sitting size, as in the separate-object specs.
- Box and basket: the front wall or rim is drawn in front of the cat's lower body, so the cat looks inside. No separate front layer is needed.
- No shadows on the backdrop, no text.
- Keep the cat's framing the same as the separate-object reference: centred, with about 10% margin.
- 42 in total (7 cats × 6 objects). Start with the pairs you already have: `tapuz-cushion` and `tapuz-box`.
- Until a combined image exists, the yard shows the separate cat and object layers.

## Garden background (one daytime image)

- Path: `inn/raw/scene/garden.png`
- Size: 1600×1100 PNG (the yard's 16:11 shape).
- Full scene only. No items, animals, people or text.
- **Top 45%:** the garden. Distant trees, a low wall, a stone lantern, a maple or pine at the left and right edges, a bridge or pond at the far back. Keep the middle clear.
- **Bottom 55%:** open lawn or moss. Nothing tall or detailed in the central 70% of the width, because items sit there. Small pebbles or moss patches are fine.
- Soft daylight from the upper right, matching the sun in the current sky.
- Palette: greens close to `#9DCC6E` and `#B2D985`, sky close to `#A9DBF3`, warm stone and wood.
- Same soft picture-book style as the cats.
- Evening and night are CSS tints over this one image, so no separate versions are needed.

## Notes for the pipeline

- The `scene/` subfolder is not picked up by `process_art.py`, which reads only top-level `raw/*.png`.
- The garden is a resize-only export, not a background cut-out.
