#!/usr/bin/env python3
"""Cross-check the processed art on disk against what index.html expects, and vice versa.

Run on its own (python3 -u tools/check_art.py, exit 1 if anything is an ERROR) or via
process_art.py, which runs it after every pipeline run (--no-check to skip, --check to run only this).

ERROR  the game will show a broken image or misbehave: referenced art is missing, a pose is wired up
       without art, a count in index.html disagrees with the files on disk.
WARN   art or config that doesn't line up but won't break anything yet: a cat with art but no CATS
       entry, an output nothing references (e.g. a stray panorama variant), a pose with art that
       READY_POSES won't let a visitor use.

index.html is parsed with regexes, not executed, so this only understands the shapes the file uses now
(object literals keyed by id, one `const NAME = ...` per structure). If a structure is reshaped and a
check goes quiet or noisy, fix the parser here rather than ignoring the output.
"""
import re
import sys
from pathlib import Path

YARD = Path(__file__).resolve().parent.parent
INDEX = YARD / 'index.html'


# ---------- a tiny JS-literal scanner ----------

def _skip_string(s, i):
    """s[i] is a quote; return the index just past the closing quote."""
    q = s[i]
    i += 1
    while i < len(s) and s[i] != q:
        i += 2 if s[i] == '\\' else 1
    return i + 1


def _strip_comments(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c in '\'"`':
            j = _skip_string(s, i)
            out.append(s[i:j])
            i = j
        elif s.startswith('//', i):
            while i < len(s) and s[i] != '\n':
                i += 1
        elif s.startswith('/*', i):
            i = s.find('*/', i) + 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def _balanced(s, start):
    """s[start] is an opening bracket; return the text strictly inside the matching pair."""
    pairs = {'{': '}', '[': ']', '(': ')'}
    depth, i = 0, start
    while i < len(s):
        c = s[i]
        if c in '\'"`':
            i = _skip_string(s, i)
            continue
        if c in pairs:
            depth += 1
        elif c in pairs.values():
            depth -= 1
            if depth == 0:
                return s[start + 1:i]
        i += 1
    raise ValueError('unbalanced')


def const_body(js, name):
    """Text inside the {...} / [...] / ( ... ) that `const NAME =` starts, or None."""
    m = re.search(rf'\bconst {re.escape(name)}\s*=\s*(?:new Set\()?\s*([\[{{])', js)
    if not m:
        return None
    return _balanced(js, m.end() - 1)


def top_level_entries(body):
    """{key: value text} for an object-literal body, splitting on depth-0 commas."""
    entries, depth, i, start = {}, 0, 0, 0
    parts = []
    while i < len(body):
        c = body[i]
        if c in '\'"`':
            i = _skip_string(body, i)
            continue
        if c in '{[(':
            depth += 1
        elif c in '}])':
            depth -= 1
        elif c == ',' and depth == 0:
            parts.append(body[start:i])
            start = i + 1
        i += 1
    parts.append(body[start:])
    for part in parts:
        m = re.match(r'\s*([\'"]?)([\w-]+)\1\s*:\s*(.*)', part, re.S)
        if m:
            entries[m.group(2)] = m.group(3)
    return entries


def str_list(text):
    return re.findall(r'[\'"]([\w-]+)[\'"]', text or '')


# ---------- the checks ----------

def run_checks(log=print):
    """Print every finding; return the number of ERRORs."""
    html = INDEX.read_text()
    # Only the game script: apostrophes in the page's markup/CSS would otherwise look like string starts.
    js = _strip_comments(html[html.rindex('<script'):])
    errors, warns = [], []
    err, warn = errors.append, warns.append
    exists = lambda rel: (YARD / rel).exists()

    cats = top_level_entries(const_body(js, 'CATS') or '')
    items = top_level_entries(const_body(js, 'ITEMS') or '')
    dests = top_level_entries(const_body(js, 'DESTINATIONS') or '')
    hug = top_level_entries(const_body(js, 'CAT_HUG') or '')
    tails = top_level_entries(const_body(js, 'CAT_TAILS') or '')
    selfies = top_level_entries(const_body(js, 'SELFIE_POSES') or '')
    bg_variants = top_level_entries(const_body(js, 'BG_VARIANTS') or '')
    trip_offset = top_level_entries(const_body(js, 'TRIP_OFFSET') or '')
    ready = set(str_list(const_body(js, 'READY_POSES')))
    for name, found in (('CATS', cats), ('ITEMS', items), ('DESTINATIONS', dests), ('READY_POSES', ready),
                        ('SELFIE_POSES', selfies)):
        if not found:
            err(f'index.html: couldn\'t parse {name} -- this checker needs updating, other results are unreliable')

    # -- cats --
    cat_dirs = {d.name: d for d in (YARD / 'cats').iterdir() if d.is_dir()}
    for cid in cats:
        if not exists(f'cats/{cid}/sit.webp'):
            err(f'cat {cid}: in CATS but cats/{cid}/sit.webp is missing')
    for cid in sorted(set(cat_dirs) - set(cats)):
        warn(f'cats/{cid}/: has art but no CATS entry, so the cat can never visit')

    # -- items --
    poses_used, overlay_names = set(), set()
    for iid, body in items.items():
        if not exists(f'objects/{iid}.webp'):
            err(f'item {iid}: in ITEMS but objects/{iid}.webp is missing')
        if re.search(r'\bhasFront\s*:\s*true', body) and not exists(f'objects/{iid}-front.webp'):
            err(f'item {iid}: hasFront but objects/{iid}-front.webp is missing')
        if re.search(r'\bwater\s*:', body) and not exists(f'objects/{iid}-water.webp'):
            err(f'item {iid}: has a water layer but objects/{iid}-water.webp is missing')
        # Floating layers are named by pattern in itemLayers(): <id>-wheel, <id>-fish, <id>-bell, <id>-acc<N>.
        overlays = [f'{iid}-wheel'] * bool(re.search(r'\bwheel\s*:', body)) + [f'{iid}-fish'] * bool(re.search(r'\bfish\s*:', body)) + [f'{iid}-bell'] * bool(re.search(r'\bbell\s*:', body))
        n_charms = len(re.findall(r'\{\s*x\s*:', (re.search(r'\bcharms\s*:\s*\[(.*)\]', body, re.S) or [None, ''])[1]))
        overlays += [f'{iid}-acc{n}' for n in range(1, n_charms + 1)]
        for ov in overlays:
            overlay_names.add(ov)
            if not exists(f'objects/{ov}.webp'):
                err(f'item {iid}: layer objects/{ov}.webp is missing')
        pm = re.search(r'\bposes\s*:\s*\[([^\]]*)\]', body)
        poses = str_list(pm.group(1)) if pm else str_list((re.search(r'\bpose\s*:\s*(\S+?)\s*[,}]', body) or [None, ''])[1])
        poses_used.update(poses)
        for pose in poses:
            if pose not in ready:
                warn(f'item {iid}: lists pose "{pose}", which is not in READY_POSES, so no visitor will ever use it')
        if re.search(r'\bhugged\s*:\s*true', body):
            hug_cats = [k.split('-')[0] for k in hug if k.endswith('-belly2')]
            if not hug_cats:
                err(f'item {iid}: hugged but CAT_HUG has no entries')

    # -- per-cat poses: which poses an item can ask for that a cat has no art for --
    lacking = {}   # pose -> [cats]
    for cid in cats:
        if re.search(r'\bonly\s*:', cats[cid]):
            continue
        have = {f.stem for f in (YARD / 'cats' / cid).glob('*.webp')} if (YARD / 'cats' / cid).exists() else set()
        skipped = set(re.findall(r"'([a-z0-9-]+)'", (re.search(r'noPose\s*:\s*\[([^\]]*)\]', cats[cid]) or [None, ''])[1]))
        for pose in sorted(poses_used & ready):
            if pose not in have and pose not in skipped:
                lacking.setdefault(pose, []).append(cid)
        for pose in sorted(skipped & have):
            warn(f'CATS {cid}: noPose lists "{pose}" but cats/{cid}/{pose}.webp exists, so the cat is being skipped for no reason')
    for pose, who in lacking.items():
        warn(f'pose "{pose}" is offered by an item but has no art for: {", ".join(who)}. pickPose only checks '
             f'READY_POSES, not the cat\'s art, so a visitor given that pose would show a broken image unless '
             f'something else filters them out')

    # -- food pool: every non-`only` cat with full (eating) art should be able to eat at the food spot --
    pool = set(str_list(const_body(js, 'FOOD_CAT_POOL')))
    for cid in sorted(pool):
        if cid not in cats:
            err(f'FOOD_CAT_POOL has "{cid}", which is not in CATS')
        elif not exists(f'cats/{cid}/full.webp'):
            err(f'FOOD_CAT_POOL has "{cid}" but cats/{cid}/full.webp is missing (broken image at the food spot)')
    for cid in cats:
        if cid not in pool and not re.search(r'\bonly\s*:', cats[cid]) and exists(f'cats/{cid}/full.webp'):
            warn(f'cat {cid}: has full art but is not in FOOD_CAT_POOL, so it never eats at the food spot')

    # -- hug / tail overlays --
    for key in hug:
        cid, _, pose = key.partition('-')
        if cid not in cats:
            err(f'CAT_HUG {key}: cat "{cid}" is not in CATS')
        if not exists(f'cats/{cid}/{pose}-paws.webp'):
            err(f'CAT_HUG {key}: cats/{cid}/{pose}-paws.webp is missing')
    for key in tails:
        cid, _, pose = key.partition('-')
        if not exists(f'cats/{cid}/{pose}-tail.webp'):
            err(f'CAT_TAILS {key}: cats/{cid}/{pose}-tail.webp is missing')

    # -- day trips --
    trippable = [c for c in cats if not re.search(r'\bonly\s*:', cats[c])]
    for did in dests:
        for bg in (str_list(bg_variants[did]) if did in bg_variants else [did]):
            if not exists(f'polaroids/{bg}-bg.webp'):
                err(f'destination {did}: polaroids/{bg}-bg.webp is missing')
        if not exists(f'objects/tkt-{did}.webp'):
            err(f'destination {did}: ticket objects/tkt-{did}.webp is missing')
        if not exists(f'stamps/{did}.webp'):
            warn(f'destination {did}: stamps/{did}.webp is missing (stamp slot shows the "?" placeholder forever)')
    for key in trip_offset:
        if not exists(f'polaroids/{key}-bg.webp'):
            err(f'TRIP_OFFSET {key}: polaroids/{key}-bg.webp is missing')
    for cid in trippable:
        if cid not in selfies:
            err(f'cat {cid}: can go on trips but has no SELFIE_POSES entry')
            continue
        want = int(re.match(r'\d+', selfies[cid]).group())
        files = sorted(int(m.group(1)) for f in (YARD / 'polaroids').glob(f'{cid}-selfie*.webp')
                       if (m := re.search(r'selfie(\d+)$', f.stem)))
        for n in range(1, want + 1):
            if n not in files:
                err(f'SELFIE_POSES {cid}={want}: polaroids/{cid}-selfie{n}.webp is missing')
        if files and max(files) > want:
            warn(f'cat {cid}: polaroids/{cid}-selfie{max(files)}.webp exists but SELFIE_POSES says {want}, so it never gets picked')
    for cid in selfies:
        if cid not in cats:
            warn(f'SELFIE_POSES has "{cid}", which is not in CATS')

    # -- panoramas --
    pano_files = set(re.findall(r'file:\s*[\'"](scene/[^\'"]+)[\'"]', js))
    for rel in sorted(pano_files):
        if not exists(rel):
            err(f'PANO_SEASONS: {rel} is missing')

    # -- outputs nothing references --
    for f in sorted((YARD / 'scene').glob('*.webp')):
        rel = f'scene/{f.name}'
        if rel not in js:
            warn(f'{rel}: generated but not referenced anywhere in index.html (stray variant? safe to delete)')
    for f in sorted((YARD / 'objects').glob('*.webp')):
        stem = f.stem
        base = re.sub(r'-(front|water)$', '', stem)
        used = (base in items or base in overlay_names or re.search(rf'(?<![\w-]){re.escape(base)}(?![\w-])', js)
                or (base.startswith('tkt-') and base[4:] in dests))
        if not used:
            warn(f'objects/{f.name}: not an ITEMS entry and its name appears nowhere in index.html (unused art)')
    for f in sorted((YARD / 'polaroids').glob('*-selfie*.webp')):
        if f.stem.split('-selfie')[0] not in cats:
            warn(f'polaroids/{f.name}: no such cat in CATS')
    for f in sorted((YARD / 'stamps').glob('*.webp')):
        if f.stem not in dests:
            warn(f'stamps/{f.name}: no such destination in DESTINATIONS')

    for label, rows in (('ERROR', errors), ('WARN', warns)):
        for row in rows:
            log(f'{label}  {row}')
    log(f'art check: {len(errors)} error(s), {len(warns)} warning(s)')
    return len(errors)


if __name__ == '__main__':
    sys.exit(1 if run_checks(print) else 0)
