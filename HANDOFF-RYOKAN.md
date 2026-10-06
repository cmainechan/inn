# Neko Ryokan: handoff

Paste the prompt below into a new Claude Code session started in `/Users/charmainechan/Documents/Hebrew/inn`.

```
I'm continuing work on "Neko Ryokan", a Neko Atsume-style cat game, a static site on GitHub Pages (https://cmainechan.github.io/inn/), no build step, one HTML file where practical, plain HTML/CSS/JS, no frameworks. Repo: /Users/charmainechan/Documents/Hebrew/inn (origin cmainechan/inn). Start by running git status and git log, then read HANDOFF-RYOKAN.md, ART-SPEC-ROOMS.md, ART-PROMPTS-ROOMS.md and index.html.

## Rules (unchanged)
- Do not commit or push without asking. Show the diff summary and the commit message, then wait for a go-ahead.
- raw/ is gitignored (~120MB). Never commit, delete or rename anything in it without asking.
- Test in a real browser before saying it's done, with screenshots at 1280x900 and 390x844.
- Use python3 -u for the pipeline. On macOS use sed -i '' or Python for edits.
- Serve the parent folder: cd /Users/charmainechan/Documents/Hebrew && python3 -m http.server 8765, then open http://localhost:8765/inn/index.html?test

## What we decided (from a long design session)
1. Concept: "Neko Ryokan". Cats come to stay at a Japanese inn. Immersive, full-screen, like Neko Atsume. The old 16:11 yard was too small on a phone. It has been removed; it is still in git history at ec9a694.
2. Full screen, four rooms side by side, swipe to move (CSS scroll-snap). Each room is a 9:16 portrait picture. On a phone it fills the screen, on desktop it is a centred strip with neighbours peeking in. HUD floats over it: fish counter, room name, room buttons, Shop and Cats buttons.
3. Rooms, left to right: 座敷 zashiki (tatami room), 食事処 shokujidokoro (dining room), 縁側 engawa (veranda), 温泉 onsen (hot spring). The room edges are designed to line up (shared floor line at 41% from the top, posts about 7% in from each edge).
4. Four item spots per room, in the same places in every room (percent of the stage: x/y bottom edge = 32/56, 68/60, 30/76, 70/80). Four items per room, and each item only belongs to one room, so each room has its own shop and its own regulars.
5. The game is purely Japanese in theme. Remove Hebrew from the game UI: room names, item names and cat names become Japanese (kana or kanji with romaji) with English text for the UI. Hebrew learning leaves the game and becomes a separate "study" experience.
6. Study desk: a low writing desk (文機, fumizukue) in the tatami room. Tapping it opens a full-screen iframe overlay with a study app (the existing Word builder at ../hwg/ and Interlinear practice at ../hbt/, and later any other language or subject). A "Back to the inn" button closes it. Fish are the reward. The study page sends window.parent.postMessage({type:'neko-ryokan:fish', amount, source}); the game checks the sender origin against an allowlist and adds the fish. hwg and hbt are on the same origin so they can also keep writing the shared localStorage wallet. Keep a small config list of study modules so adding one is a one-line change. Hebrew text inside the study pages keeps its nikkud.
7. The rooms game IS now index.html, the live main page. The old yard is gone. It uses the shared 'fish' wallet (so hwg and hbt still earn fish) and a new save key ryokan-save-v1. A temporary Study button lists links to ../hwg/ and ../hbt/ until the Study desk replaces it.

## Current state
- index.html: the game. Four rooms, per-room items, shop filtered by room, cats, visiting logic, gifts, ?test tools (+50 fish, summon cats, reset), evening tint. The UI text and item/cat names are still the old Hebrew names, and the matcha cup is a stand-in for a bath.
- scene/room-zashiki.webp, room-shokudo.webp, room-engawa.webp, room-onsen.webp: low-resolution (941x1672) versions of the real backgrounds, converted from images pasted in chat. The full-size originals are in my raw/ folder or Downloads.
- ART-SPEC-ROOMS.md and ART-PROMPTS-ROOMS.md: specs and prompts for the room backgrounds and new items. guides/room-layout-guide.png: layout zones (top 12% under HUD, back wall 12-38%, floor 38-88%, outer 9% cropped on phones).
- The old yard code was deleted from index.html. The old art that only it used (scene/ryokan.webp, combos/) is still in the repo and can be cleaned up.

## My art, now generated (in raw/ on this machine)
- Room backgrounds: raw/scene/room-zashiki.png, room-shokudo.png, room-engawa.png, room-onsen.png. The tool tools/process_art.py has no step for these yet.
- New items (one image each): bonsai, onsen-stone (large stone bath), foot-bath, towels, yuoke (wash bucket), yukata, bath-stool, onsen-scoop. Plus new cat poses. List raw/ to see exactly what exists, and tell me what is missing.
- Front layers: onsen-stone, foot-bath and yuoke need a front wall or rim, cut from the same image along a curve with FRONT_CURVES in process_art.py (as for box and basket). The stone onsen and foot bath should leave the cat visible above the rim.
- Items are drawn on a flat #D0D0D0 background that the pipeline removes, so check results for stones or wood that look grey and got eaten.

## To do, in this order
1. Add a room-background step to tools/process_art.py: raw/scene/room-<id>.png to scene/room-<id>.webp (keep the 9:16 shape, 1080x1920 or similar). Run python3 -u tools/process_art.py (takes a few minutes), then check git status.
2. Add the new items to ITEMS in index.html (room, pose, cat anchor, hasFront, wobble for toys) and tune the anchors by overlay. Per-cat nudges go in the item's offset table. Remove the matcha stand-in.
3. Replace Hebrew in the UI with Japanese names plus English. Ask me before inventing Japanese names for the seven cats (Tapuz, Pilpel, Sheleg, Dvash, Shoko, Rimon, Kokhav).
4. Build the Study desk and iframe overlay with the postMessage fish contract, with hwg and hbt as the first two modules.
5. Test at 1280x900 and 390x844 and send screenshots, including the seams between rooms 2/3 and 3/4. Ask before committing.

## Open questions for me
- Japanese names for the cats.
- Where the study desk sits in the tatami room (it takes one of the four spots, or sits as fixed decoration).
```
