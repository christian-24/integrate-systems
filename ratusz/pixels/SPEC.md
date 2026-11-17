# Agent Quest pixel-art spec

Agent Quest is a top-down pixel-art RPG village drawn in a pane beside the Claude chat. Agents
(Claude sessions and their subagents) walk between buildings, each building standing for a kind of
work. The look to match: a cozy 16-bit fantasy RPG overworld seen from a 3/4 top-down angle,
like classic SNES/GBA Zelda or Stardew Valley — chunky readable shapes, a dark outline, 3-4 shades
per material, light from the upper left.

## File format

One JSON file per sprite in this folder, `pixels/<name>.json`:

```json
{
  "name": "library",
  "w": 48, "h": 48,
  "anchor": [24, 46],
  "palette": { "o": "#1b1b2a", "a": "#e8c170", "b": "#c3933f" },
  "frames": [
    [
      "......oooo......",
      "...."
    ]
  ]
}
```

- `frames` is a list of frames; each frame is exactly `h` strings of exactly `w` characters.
  Buildings and scenery usually have 1 frame; an animated sprite has 2 to 4 (played in order, about
  4 frames per second): smoke, flags, flames, water, a glowing window.
- `.` is transparent. Every other character must be a key of `palette` (any single letter or digit).
- `anchor` is the pixel that stands on the ground (bottom centre of the base, or the feet).
- Draw your own 1-2 pixel soft shadow on the ground with a dark semi-transparent colour key
  (e.g. `"s": "#00000055"`), since the engine draws none.
- No anti-aliasing, no gradients: flat pixels only.

## Shared palette

Use these colours (you may add at most 3 accents of your own per sprite):

| Use | Colours |
|---|---|
| outline | `#1b1b2a` |
| grass | `#8bc34a` `#6ea93b` `#4f8a2b` `#a9d65a` |
| pine | `#2e7d5b` `#1f5f45` `#14453a` `#3f9a6e` |
| dirt path | `#8a6a45` `#6e5233` `#a3825a` |
| thatch / straw | `#e8c170` `#c3933f` `#9a6b2a` `#f3dd9a` |
| wood | `#8a5a34` `#5e3b22` `#b07a4a` |
| blue stone (towers, castle) | `#4fa3c7` `#3a7fa0` `#28597a` `#8fd1e6` |
| grey stone | `#9b9384` `#6c665c` `#c4bdae` |
| red roof / banner | `#c8463a` `#8e2b25` `#e8735f` |
| plaster | `#efe2c6` `#cdb994` |
| window glow | `#ffd36b` `#ff9b3d` |
| magic | green `#6ee08a`, violet `#9a6ad8`, cyan `#7fe3ff` |
| shadow | `#00000055` |

## Sizes

- Buildings: 48x48 (castle and arena may be 64x48). Anchor at the bottom centre.
- Trees: pine 16x24, round tree 16x20. Bushes, rocks, flowers: 8x8 to 12x10.
- Characters: 12x16, anchor [6, 15].

## Check your work (required)

Run `node pixels/check.js pixels/<name>.json`. It validates the file and writes `pixels/preview/<name>.png`
(each pixel 8x, every frame side by side, on grass). Then look at that PNG with your Read tool and
improve the art until it reads clearly as what it should be at a glance. Iterate at least twice.
