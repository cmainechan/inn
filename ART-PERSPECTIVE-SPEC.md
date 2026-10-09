# Neko Ryokan: one shared camera

Why item art keeps needing hand angle-fixes: the room backgrounds and the
items have never been specified from the same camera. `ART-PROMPTS-ROOMS.md`
nails the room camera down precisely ("one-point perspective, eye level
slightly above the floor, looking straight at the back wall," floor from 38%
to 100%). But the item spec (`ART-SPEC.md`, and the shared item block in
`ART-PROMPTS-ROOMS.md`) says items are drawn "side-on... at eye level" — a
flat, head-on product-photo angle. That's a different camera. Every item is
effectively guessing its own perspective, which is why each one (kaiseki, the
food-mat, food bowls) needed a separate manual fix instead of just working.

This doc defines one camera and ties it to measured numbers already in the
game, so future art and future fixes both derive from the same source instead
of being re-eyeballed per item.

## The camera, in one paragraph (paste this into every item prompt)

> Same camera as the room it sits in: eye level but slightly above the floor,
> looking down at a shallow angle (roughly 15-20° below horizontal) across a
> floor that recedes toward the back wall. The object sits flat on that floor
> and is drawn from that same shallow, slightly-overhead angle — not
> side-on, not top-down. Its near edge (toward the viewer) sits low in the
> frame and reads wide; its far edge sits higher in the frame and reads
> slightly narrower, with its top surface faintly visible. Mild
> foreshortening, the same amount a rug or tray shows when seen at a low
> angle rather than dead-on.

This replaces the "seen from the side at eye level with a slight view from
above" line in the shared item block. That line was vague enough to produce a
different angle every generation; the paragraph above gives a concrete tilt
and a concrete tell (near edge low+wide, far edge high+narrow) a reviewer can
check for before accepting art, instead of discovering the mismatch only
after compositing into the room.

This is exactly the technique that already worked for the food-mat prompt
("looking across the floor at a low angle, so the mat is strongly
foreshortened..."). The fix here is making it the *default* for every item,
not a one-off, so the next ochazuke or kaiseki doesn't need it rediscovered.

## Measured floor-plane bands (ground truth, from the live art + code)

Each room is one slice of `scene/ryokan-pano.webp`, 4096×1213px total, 6
slices wide (margin, 4 rooms, margin) → each room slice is 683px wide,
1213px tall. Cropping and inspecting all four:

| Room | Back wall meets floor at | Floor fills down to |
|---|---|---|
| All 4 rooms | ~38% from top (matches the room-background spec exactly) | 100% (bottom edge) |

This is also exactly what the hand-tuned item coordinates in `index.html`
already assume, which is a second, independent confirmation:

- `DESK` (tatami room, against the back wall): `y: 47` — just past the 38%
  wall line, i.e. right at the back of the floor.
- `FOOD_SPOT` (dining room): `y: 48.6` — also near the back.
- `SPOTS` (all rooms): `y: 56, 60, 76, 80` — the two back spots (56, 60) sit
  mid-floor, the two front spots (76, 80) sit close to the viewer.
- Front-most items: `tent y: 94`, `ball`/`yarn y: 93-94` — near the bottom
  edge, closest to camera.

So **y in game-coordinates (0% = back wall, 100% = bottom of frame) already
is depth** — not just a layout knob. An item/cat placed at y=48 is "far" from
camera, one at y=90 is "near." This was arrived at by hand per-item; it's
worth treating as a documented rule going forward rather than re-discovering
it with every placement.

## Depth-based scale (the next source of "looks a bit off," worth doing deliberately)

Right now every placed instance of an item uses one fixed `scale` regardless
of which spot (back vs. front) it lands in — `SPOTS` don't vary size by
depth. In a real one-point perspective, something at y=56 (mid-floor) should
read smaller than the same object at y=80 (near camera). The mismatch is
subtle and hasn't been the main complaint, but it compounds with the camera
mismatch above to make placed items feel slightly "glued on" rather than
sitting in the room.

If this is worth fixing: derive a per-spot scale multiplier from y, e.g.
`scale = 0.85 + (y - 45) / 50 * 0.3` (roughly 0.85× at the back wall, 1.15×
at the front edge), applied on top of each item's own base scale. This is a
one-line change in `itemLayers()`/spot rendering, not an art change — doesn't
require regenerating anything. Worth doing after the camera-angle fix above,
once that stops being the dominant source of mismatch.

## Review checklist before accepting new item art

Check these against the paragraph above before running it through the
pipeline, instead of discovering the mismatch live in the game:

- [ ] Near edge of the object is low in frame and reads wide.
- [ ] Far edge is higher in frame and reads narrower than the near edge.
- [ ] A faint sliver of the top surface is visible (not a pure side-on
      silhouette, not a top-down plan view).
- [ ] Held up next to an existing good item (e.g. `objects/box.webp`) at the
      same frame size, the two tilt angles look like the same camera.
- [ ] No steam/smoke/haze (existing rule, still applies, unrelated reason).

## What this doesn't fix

This is a documentation/prompt discipline fix, not a geometry engine — it
won't make every generation perfect, and flat-lay-ish items (food trays,
mats, cushions) will still be far more forgiving of small angle errors than
tall or strongly 3D objects (boxes, tiered dishes like kaiseki). Where an
item is inherently hard to get right at this angle, it's reasonable to
simplify the object's silhouette (flatter, less three-dimensional) rather
than keep fighting the angle — charm over strict accuracy.
