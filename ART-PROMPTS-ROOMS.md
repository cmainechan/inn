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
```
Soft Japanese picture-book illustration of ONE object, same style as the
attached reference. Flat plain light grey background (#D0D0D0). Square
1254 x 1254. The object is centred with about 10% margin, seen from the
side at eye level with a slight view from above. No ground shadow, no
cast shadow on the background, no text, no cat, no people, no frame.
Scale: draw it at the size shown in the notes, where "a sitting cat" is
the attached reference cat.
```

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

## Checklist for each finished room

- [ ] 9:16 portrait, nothing cropped, no text or watermark.
- [ ] Floor from 38% down is completely clear and calm.
- [ ] Nothing important in the outer 9% on each side.
- [ ] Top 12% is plain.
- [ ] Light comes from the upper right and matches the other rooms.
- [ ] No cats, people, or furniture on the floor.
- [ ] Looks like the same inn as the other rooms.

When you have the four PNGs, put them in `raw/scene/` as `room-zashiki.png`, `room-shokudo.png`, `room-engawa.png`, `room-onsen.png`.
