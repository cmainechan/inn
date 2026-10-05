# Neko Ryokan: room art specs

The game is `index.html` (open `/index.html?test`). It currently uses low-resolution room backgrounds in `scene/room-*.webp`. Ready-to-paste image prompts are in `ART-PROMPTS-ROOMS.md`.

## How the rooms work

- Four rooms side by side. The player swipes left and right between them, like walking through the inn.
- Each room is a **portrait picture, 9:16**. On a phone it fills the screen. On a desktop it is a centred strip with the next room peeking in at the side.
- Items belong to one room. A cat only visits items in that room, so each room has its own shop and its own regulars.
- **Four item spots per room**, in the same places in every room (see `guides/room-layout-guide.png`). The shop has up to 10 items per room. Each room has four spots, so a room shows at most four items on the floor at once.

## Rooms (all Japanese names)

| # | Room | Japanese | Notes |
|---|---|---|---|
| 1 | Tatami room | 座敷 (ざしき, zashiki) | Guest room with an alcove and shoji window |
| 2 | Dining room | 食事処 (しょくじどころ, shokujidokoro) | Noren curtain, shelves, wooden floor |
| 3 | Veranda | 縁側 (えんがわ, engawa) | Open to the garden, the most scenic room |
| 4 | Hot spring | 温泉 (おんせん, onsen) | Outdoor stone bath area |

## Background images (4 files)

| | |
|---|---|
| Size | **1440 × 2560 px** PNG (9:16 portrait) |
| Files | `raw/scene/room-zashiki.png`, `room-shokudo.png`, `room-engawa.png`, `room-onsen.png` |
| Content | Empty room only. No items, cats, people, or text. |
| Style | Soft picture-book style, same as `scene/ryokan.webp`: warm daylight from the upper right, honey wood and greens, gentle shadows. |
| Light | All four rooms share the same light direction and colour temperature so they feel like one building. |

Layout zones (all marked on `guides/room-layout-guide.png`):

- **Top 12%:** hidden under the fish counter and room name. Ceiling or beam only.
- **12% to 38%: back wall.** Windows, alcoves and scenery. The floor meets the wall at about 38%.
- **38% to 88%: floor.** Open and quiet, with a plain texture (tatami, wood, stone). Items and cats sit here. No furniture, rugs or strong patterns.
- **Bottom 12%:** hidden under the buttons. Plain floor only.
- **Outer 9% left and right:** cropped on narrow phones. Walls and pillars only.
- Perspective: one-point, eye level slightly above the floor.
- Optional: the right edge of each room hints at a door to the next room, and the left edge at the previous one.

## Items: four per room

Items use the rules in `ART-SPEC.md` (flat `#D0D0D0` background, 1254 × 1254, 10% margin, shared scale with a sitting cat). Add `<item>-front.png` where the cat sits inside.

| Room | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 座敷 Tatami | cushion 座布団 (have) | box 箱 (have) | basket 籠 (have) | tent テント (have) |
| 食事処 Dining | onigiri おにぎり (have) | takoyaki たこ焼き (have) | taiyaki たい焼き (have) | mochi 餅 (have) |
| 縁側 Veranda | ball 毬 (have) | yarn 毛糸 (have) | red panda suit レッサーパンダ (have) | **bonsai 盆栽 (new, cat sits beside)** |
| 温泉 Onsen | big taiyaki 大きなたい焼き (have, a cat rides it like a boat) | **stone onsen 岩風呂 (new; one image, the front rim is cut from it)** | **foot bath 足湯 (new; one image, the front wall is cut from it, cat sits behind it)** | **towels 手拭い (new, cat sleeps on top)** |

The matcha cup is a temporary stand-in for a bath in the prototype and goes away once the real stone onsen art exists.

## Not decided yet

- Per-room cat preferences (a regular who loves one room).
- Seasonal versions of the veranda (cherry blossom, fireflies, maple, snow): same layout and floor, a different back wall.
- A `soak` cat pose (head and ears above water) for the stone onsen.

## Files the pipeline will need

`tools/process_art.py` needs one new step: read `raw/scene/room-*.png`, resize to 1080 × 1920 (or keep 1440 × 2560), write `scene/room-<id>.webp`. Then the `scene/room-*.webp` files are replaced by the full-size versions. Until then, nothing in the pipeline changes.
