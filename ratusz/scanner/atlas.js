// Gathers the pixel sprites (pixels/*.json) into one file, pixels/atlas.json, for the mod to read.
// The pane strips href from SVG, so the mod draws these pixels as vector paths, never as images.
// Rebuilt only when a sprite file is newer than the atlas.

const fs = require("fs");
const path = require("path");

const DIR = path.join(__dirname, "..", "pixels");
const OUT = path.join(DIR, "atlas.json");

function ensureAtlas() {
  const files = fs.readdirSync(DIR).filter(f => f.endsWith(".json") && f !== "atlas.json");
  const newest = Math.max(0, ...files.map(f => fs.statSync(path.join(DIR, f)).mtimeMs));
  const current = fs.existsSync(OUT) ? fs.statSync(OUT).mtimeMs : 0;
  if (current >= newest && current > 0) return Math.round(current);
  const atlas = {};
  for (const f of files) {
    let sp; try { sp = JSON.parse(fs.readFileSync(path.join(DIR, f), "utf8")); } catch { continue; }
    if (!sp.frames || !sp.palette) continue;
    atlas[f.slice(0, -5)] = { w: sp.w, h: sp.h, anchor: sp.anchor, palette: sp.palette, frames: sp.frames };
  }
  const tmp = OUT + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(atlas));
  fs.renameSync(tmp, OUT);
  return Math.round(fs.statSync(OUT).mtimeMs);
}

module.exports = { ensureAtlas };
if (require.main === module) console.log("atlas version", ensureAtlas());
