// Cozy fantasy cottages: stone base, plaster + timber walls, tiled roof, chimney, shuttered windows,
// flower boxes, lantern, porch and bench. Level 3 gets a little corner tower.
import { THREE, mat, glow, PALETTE, placed, mergeByMaterial, canvasTexture, rnd } from "./kit.js";

const FH = 2.3;      // floor height
const BASE = 0.5;    // stone base height
const W = 5.2, D = 4.2;

const unit = new THREE.BoxGeometry(1, 1, 1);

// ---------- roof material: one cached material per colour, shared tile texture ----------
const roofMats = new Map();
function roofMat(color) {
  if (!roofMats.has(color)) {
    const map = canvasTexture("roof-tiles", 64, (c, s) => {
      c.fillStyle = "#e6e6e6"; c.fillRect(0, 0, s, s);
      const rows = 4, rh = s / rows, cols = 4, cw = s / cols;
      for (let r = 0; r < rows; r++) {
        for (let k = -1; k < cols + 1; k++) {
          const cx = k * cw + (r % 2 ? cw / 2 : 0) + cw / 2, cy = r * rh;
          const v = 205 + ((r * 7 + k * 13) % 4) * 14;
          c.fillStyle = `rgb(${v},${v},${v})`;
          c.beginPath(); c.moveTo(cx - cw / 2, cy); c.lineTo(cx + cw / 2, cy); c.lineTo(cx + cw / 2, cy + rh * 0.55);
          c.arc(cx, cy + rh * 0.55, cw / 2, 0, Math.PI, false); c.closePath(); c.fill();
          c.strokeStyle = "rgba(60,40,40,0.55)"; c.lineWidth = 2; c.stroke();
        }
      }
    }, [3, 4]);
    roofMats.set(color, new THREE.MeshStandardMaterial({ color, map, roughness: 0.8, flatShading: true }));
  }
  return roofMats.get(color);
}

/** Box adder with an outer transform (translate + rotate around Y), so walls can share window code. */
function adder(parts, outer = {}) {
  const M = new THREE.Matrix4().compose(
    new THREE.Vector3(outer.x || 0, outer.y || 0, outer.z || 0),
    new THREE.Quaternion().setFromEuler(new THREE.Euler(0, outer.ry || 0, 0)),
    new THREE.Vector3(1, 1, 1));
  return (m, w, h, d, o = {}) => {
    const g = placed(unit, { ...o, sx: w, sy: h, sz: d });
    g.applyMatrix4(M); parts.push([g, m]);
  };
}

/** A framed window with shutters, sill and optional flower box. Local: wall surface at z = 0, facing +z. */
function win(add, M, x, y, w, h, o = {}) {
  const t = 0.07;
  add(M.pane, w, h, 0.05, { x, y, z: 0.02 });
  add(M.dark, w + 2 * t, t, 0.12, { x, y: y + h / 2 + t / 2, z: 0.04 });
  add(M.dark, w + 2 * t, t, 0.12, { x, y: y - h / 2 - t / 2, z: 0.04 });
  add(M.dark, t, h, 0.12, { x: x - w / 2 - t / 2, y, z: 0.04 });
  add(M.dark, t, h, 0.12, { x: x + w / 2 + t / 2, y, z: 0.04 });
  add(M.dark, 0.04, h, 0.07, { x, y, z: 0.05 });
  add(M.dark, w, 0.04, 0.07, { x, y, z: 0.05 });
  add(M.stone, w + 0.34, 0.08, 0.24, { x, y: y - h / 2 - t - 0.04, z: 0.1 });
  if (o.shutters !== false) {
    const sw = w * 0.45;
    for (const s of [-1, 1]) {
      add(M.shut, sw, h + 0.14, 0.05, { x: x + s * (w / 2 + t + sw / 2), y, z: 0.05 });
      add(M.dark, sw * 0.6, 0.03, 0.06, { x: x + s * (w / 2 + t + sw / 2), y, z: 0.07 });
    }
  }
  if (o.box) {
    const by = y - h / 2 - 0.26, bw = w + 0.2;
    add(M.wood, bw, 0.2, 0.28, { x, y: by, z: 0.22 });
    add(M.leaf, bw - 0.04, 0.12, 0.24, { x, y: by + 0.14, z: 0.22 });
    for (let i = 0; i < 5; i++)
      add((i + (o.flip ? 1 : 0)) % 2 ? M.fl1 : M.fl2, 0.1, 0.1, 0.1, { x: x - bw / 2 + 0.1 + i * (bw - 0.2) / 4, y: by + 0.24 + (i % 2) * 0.04, z: 0.22, ry: i });
  }
}

export function createHouse({ color = PALETTE.roofRed, floors = 1, seed = 1 } = {}) {
  floors = Math.max(1, Math.min(3, floors | 0));
  const r = i => rnd(i, seed);
  const baseY = BASE + floors * FH;       // eave height
  const shutterCols = ["#3f7f6a", "#4a6fa5", "#a8483c", "#6a8a3a", "#8a5a9a"];
  const paneMat = glow(PALETTE.window, 1.1).clone();
  const M = {
    pane: paneMat,
    dark: mat(PALETTE.woodDark), wood: mat(PALETTE.wood),
    plaster: mat(r(1) > 0.5 ? PALETTE.plaster : "#f3e8d0"),
    stone: mat(PALETTE.stone), roof: roofMat(color), leaf: mat(PALETTE.leaf),
    fl1: mat(r(2) > 0.5 ? "#e8657a" : "#f08a4b"), fl2: mat("#f4d03f"),
    shut: mat(shutterCols[Math.floor(r(3) * shutterCols.length)]),
    lant: glow("#ffcf6a", 1.6),
  };
  const parts = [];
  const add = adder(parts);
  const benchSide = r(4) > 0.5 ? 1 : -1;
  const chimSide = floors === 3 ? 1 : (r(5) > 0.5 ? 1 : -1);

  // --- stone base, walls ---
  add(M.stone, W + 0.24, BASE, D + 0.24, { y: BASE / 2 });
  add(M.stone, W + 0.4, 0.12, D + 0.4, { y: 0.06 });
  add(M.plaster, W, floors * FH, D, { y: BASE + floors * FH / 2 });

  // --- timber frame: corner posts, floor beams ---
  for (const sx of [-1, 1]) for (const sz of [-1, 1])
    add(M.dark, 0.24, floors * FH + 0.1, 0.24, { x: sx * W / 2, y: BASE + floors * FH / 2, z: sz * D / 2 });
  for (let i = 1; i <= floors; i++) {
    const y = BASE + i * FH - 0.07;
    for (const sz of [-1, 1]) add(M.dark, W + 0.2, 0.16, 0.12, { y, z: sz * D / 2 });
    for (const sx of [-1, 1]) add(M.dark, 0.12, 0.16, D + 0.2, { x: sx * W / 2, y });
  }
  // side + back braces and mid posts
  for (let i = 0; i < floors; i++) {
    const y = BASE + i * FH + FH / 2;
    for (const s of [-1, 1]) {
      const a = adder(parts, { x: s * W / 2, ry: s * Math.PI / 2 });
      for (const bx of [-1.45, 1.45]) add_brace(a, bx, y, bx > 0 ? 0.55 : -0.55);
    }
    const a = adder(parts, { z: -D / 2, ry: Math.PI });
    for (const bx of [-1.85, 1.85]) add_brace(a, bx, y, bx > 0 ? 0.55 : -0.55);
  }
  function add_brace(a, bx, y, rz) { a(M.dark, 0.1, 1.55, 0.07, { x: bx, y, z: 0.03, rz }); }

  // --- windows ---
  const front = adder(parts, { z: D / 2 });
  for (let i = 0; i < floors; i++) {
    const y = BASE + i * FH + 1.35;
    const xs = i === 0 ? [-1.7, 1.7] : [-1.7, 0, 1.7];
    xs.forEach(x => {
      const benchHere = i === 0 && Math.sign(x) === benchSide;
      win(front, M, x, y, 0.8, 1.0, { box: !benchHere, flip: x > 0 });
    });
    for (const s of [-1, 1]) win(adder(parts, { x: s * W / 2, ry: s * Math.PI / 2 }), M, 0, y, 0.8, 1.0, { box: i === 0 && r(6 + s) > 0.4 });
    win(adder(parts, { z: -D / 2, ry: Math.PI }), M, 0, y, 0.8, 1.0, { box: false });
  }

  // --- door, porch, steps, lantern, bench ---
  add(M.dark, 1.34, 2.0, 0.16, { y: BASE + 1.0, z: D / 2 });
  front(M.wood, 1.02, 1.86, 0.12, { y: BASE + 0.93, z: 0.05 });
  for (const x of [-0.25, 0.25]) front(M.dark, 0.04, 1.8, 0.14, { x, y: BASE + 0.93, z: 0.06 });
  front(M.dark, 1.0, 0.07, 0.14, { y: BASE + 1.2, z: 0.06 });
  front(M.pane, 0.4, 0.3, 0.05, { y: BASE + 1.45, z: 0.13 });
  front(M.dark, 0.1, 0.1, 0.1, { x: 0.35, y: BASE + 0.95, z: 0.14 });
  front(M.stone, 1.9, 0.12, 0.2, { y: BASE + 2.06, z: 0.04 });          // lintel
  front(M.stone, 1.9, 0.4, 0.95, { y: 0.2, z: 0.55 });                 // step
  front(M.stone, 1.4, 0.18, 0.5, { y: 0.09, z: 1.2 });
  for (const s of [-1, 1]) front(M.dark, 0.14, 2.7, 0.14, { x: s * 0.82, y: BASE + 1.2, z: 1.25 });
  front(M.roof, 2.0, 0.1, 1.6, { y: BASE + 2.8, z: 0.8, rx: 0.32 });
  front(M.dark, 2.0, 0.1, 0.1, { y: BASE + 2.55, z: 1.5 });
  // lantern on a bracket
  front(M.dark, 0.06, 0.06, 0.34, { x: -0.95, y: BASE + 2.0, z: 0.2 });
  front(M.dark, 0.03, 0.14, 0.03, { x: -0.95, y: BASE + 1.9, z: 0.34 });
  front(M.lant, 0.2, 0.28, 0.2, { x: -0.95, y: BASE + 1.7, z: 0.34 });
  front(M.dark, 0.26, 0.05, 0.26, { x: -0.95, y: BASE + 1.87, z: 0.34 });
  // bench + barrel
  const bx = benchSide * 1.7;
  front(M.wood, 1.3, 0.08, 0.42, { x: bx, y: 0.5, z: 0.55 });
  front(M.wood, 1.3, 0.34, 0.06, { x: bx, y: 0.85, z: 0.38, rx: -0.15 });
  for (const s of [-1, 1]) front(M.dark, 0.08, 0.5, 0.36, { x: bx + s * 0.55, y: 0.25, z: 0.55 });
  const barrel = placed(new THREE.CylinderGeometry(0.28, 0.24, 0.6, 8), { x: -benchSide * 2.45, y: 0.3, z: D / 2 + 0.5 });
  parts.push([barrel, M.wood]);
  parts.push([placed(new THREE.CylinderGeometry(0.29, 0.29, 0.05, 8), { x: -benchSide * 2.45, y: 0.5, z: D / 2 + 0.5 }), M.dark]);
  // bushes
  for (const [bx2, bz, s] of [[W / 2 + 0.3, D / 2 + 0.3, 0.38], [-W / 2 - 0.3, D / 2 + 0.2, 0.3], [W / 2 + 0.25, -D / 2 - 0.1, 0.34]]) {
    parts.push([placed(new THREE.SphereGeometry(s, 8, 6), { x: bx2, y: s * 0.7, z: bz, sy: 0.85 }), M.leaf]);
    add(r(bx2) > 0.5 ? M.fl1 : M.fl2, 0.1, 0.1, 0.1, { x: bx2 + 0.12, y: s * 1.2, z: bz + 0.2 });
  }

  // --- roof ---
  const h = 1.75, hw = W / 2 + 0.4, ang = Math.atan2(h, hw), L = Math.hypot(hw, h) + 0.08, RD = D + 0.8;
  for (const s of [-1, 1]) add(M.roof, L, 0.16, RD, { x: s * hw / 2, y: baseY + h / 2 + 0.08, rz: -s * ang });
  add(M.dark, 0.2, 0.18, RD + 0.05, { y: baseY + h + 0.14 });
  // gable triangles (plaster) front and back
  const shape = new THREE.Shape();
  shape.moveTo(-W / 2 - 0.04, 0); shape.lineTo(W / 2 + 0.04, 0); shape.lineTo(0, h - 0.05); shape.closePath();
  const tri = new THREE.ExtrudeGeometry(shape, { depth: D, bevelEnabled: false });
  parts.push([placed(tri, { y: baseY - 0.02, z: -D / 2 }), M.plaster]);
  for (const sz of [-1, 1]) {
    const a = adder(parts, { z: sz * D / 2, ry: sz < 0 ? Math.PI : 0 });
    for (const s of [-1, 1]) a(M.dark, Math.hypot(W / 2, h) - 0.1, 0.12, 0.1, { x: s * W / 4, y: h / 2 + baseY - 0.05, z: 0.04, rz: -s * Math.atan2(h, W / 2) });
    a(M.dark, 0.1, h - 0.2, 0.1, { y: baseY + h / 2 - 0.12, z: 0.04 });
    a(M.dark, W, 0.14, 0.1, { y: baseY, z: 0.04 });
    // diamond attic window
    a(M.dark, 0.62, 0.62, 0.1, { y: baseY + 0.7, z: 0.05, rz: Math.PI / 4 });
    a(M.pane, 0.46, 0.46, 0.06, { y: baseY + 0.7, z: 0.08, rz: Math.PI / 4 });
  }

  // --- chimney ---
  const cx = chimSide * 1.35, cz = -0.2, ctop = baseY + h + 0.75;
  add(M.stone, 0.7, ctop - baseY + 0.6, 0.7, { x: cx, y: (ctop + baseY - 0.6) / 2, z: cz });
  add(M.dark, 0.88, 0.12, 0.88, { x: cx, y: ctop + 0.06, z: cz });
  add(M.stone, 0.62, 0.1, 0.62, { x: cx, y: ctop + 0.17, z: cz });
  const chimneyTop = new THREE.Vector3(cx, ctop + 0.3, cz);

  // --- level 3: corner tower ---
  if (floors === 3) {
    const tx = -W / 2 - 0.1, tz = -D / 2 + 0.2, ts = 1.7, top = baseY + 2.0;
    add(M.stone, ts + 0.24, BASE, ts + 0.24, { x: tx, y: BASE / 2, z: tz });
    add(M.plaster, ts, top - BASE, ts, { x: tx, y: (top + BASE) / 2, z: tz });
    for (const sx of [-1, 1]) for (const sz of [-1, 1])
      add(M.dark, 0.2, top - BASE, 0.2, { x: tx + sx * ts / 2, y: (top + BASE) / 2, z: tz + sz * ts / 2 });
    for (const y of [baseY - 0.9, top - 0.05]) add(M.dark, ts + 0.3, 0.14, ts + 0.3, { x: tx, y, z: tz });
    for (const y of [BASE + 1.7, baseY + 1.05]) {
      win(adder(parts, { x: tx, z: tz + ts / 2 }), M, 0, y, 0.55, 0.8);
      win(adder(parts, { x: tx - ts / 2, z: tz, ry: -Math.PI / 2 }), M, 0, y, 0.55, 0.8);
    }
    win(adder(parts, { x: tx, z: tz + ts / 2 }), M, 0, baseY - 0.2 - 1.5 + 0.2, 0.55, 0.8);
    parts.push([placed(new THREE.ConeGeometry(1.4, 1.9, 8), { x: tx, y: top + 0.95, z: tz, ry: Math.PI / 8 }), M.roof]);
    add(M.dark, 0.06, 0.8, 0.06, { x: tx, y: top + 2.2, z: tz });
    add(M.fl1, 0.45, 0.22, 0.03, { x: tx + 0.25, y: top + 2.45, z: tz });
  }

  const group = mergeByMaterial(parts);
  const windows = group.children.filter(m => m.material === paneMat);
  group.userData.roofColor = color;
  return { group, windows, chimneyTop };
}

export function preview(scene) {
  const specs = [
    { color: PALETTE.roofRed, floors: 1, seed: 3 },
    { color: PALETTE.roofBlue, floors: 2, seed: 7 },
    { color: PALETTE.roofTeal, floors: 3, seed: 11 },
  ];
  specs.forEach((s, i) => {
    const { group } = createHouse(s);
    group.position.x = (i - 1) * 10;
    scene.add(group);
  });
}
