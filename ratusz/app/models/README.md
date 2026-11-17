# Agent Quest 3D models: the contract

The village (`app/index.html`) is a three.js r160 scene of a fantasy island: a Hall of Progress in
the middle, one house per project around it, agents (small characters) walking about. It must run
smoothly in a browser pane: **performance first**, then beauty.

Look: a cozy, stylised low-poly fantasy village, like a polished indie game (think *Townscaper* or
*Ooblets*): soft rounded proportions, warm colours from `PALETTE` in `kit.js`, crisp silhouettes,
small charming details (flower boxes, lanterns, banners, barrels). Flat-shaded, no photo textures;
small canvas textures from `kit.canvasTexture` are fine for roof tiles, planks, stone and grass.

## Rules for every model file

- One file per model group in `app/models/`, an ES module: `import { THREE, mat, glow, PALETTE, placed, mergeByMaterial, shadowed, canvasTexture, rnd } from "./kit.js";`
- **Budget**: static parts merged with `mergeByMaterial` (one mesh per material). Only moving parts stay
  separate. Use `mat()`/`glow()` (cached materials); never `new MeshStandardMaterial` per instance.
  Keep low-poly: cylinders/cones ≤ 8 segments, spheres ≤ 10x8.
- Deterministic: use `rnd(i, seed)`, never `Math.random`.
- Units: 1 = about 1 m. The ground is y = 0; models stand on it, centred on x = z = 0, front facing +z.
- Export `preview(scene)` that adds every variant side by side (x spaced) and returns an optional
  `update(dt, t)` for animation. Open `http://127.0.0.1:4790/models/preview.html?model=<file name>`
  (optional `&view=top`, `&dist=30`) in the browser to see it; the top-left shows draw calls,
  triangles and fps. Look at it and improve it at least twice.

## The files and their exports

### `characters.js`
`createCharacter({ role, small })` → `{ group, setState(state), update(dt, t, moving) }`
- `role`: `"backend"` (rust red `#c8463a`), `"testers"` (teal `#2f9fa8`), `"marketing"` (violet `#9a6ad8`)
  tints the robe/cloak. `small: true` is a subagent: ~65% height, carries a glowing lantern.
- A chibi adventurer about 1.6 m tall (big head, small body): hood or pointed hat, cloak, staff with a
  glowing gem (session) or lantern (subagent). Separate meshes for head, body, both arms, both legs
  so they can animate. ≤ 12 meshes per character.
- `setState(s)`: `"working"`, `"waiting"`, `"resting"`, `"done"`.
- `update(dt, t, moving)` animates: **walk cycle** when `moving` (legs and arms swing, body bobs);
  when standing: `working` = a busy gesture (hammering / casting with the staff, gem pulses),
  `waiting` = idle breathing and looking around, `resting`/`done` = sitting down, head nodding (sleep).
- Preview: all three roles × session/subagent in a row, cycling through the states every 3 s and
  walking back and forth.

### `house.js`
`createHouse({ color, floors, seed })` → `{ group, windows, chimneyTop }`
- A project's house; `color` is the roof colour, `floors` 1–3 (bigger with more sessions), `seed` varies
  details. Front door on +z. Stone base, plaster walls with timber framing, a tiled roof (canvas
  texture), chimney, windows with frames and shutters, flower boxes, a lantern by the door, a small
  porch or bench. Level 3 can add a little tower or balcony.
- `windows`: the window pane meshes (their material must be a per-house `glow` clone the village can
  dim or brighten; give each house its own pane material). `chimneyTop`: a `THREE.Vector3` in the
  group's local space where smoke rises.
- ≤ 12 draw calls per house. Preview: floors 1, 2, 3 with three roof colours.

### `hall.js`
`createHall()` → `{ group, update(dt, t) }`
- The Hall of Progress in the middle of the village (~12 m tall): a grand guild hall with a clock
  tower and golden spire, stone base on a round plaza, banners, steps, lanterns, a small fountain or
  notice board. `update` sways the banners and turns the clock hands.
- ≤ 20 draw calls. Preview: the hall alone.

### `barracks.js` (new)
`createBarracks()` → `{ group, update(dt, t) }`
- Home of the backend agents: a long timber barracks with a shingled roof, a training yard with
  straw dummies and weapon racks, a campfire with flickering flames (animate in `update`), a banner
  with a hammer emblem, crates and a water trough. Footprint about 14 x 10 m, front on +z.
- ≤ 20 draw calls. Preview: the barracks alone.

### `guilds.js` (new)
Three guild halls, each `{ group, update(dt, t) }`, footprint about 11 x 9 m, front on +z, ≤ 18 draw calls each:
- `createTestersGuild()` — the testers' guild: an inspector's tower with a big brass magnifying lens,
  an alchemy lab with flasks, and a large status lamp. Also return `setStatus(s)` with `"pass"` (lamp
  glows green), `"fail"` (red), `"none"` (dim amber).
- `createTechAcademy()` — the academy of technologies: a scholarly library-observatory with a dome,
  bookshelves visible through arched windows, floating rune crystals and slowly turning brass gears
  (animate in `update`).
- `createMarketingHall()` — the heralds' house: a guild hall with a violet roof, a big notice board
  with parchment posters, long banners, a bell or horn tower, messenger birds on the ridge; banners
  sway in `update`.
- Preview: the three side by side.

### `treasury.js` (new)
`createTreasury()` → `{ group, update(dt, t), setWealth(level) }`
- The village treasury, home of the treasurer agents who track how much each project earns and
  costs: a sturdy stone counting-house with a vault door, a gold-trimmed roof, a balance-scale sign,
  stacked coin chests and sacks outside, a counting table with ledgers, guard lanterns.
- `setWealth(level)` 0..1: the visible pile of gold coins and chests outside grows (instanced coins),
  and a small gold glow on the roof finial brightens. `update` gives the coins a gentle glint.
- Footprint about 11 x 9 m, front on +z, ≤ 18 draw calls. Preview: wealth 0, 0.5 and 1 side by side.

### `estate.js` (new)
`createEstate({ color, floors, seed })` → `{ group, windows, chimneyTop, setGrowth(p), setLevel(n) }`
- A project's estate: `import { createHouse } from "./house.js"` for the house (keep its windows and
  chimneyTop), placed at the back; in front of it a fenced garden of about 8 x 6 m with crop rows,
  a small orchard tree, a scarecrow and a signpost, plus a gravel path to the gate on +z.
- `setGrowth(p)`, `p` 0..1 = the project's progress: the crops grow from bare soil and sprouts
  (p≈0) to full plants with flowers and fruit (p≈1); the orchard tree bears fruit above 0.6. Animate
  nothing per frame; growth only changes when it is called (scale/visibility of instanced plants).
- `setLevel(n)` 1..10: a level banner on a pole by the gate, taller and more golden at higher levels.
- ≤ 22 draw calls including the house. Preview: three estates at growth 0, 0.5, 1 and levels 1, 4, 9.

### `nature.js`
`createNature({ radius, keepClear })` → `{ group, update(dt, t) }`
- The island's ground and scenery for an island of `radius` (about 62): a grassy island with a
  canvas grass texture, sandy beach rim, rocky edge, animated sea around it (a few gentle waves,
  cheap), and scattered pine and round trees, bushes, rocks, flowers, grass tufts.
- `keepClear(x, z)` returns `true` where nothing may stand (houses, roads, plaza): skip those spots.
- **Use `THREE.InstancedMesh` for all repeated things** (one instanced mesh per tree part per
  material), so 200 trees cost a handful of draw calls. ≤ 25 draw calls in total.
- Preview: an island of radius 30 with `keepClear` clearing a cross-shaped road and a circle.
