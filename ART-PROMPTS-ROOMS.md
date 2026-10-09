# Neko Ryokan: image prompts

Copy-paste prompts for the four room backgrounds and the new items. Specs behind them are in `ART-SPEC-ROOMS.md`.

## Before you generate

**Reference images to attach to every room prompt**
1. `scene/ryokan.webp`: the style, light and palette to match.
2. `guides/room-layout-guide.png`: the composition. Say "use the second image only for layout zones, and do not draw its colours, boxes, ovals, numbers or text."

**Workflow that keeps the four rooms looking like one building**
1. Generate the **tatami room** first. Keep trying until you love it.
2. For each other room, attach the tatami room as a third reference: "same inn, same wood, same light, same art style."
3. After each result, check the checklist at the bottom, and regenerate if the floor has furniture on it.
4. Output size: ask for 9:16 portrait, 1440 × 2560. If the generator can't do that size, ask for 1152 × 2048 (9:16) and I will upscale. Never ask for a square and crop.

## Shared style block (paste at the top of every room prompt)

```
Soft Japanese picture-book illustration of an empty room in a traditional
Japanese inn (ryokan), for a cozy cat game. Warm gouache and watercolour
look, gentle outlines, soft shading, no photorealism, no 3D render.
Daylight comes from the upper right, warm and golden, with soft shadows
falling to the lower left. Palette: honey wood, pale green tatami,
warm cream paper screens, leafy greens, soft sky blue.
Portrait format, 9:16, one-point perspective, eye level slightly above
the floor, looking straight at the back wall.
Composition rules, important:
- The top 12% of the picture is plain ceiling or beam only.
- The back wall with all the scenery and detail occupies roughly the
  12% to 38% band from the top. The floor meets the back wall at about
  38% from the top.
- The floor fills from 38% to the bottom. Keep the floor completely
  clear, open and calmly textured. No furniture, no rugs, no tables,
  no cushions, no pots, no objects on the floor at all, because game
  items and cats are added on top later.
- The bottom 12% is plain floor.
- Keep the outer 9% on the left and right to walls, pillars or quiet
  edge details. No important detail in the outer 9%.
No cats, no animals, no people, no text, no signs, no logos, no
watermark, no frame, no border, no UI.
```

## Room 1: Tatami room (座敷 zashiki)

```
[Shared style block]

The room: a quiet guest room. Back wall: a wide shoji paper window on
the right with a view of green maple branches and soft sky, and on the
left a tokonoma alcove with a hanging scroll of a mountain and a small
vase with a plum blossom branch. A round paper lantern hangs from the
ceiling beam near the top centre. Honey-coloured wood pillars and
beams. Floor: neat pale green tatami mats with dark green edging,
arranged in a clean grid, plain and open, a soft patch of sunlight
falling across the floor from the window.
```

## Room 2: Dining room (食事処 shokujidokoro)

```
[Shared style block. Also attach the tatami room image as a third
reference: same inn, same wood, same light, same style.]

The room: the inn's cosy dining room. Back wall: a kitchen pass-through
opening hung with a short indigo noren curtain, wooden shelves beside it
holding teapots, bowls and a few jars, a hanging paper lantern, and a
small window showing a bamboo grove. Warm honey wood panelling, cream
plaster. Floor: warm polished wooden boards running toward the back wall,
plain and open, soft reflections of window light. No table, no stools,
nothing on the floor.
```

## Room 3: Veranda (縁側 engawa)

```
[Shared style block. Also attach the tatami room image as a third
reference.]

The room: the inn's veranda, open to the garden. Back wall: no wall at
all, a wide open view to a Japanese garden: a stone lantern, a small
pond with a few orange koi, a red maple tree, soft moss and raked
gravel, clipped pines, bamboo, and hazy blue hills far behind. A
sliding shoji door frame at each side. A small bamboo blind rolled up
under the eave. Floor: warm honey wooden veranda boards with a clear
grain running toward the garden, plain and open. Sunlight is strongest
in this room.
```

## Room 4: Hot spring (温泉 onsen)

```
[Shared style block. Also attach the tatami room image as a third
reference.]

The room: the inn's outdoor hot spring area at dusk-gold light. Back
wall: a tall bamboo fence with a few smooth boulders, soft steam rising
behind it, a maple branch hanging over, a lantern glowing warm, and a
sky going from soft peach to pale blue. Honey wooden walls at the
sides. Floor: large flat pale stone slabs with thin mortar lines and a
wooden border, plain and open, slightly damp-looking with a soft sheen.
No tubs, no buckets, no towels on the floor, since those are separate
game items.
```

## New items

Reference for the style: any existing item, for example `objects/box.webp` (or its raw PNG). Attach one existing item and the matching cat sitting reference to set the scale.

**Shared item block (paste at the top of every item prompt)**

Camera: see `ART-PERSPECTIVE-SPEC.md` for why this exact wording matters —
it's the same camera as the room backgrounds, not a generic "eye level"
product shot. Getting this right here is what saves a manual angle-fix
later.

```
Soft Japanese picture-book illustration of ONE object, same style as the
attached reference. Flat plain light grey background (#D0D0D0). Square
1254 x 1254. The object is centred with about 10% margin. Same camera as
the room it sits in: eye level but slightly above the floor, looking down
at a shallow angle (roughly 15-20 degrees below horizontal). The object
sits flat on a floor and is drawn from that shallow, slightly-overhead
angle -- not side-on, not top-down. Its near edge sits low in the frame
and reads wide; its far edge sits higher in the frame and reads slightly
narrower, with its top surface faintly visible -- mild foreshortening,
the same amount a rug or tray shows seen at a low angle rather than
dead-on. No ground shadow, no cast shadow on the background, no text, no
cat, no people, no frame.
No steam, no smoke, no haze rising off the object: it never cuts out
cleanly against the grey background (same reason the onsen prompts
below say "no steam") and leaves a grey smudge in the finished item.
Scale: draw it at the size shown in the notes, where "a sitting cat" is
the attached reference cat.
```

Before accepting a result, run it through the checklist in
`ART-PERSPECTIVE-SPEC.md` (near edge low+wide, far edge high+narrow, a
sliver of top surface visible, tilt matches an existing good item like
`objects/box.webp`).

| Room | Item | Prompt |
|---|---|---|
| Veranda | 盆栽 bonsai | `[Shared item block] A small pine bonsai in a shallow glazed blue-green ceramic pot on a low wooden stand. Pot width about 70% of a sitting cat's width. A cat will sit next to it, so keep the left half of the image plain.` |
| Onsen | 岩風呂 stone onsen | One image only: `onsen-stone.png`. Use the prompt on the prompts page: large stone bath, warm brown and tan boulders with moss, milky blue water, three yuzu, clean continuous near rim, no steam, no grey stones. |
| Onsen | 足湯 foot bath | One image only: `foot-bath.png`. Use the prompt on the prompts page: small honey-wood hinoki trough with milky blue water, clean straight near wall, nothing inside, no steam. |
| Onsen | 手拭い towels | `[Shared item block] A neat stack of three folded white cotton hand towels, a pale blue stripe on the top one, soft rounded shapes. Width about 1.2x a sitting cat, height about one-third of a cat. A cat will sleep on top.` |
| Optional | 湯桶 wash bucket | `yuoke.png`, one image, front wall cut from it, cat sits inside (half pose). Prompt on the prompts page. |
| Optional | 浴衣 folded yukata | `yukata.png`, one image, flat and low, cat sleeps on top. Prompt on the prompts page. |
| Optional | 風呂椅子 bath stool | `bath-stool.png`, one image, low slatted hinoki stool, cat sits on top. Prompt on the prompts page. |
| Optional | 手桶 scoop with handle | `onsen-scoop.png`, one image, lies on its side with the handle pointing left and the right 40% empty, cat lies to its right (lie pose, like the ball). Prompt on the prompts page. |

The three existing items listed for each room don't need new art.

## Food (dining room shop tier, consumable)

These are a separate layer from the dining room's sittable props above
(onigiri, takoyaki, taiyaki, mochi): no cat ever poses on or visits
food, it just gets set out and is eaten up after its duration. Save
raw files to `raw/food/<item>.png`, not plain `raw/<item>.png` — the
pipeline reads both, but keeping food in its own folder keeps the shop
tiers easy to find. Ordered cheapest to most expensive; kaiseki is the
flagship, priciest item.

| Order | Item | Prompt |
|---|---|---|
| 1 (cheapest) | お茶漬け ochazuke | Done — `objects/ochazuke.webp`, from `raw/food/ochazuke.png`. |
| 2 | 卵焼き tamagoyaki | Done — `objects/tamagoyaki.webp`, from `raw/food/tamagoyaki.png`. |
| 3 | 焼き鳥 yakitori | Done — `objects/yakitori.webp`, from `raw/food/yakitori.png`. |
| 4 | 天ぷら盛り合わせ tempura moriawase | Done — `objects/tempura.webp`, from `raw/food/tempura.png`. |
| 5 | ちらし寿司 chirashizushi | Done — `objects/chirashi.webp`, from `raw/food/chirashi.png`. |
| 6 | うな丼 unadon | Done — `objects/unadon.webp`, from `raw/food/unadon.png`. |
| 7 (most expensive) | 懐石 kaiseki | Done — `objects/kaiseki.webp`, from `raw/food/kaiseki.png`. |

Each new food item needs an `ITEMS` entry in index.html with
`food: true`, a `duration` in minutes, and no `pose`/`cat` fields
(those only matter for items a cat visits). All seven are done now.

### Food spot placemat

Food is set out on the open dining-room floor, not the counter (the
counter blended too much with the background shelf clutter). The spot
is marked by a placemat, always drawn whether or not food is out —
done, `objects/food-mat.webp` from `raw/food/food-mat.png`. The first
version was drawn from almost directly overhead, which read as
standing upright once composited into the room rather than lying flat;
the prompt below (used for the current version) asks for the same
shallow, nearly edge-on angle as every other item instead.

```
[Shared item block] A rectangular woven rush-grass placemat
(ランチョンマット), lying flat on a floor. Drawn at the same shallow,
nearly edge-on angle as the room scenes and every other floor-level
item — NOT a top-down or almost-overhead view. Looking across the
floor at a low angle, so the mat is strongly foreshortened: its near
edge is low in the frame and appears wide, its far edge is higher in
the frame and appears noticeably narrower, the way a rug recedes when
seen nearly edge-on rather than from above. Natural tan woven texture
with a simple thin dark-brown fabric border trim, a small embroidered
or dyed accent near the near corner (e.g. a single pale green maple
leaf or pine sprig) echoing the inn's palette. Plain, uncluttered,
nothing on top of it. Width about 1.6x a sitting cat's width — wide
enough that a small food plate sits clearly inside its border once
placed on top.
```

## Checklist for each finished room

- [ ] 9:16 portrait, nothing cropped, no text or watermark.
- [ ] Floor from 38% down is completely clear and calm.
- [ ] Nothing important in the outer 9% on each side.
- [ ] Top 12% is plain.
- [ ] Light comes from the upper right and matches the other rooms.
- [ ] No cats, people, or furniture on the floor.
- [ ] Looks like the same inn as the other rooms.

When you have the four PNGs, put them in `raw/scene/` as `room-zashiki.png`, `room-shokudo.png`, `room-engawa.png`, `room-onsen.png`.
