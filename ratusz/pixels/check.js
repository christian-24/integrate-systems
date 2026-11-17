// Validates a pixel sprite JSON file and writes an 8x preview PNG of all its frames.
// Usage: node pixels/check.js pixels/<name>.json
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const file = process.argv[2];
if (!file) { console.error("usage: node pixels/check.js pixels/<name>.json"); process.exit(2); }
const sp = JSON.parse(fs.readFileSync(file, "utf8"));
const errors = [];
if (!Number.isInteger(sp.w) || !Number.isInteger(sp.h)) errors.push("w and h must be integers");
if (!Array.isArray(sp.frames) || !sp.frames.length) errors.push("frames must be a non-empty list");
if (!Array.isArray(sp.anchor) || sp.anchor.length !== 2) errors.push("anchor must be [x, y]");
for (const [k, v] of Object.entries(sp.palette || {})) {
  if (k.length !== 1 || k === ".") errors.push(`palette key "${k}" must be one character, not "."`);
  if (!/^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(v)) errors.push(`palette "${k}": "${v}" is not #rrggbb or #rrggbbaa`);
}
(sp.frames || []).forEach((rows, f) => {
  if (rows.length !== sp.h) errors.push(`frame ${f}: ${rows.length} rows, expected ${sp.h}`);
  rows.forEach((r, y) => {
    if (r.length !== sp.w) errors.push(`frame ${f} row ${y}: ${r.length} chars, expected ${sp.w}`);
    for (const c of r) if (c !== "." && !(c in sp.palette)) { errors.push(`frame ${f} row ${y}: "${c}" is not in the palette`); break; }
  });
});
if (errors.length) { console.error(errors.slice(0, 30).join("\n")); process.exit(1); }

// Render: frames side by side with a 4px gap, on grass, 8x.
const S = 8, gap = 4, W = (sp.w * sp.frames.length + gap * (sp.frames.length + 1)) * S, H = (sp.h + gap * 2) * S;
const px = Buffer.alloc(W * H * 4);
const hex = h => [1, 3, 5, 7].map(i => parseInt(h.slice(i, i + 2) || "ff", 16));
const set = (x, y, [r, g, b, a]) => {
  const i = (y * W + x) * 4, al = a / 255;
  px[i] = Math.round(r * al + px[i] * (1 - al)); px[i + 1] = Math.round(g * al + px[i + 1] * (1 - al)); px[i + 2] = Math.round(b * al + px[i + 2] * (1 - al)); px[i + 3] = 255;
};
for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) set(x, y, ((x >> 4) + (y >> 4)) % 2 ? [139, 195, 74, 255] : [130, 186, 68, 255]);
sp.frames.forEach((rows, f) => {
  const ox = gap + f * (sp.w + gap), oy = gap;
  rows.forEach((r, y) => [...r].forEach((c, x) => {
    if (c === ".") return;
    const col = hex(sp.palette[c]);
    for (let dy = 0; dy < S; dy++) for (let dx = 0; dx < S; dx++) set((ox + x) * S + dx, (oy + y) * S + dy, col);
  }));
  // anchor marker
  const ax = (ox + sp.anchor[0]) * S + S / 2, ay = (oy + sp.anchor[1]) * S + S / 2;
  for (let d = -6; d <= 6; d++) { set(ax + d, ay, [255, 0, 255, 255]); set(ax, ay + d, [255, 0, 255, 255]); }
});

// Minimal PNG encoder.
const crcTable = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
const crc = b => { let c = 0xffffffff; for (const x of b) c = crcTable[(c ^ x) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
const chunk = (type, data) => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type), data]); const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([len, td, c]); };
const raw = Buffer.alloc((W * 4 + 1) * H);
for (let y = 0; y < H; y++) { raw[y * (W * 4 + 1)] = 0; px.copy(raw, y * (W * 4 + 1) + 1, y * W * 4, (y + 1) * W * 4); }
const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4); ihdr[8] = 8; ihdr[9] = 6;
const png = Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ihdr), chunk("IDAT", zlib.deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
const out = path.join(path.dirname(file), "preview", path.basename(file, ".json") + ".png");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, png);
console.log(`ok: ${sp.name || path.basename(file)} ${sp.w}x${sp.h}, ${sp.frames.length} frame(s) -> ${out}`);
