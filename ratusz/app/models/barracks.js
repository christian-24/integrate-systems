// The backend barracks: long timber hall with shingled roof, training yard (straw dummies, weapon
// racks), campfire, hammer banner, crates and a water trough. Front faces +z.
import { THREE, mat, glow, PALETTE, placed, mergeByMaterial, canvasTexture, rnd } from "./kit.js";

const unit = new THREE.BoxGeometry(1, 1, 1);
const cyl8 = new THREE.CylinderGeometry(1, 1, 1, 8);
const cone8 = new THREE.ConeGeometry(1, 1, 8);
const sph = new THREE.SphereGeometry(1, 8, 6);

let shingleMat;
function shingles() {
  if (!shingleMat) {
    const map = canvasTexture("barracks-shingles", 64, (c, s) => {
      c.fillStyle = "#d8d8d8"; c.fillRect(0, 0, s, s);
      const rows = 8, rh = s / rows, cols = 6, cw = s / cols;
      for (let r = 0; r < rows; r++) for (let k = 0; k < cols + 1; k++) {
        const v = 195 + ((r * 5 + k * 11) % 4) * 14;
        c.fillStyle = `rgb(${v},${v},${v})`;
        c.fillRect(k * cw + (r % 2 ? cw / 2 : 0) - cw / 2, r * rh, cw - 1, rh - 1);
        c.strokeStyle = "rgba(40,25,15,0.6)"; c.lineWidth = 1.5;
        c.strokeRect(k * cw + (r % 2 ? cw / 2 : 0) - cw / 2, r * rh, cw - 1, rh - 1);
      }
    }, [5, 2]);
    shingleMat = new THREE.MeshStandardMaterial({ color: "#8a4a32", map, roughness: 0.9, flatShading: true });
  }
  return shingleMat;
}

export function createBarracks() {
  const M = {
    wood: mat(PALETTE.wood), dark: mat(PALETTE.woodDark), light: mat(PALETTE.woodLight),
    plaster: mat("#e4d3b0"), stone: mat(PALETTE.stone), stoneD: mat(PALETTE.stone),
    roof: shingles(), straw: mat("#d9b45a"), strawD: mat(PALETTE.wood),
    iron: mat(PALETTE.stone), red: mat(PALETTE.roofRed),
    water: mat("#4a9ac0", { roughness: 0.2 }), win: glow(PALETTE.window, 1.1), dirt: mat("#a98253"),
    leaf: mat(PALETTE.leaf),
  };
  const parts = [];
  const box = (m, w, h, d, o = {}) => parts.push([placed(unit, { ...o, sx: w, sy: h, sz: d }), m]);
  const cyl = (m, rx, h, rz, o = {}) => parts.push([placed(cyl8, { ...o, sx: rx, sy: h, sz: rz }), m]);

  // --- trodden yard ground (a flat disc-ish slab) ---
  box(M.dirt, 13.4, 0.06, 5.6, { y: 0.03, z: 2.3 });
  box(M.dirt, 12.4, 0.07, 4.8, { y: 0.035, z: 2.5, ry: 0.0 });

  // --- main hall: x -4.5..4.5, z -5..-0.4 ---
  const HX = 9.2, HD = 4.6, HZ = -2.9, BASE = 0.5, WH = 2.4;
  box(M.stone, HX + 0.3, BASE, HD + 0.3, { y: BASE / 2, z: HZ });
  box(M.plaster, HX, WH, HD, { y: BASE + WH / 2, z: HZ });
  // timber frame
  for (let i = 0; i <= 6; i++) {
    const x = -HX / 2 + (i * HX) / 6;
    box(M.dark, 0.2, WH + 0.1, 0.2, { x, y: BASE + WH / 2, z: HZ + HD / 2 });
    box(M.dark, 0.2, WH + 0.1, 0.2, { x, y: BASE + WH / 2, z: HZ - HD / 2 });
  }
  for (const y of [BASE + 0.05, BASE + WH - 0.1]) {
    box(M.dark, HX + 0.2, 0.2, 0.22, { y, z: HZ + HD / 2 });
    box(M.dark, HX + 0.2, 0.2, 0.22, { y, z: HZ - HD / 2 });
    for (const s of [-1, 1]) box(M.dark, 0.22, 0.2, HD + 0.2, { x: s * HX / 2, y, z: HZ });
  }
  for (const s of [-1, 1]) for (const k of [-1.3, 1.3]) box(M.dark, 0.2, WH + 0.1, 0.2, { x: s * HX / 2, y: BASE + WH / 2, z: HZ + k });
  // diagonal braces on front
  for (let i = 0; i < 6; i++) {
    if (i === 2 || i === 3) continue;
    const x = -HX / 2 + ((i + 0.5) * HX) / 6;
    box(M.dark, 0.1, 1.7, 0.08, { x, y: BASE + WH / 2, z: HZ + HD / 2 + 0.06, rz: i % 2 ? 0.6 : -0.6 });
  }
  // door (centre) with porch
  const fz = HZ + HD / 2;
  box(M.dark, 1.5, 2.0, 0.16, { y: BASE + 1.0, z: fz + 0.02 });
  box(M.wood, 1.2, 1.85, 0.14, { y: BASE + 0.93, z: fz + 0.08 });
  box(M.dark, 0.05, 1.85, 0.16, { y: BASE + 0.93, z: fz + 0.1 });
  for (const y of [BASE + 0.4, BASE + 1.4]) box(M.iron, 1.2, 0.08, 0.16, { y, z: fz + 0.1 });
  box(M.stone, 2.4, 0.2, 1.3, { y: 0.1, z: fz + 0.8 });
  for (const s of [-1, 1]) box(M.dark, 0.16, 2.7, 0.16, { x: s * 1.05, y: BASE + 1.2, z: fz + 1.3 });
  box(M.shingle ?? M.roof, 2.6, 0.12, 1.7, { y: BASE + 2.75, z: fz + 0.65, rx: 0.3 });
  // windows (front, four) with shutters
  for (const x of [-3.3, -1.9, 1.9, 3.3]) {
    box(M.win, 0.7, 0.8, 0.05, { x, y: BASE + 1.4, z: fz + 0.03 });
    box(M.dark, 0.86, 0.08, 0.1, { x, y: BASE + 1.84, z: fz + 0.05 });
    box(M.dark, 0.86, 0.08, 0.1, { x, y: BASE + 0.96, z: fz + 0.05 });
    box(M.dark, 0.06, 0.8, 0.1, { x, y: BASE + 1.4, z: fz + 0.05 });
    for (const s of [-1, 1]) box(M.red, 0.3, 0.9, 0.05, { x: x + s * 0.55, y: BASE + 1.4, z: fz + 0.06 });
  }
  // roof (ridge along x)
  const rh = 1.9, rw = HD / 2 + 0.55, ang = Math.atan2(rh, rw), L = Math.hypot(rw, rh) + 0.05, RX = HX + 1.0;
  const by = BASE + WH;
  for (const s of [-1, 1]) box(M.roof, RX, 0.16, L, { y: by + rh / 2 + 0.08, z: HZ + s * rw / 2, rx: s * ang });
  box(M.dark, RX + 0.1, 0.2, 0.22, { y: by + rh + 0.1, z: HZ });
  // gable triangles at the ends
  const tri = new THREE.Shape();
  tri.moveTo(-HD / 2, 0); tri.lineTo(HD / 2, 0); tri.lineTo(0, rh - 0.05); tri.closePath();
  const triG = new THREE.ExtrudeGeometry(tri, { depth: HX, bevelEnabled: false });
  parts.push([placed(triG, { x: -HX / 2, y: by - 0.02, z: HZ, ry: Math.PI / 2 }), M.plaster]);
  for (const s of [-1, 1]) {
    box(M.dark, 0.1, 0.14, HD, { x: s * (HX / 2 + 0.03), y: by, z: HZ });
    box(M.dark, 0.1, rh - 0.1, 0.12, { x: s * (HX / 2 + 0.03), y: by + rh / 2, z: HZ });
  }
  // chimney
  box(M.stone, 0.7, 2.4, 0.7, { x: -2.6, y: by + 1.5, z: HZ - 0.6 });
  box(M.stoneD, 0.9, 0.14, 0.9, { x: -2.6, y: by + 2.75, z: HZ - 0.6 });

  // --- banner pole (banner itself animated) at the right of the door ---
  cyl(M.dark, 0.07, 4.6, 0.07, { x: 5.4, y: 2.3, z: 0.4 });
  parts.push([placed(sph, { x: 5.4, y: 4.7, z: 0.4, sx: 0.12, sy: 0.12, sz: 0.12 }), M.straw]);
  box(M.dark, 1.3, 0.07, 0.07, { x: 6.0, y: 4.35, z: 0.4 });
  cyl(M.stoneD, 0.4, 0.3, 0.4, { x: 5.4, y: 0.15, z: 0.4 });

  // --- weapon racks (left of yard) ---
  const rack = (x, z, ry) => {
    const a = (m, w, h, d, o) => {
      const g = placed(unit, { ...o, sx: w, sy: h, sz: d });
      g.applyMatrix4(new THREE.Matrix4().makeRotationY(ry)); g.applyMatrix4(new THREE.Matrix4().makeTranslation(x, 0, z));
      parts.push([g, m]);
    };
    for (const s of [-1, 1]) a(M.dark, 0.12, 1.4, 0.12, { x: s * 0.9, y: 0.7 });
    a(M.dark, 2.0, 0.1, 0.12, { y: 1.35 }); a(M.dark, 2.0, 0.1, 0.12, { y: 0.55 });
    for (let i = 0; i < 4; i++) {
      const px = -0.65 + i * 0.43;
      a(M.light, 0.07, 1.5, 0.07, { x: px, y: 0.9, z: 0.1, rz: (i % 2) * 0.12 - 0.06 });   // spear/sword shaft
      a(M.iron, 0.12, 0.3, 0.05, { x: px, y: 1.72, z: 0.1 });
    }
    a(M.red, 0.5, 0.5, 0.06, { x: 0.45, y: 0.3, z: -0.1 });                      // shield leaning
    a(M.gold ?? M.straw, 0.14, 0.14, 0.08, { x: 0.45, y: 0.3, z: -0.06 });
  };
  rack(-5.2, 1.6, 0.4);
  rack(-4.0, 4.5, 0);

  // --- straw dummies ---
  const dummy = (x, z, ry) => {
    cyl(M.dark, 0.07, 1.6, 0.07, { x, y: 0.8, z });
    cyl(M.strawD, 0.3, 0.12, 0.3, { x, y: 0.06, z });
    parts.push([placed(cyl8, { x, y: 1.25, z, sx: 0.3, sy: 0.7, sz: 0.24, ry }), M.straw]);
    parts.push([placed(sph, { x, y: 1.85, z, sx: 0.23, sy: 0.23, sz: 0.23 }), M.straw]);
    parts.push([placed(unit, { x, y: 1.5, z, sx: 1.0, sy: 0.12, sz: 0.12, ry }), M.wood]);
    parts.push([placed(cone8, { x, y: 2.1, z, sx: 0.26, sy: 0.3, sz: 0.26 }), M.red]);
    parts.push([placed(unit, { x: x + 0.1 * Math.cos(ry), y: 1.25, z: z - 0.1 * Math.sin(ry), sx: 0.55, sy: 0.1, sz: 0.5, ry }), M.red]);
  };
  dummy(-1.4, 4.4, 0.3);
  dummy(1.2, 5.0, -0.4);
  dummy(3.4, 4.0, 0.1);

  // --- fire ring, log seats ---
  const FX = 2.6, FZ = 1.6;
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    parts.push([placed(sph, { x: FX + Math.cos(a) * 0.75, y: 0.15, z: FZ + Math.sin(a) * 0.75, sx: 0.22, sy: 0.17, sz: 0.22 }), M.stoneD]);
  }
  cyl(mat("#2a2420"), 0.6, 0.06, 0.6, { x: FX, y: 0.04, z: FZ });
  for (let i = 0; i < 3; i++) box(M.dark, 0.9, 0.12, 0.12, { x: FX, y: 0.16, z: FZ, ry: i * 1.05 });
  for (const [a, r] of [[0.9, 1.7], [3.2, 1.8], [5.0, 1.7]]) {
    cyl(M.wood, 0.2, 1.0, 0.2, { x: FX + Math.cos(a) * r, y: 0.2, z: FZ + Math.sin(a) * r, rz: Math.PI / 2, ry: -a });
  }

  // --- crates, barrels, trough ---
  box(M.light, 0.8, 0.8, 0.8, { x: 5.0, y: 0.4, z: -1.2, ry: 0.2 });
  box(M.light, 0.65, 0.65, 0.65, { x: 5.2, y: 0.33, z: -0.2, ry: -0.3 });
  box(M.light, 0.6, 0.6, 0.6, { x: 5.05, y: 1.1, z: -1.2, ry: 0.6 });
  for (const [x, z] of [[-5.2, -0.6], [-5.8, -1.3]]) {
    cyl(M.wood, 0.34, 0.8, 0.34, { x, y: 0.4, z });
    cyl(M.dark, 0.35, 0.06, 0.35, { x, y: 0.28, z }); cyl(M.dark, 0.35, 0.06, 0.35, { x, y: 0.62, z });
  }
  // hay bales and a lantern post
  for (const [x, z, r] of [[-6.0, 3.0, 0.3], [-6.1, 4.1, -0.2]]) {
    cyl(M.straw, 0.5, 0.7, 0.5, { x, y: 0.35, z, rz: Math.PI / 2, ry: r });
  }
  cyl(M.dark, 0.06, 2.4, 0.06, { x: 0.0, y: 1.2, z: 5.0 });
  box(M.dark, 0.5, 0.05, 0.05, { x: 0.2, y: 2.35, z: 5.0 });
  box(M.win, 0.2, 0.28, 0.2, { x: 0.4, y: 2.18, z: 5.0 });
  // trough
  box(M.wood, 2.0, 0.5, 0.7, { x: 5.0, y: 0.25, z: 3.6 });
  box(M.water, 1.8, 0.05, 0.5, { x: 5.0, y: 0.5, z: 3.6 });
  for (const s of [-1, 1]) box(M.dark, 0.1, 0.55, 0.8, { x: 5.0 + s * 0.95, y: 0.27, z: 3.6 });
  // fence posts along yard front
  for (let i = 0; i < 9; i++) {
    const x = -6.4 + i * 1.6;
    if (i >= 3 && i <= 5) continue;
    cyl(M.dark, 0.08, 0.8, 0.08, { x, y: 0.4, z: 5.6 });
    box(M.wood, 1.5, 0.08, 0.06, { x: x + 0.8, y: 0.62, z: 5.6 });
  }
  // bushes by the hall
  for (const [x, z, s] of [[-5.0, -0.2, 0.4], [4.9, 1.1, 0.35]]) parts.push([placed(sph, { x, y: s * 0.7, z, sx: s, sy: s * 0.85, sz: s }), M.leaf]);

  const group = mergeByMaterial(parts);

  // --- animated: flames + banner ---
  const flameMat = glow("#ff5a10", 1.3), flameIn = flameMat;
  const flames = [];
  for (let i = 0; i < 2; i++) {
    const f = new THREE.Mesh(cone8, i === 0 ? flameIn : flameMat);
    const a = i * 3.1; f.position.set(FX + Math.cos(a) * 0.12, 0.45, FZ + Math.sin(a) * 0.12);
    const h = i === 0 ? 1.4 : 1.0;
    f.userData = { h, i }; f.scale.set(0.4, h, 0.4); flames.push(f); group.add(f);
  }

  const bannerGeo = new THREE.PlaneGeometry(1.1, 2.2, 4, 8);
  const bannerMat = new THREE.MeshStandardMaterial({
    side: THREE.DoubleSide, roughness: 0.9,
    map: canvasTexture("barracks-banner", 64, (c, s) => {
      c.fillStyle = "#c8463a"; c.fillRect(0, 0, s, s);
      c.fillStyle = "#e2b347"; c.fillRect(0, 0, s, 5); c.fillRect(0, s - 5, s, 5);
      c.fillRect(s * 0.18, s * 0.2, s * 0.64, s * 0.2);          // hammer head
      c.fillRect(s * 0.45, s * 0.2, s * 0.1, s * 0.62);         // handle
    }),
  });
  const banner = new THREE.Mesh(bannerGeo, bannerMat);
  banner.position.set(6.0, 3.2, 0.4); banner.castShadow = true;
  group.add(banner);
  const base = bannerGeo.attributes.position.array.slice();

  function update(dt, t) {
    for (const f of flames) {
      const { h, i } = f.userData;
      const k = 1 + 0.25 * Math.sin(t * 11 + i * 2) + 0.12 * Math.sin(t * 23 + i);
      f.scale.set(0.38 + 0.06 * Math.sin(t * 9 + i), h * k, 0.38 + 0.06 * Math.cos(t * 8 + i));
      f.position.y = 0.2 + f.scale.y / 2;
      f.rotation.y = t * 2 + i;
    }
    const p = bannerGeo.attributes.position;
    for (let n = 0; n < p.count; n++) {
      const x = base[n * 3], y = base[n * 3 + 1];
      const amp = (x + 0.55) * 0.18;
      p.setZ(n, Math.sin(t * 2.4 + y * 1.5 + x * 2) * amp);
    }
    p.needsUpdate = true;
  }
  update(0, 0);
  return { group, update };
}

export function preview(scene) {
  const { group, update } = createBarracks();
  scene.add(group);
  return update;
}
