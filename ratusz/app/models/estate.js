// A project's estate: a cottage at the back, a fenced garden in front whose crops grow with the
// project's progress (setGrowth 0..1), an orchard tree, scarecrow, signpost and a level banner (setLevel 1..10).
// Crops, tree canopy, flowers and fruit are InstancedMeshes: growth only rewrites instance matrices.
import { THREE, mat, PALETTE, placed, mergeByMaterial, rnd } from "./kit.js";
import { createHouse } from "./house.js";

const HOUSE_Z = -6;
const GX = 4, GZ0 = -1.6, GZ1 = 4.5;       // garden half-width, back and front fence lines
const BANNER = { x: -1.5, z: 4.95 };
const TREE = { x: -3.2, z: -0.7 };
const clamp01 = v => Math.max(0, Math.min(1, v));
const smooth = v => { v = clamp01(v); return v * v * (3 - 2 * v); };

const box = new THREE.BoxGeometry(1, 1, 1);
const ico = new THREE.IcosahedronGeometry(1, 0);

export function createEstate({ color = PALETTE.roofRed, floors = 1, seed = 1 } = {}) {
  const group = new THREE.Group();
  const house = createHouse({ color, floors, seed });
  house.group.position.z = HOUSE_Z;
  group.add(house.group);

  const M = {
    wood: mat(PALETTE.wood), dark: mat(PALETTE.woodDark), soil: mat("#6b4a2e"),
    gravel: mat("#cdbf9f"), straw: mat(PALETTE.roofThatch), shirt: mat(PALETTE.roofBlue),
    white: mat("#ffffff"),
  };
  const parts = [];
  const add = (m, w, h, d, o = {}) => parts.push([placed(box, { ...o, sx: w, sy: h, sz: d }), m]);

  // ---------- gravel path (gate to the porch), edged with soil ----------
  const pz0 = HOUSE_Z + 3.7, pz1 = GZ1 + 0.9;
  add(M.gravel, 1.2, 0.05, pz1 - pz0, { y: 0.025, z: (pz0 + pz1) / 2 });
  for (const s of [-1, 1]) add(M.soil, 0.12, 0.08, pz1 - pz0, { x: s * 0.66, y: 0.04, z: (pz0 + pz1) / 2 });
  for (let i = 0; i < 9; i++)       // lighter flagstones scattered on the path
    add(M.straw, 0.28 + rnd(i, seed) * 0.2, 0.02, 0.22 + rnd(i + 9, seed) * 0.15,
      { x: (rnd(i + 20, seed) - 0.5) * 0.7, y: 0.055, z: pz0 + 0.5 + i * (pz1 - pz0 - 1) / 9, ry: rnd(i + 5, seed) * 3 });

  // ---------- fence with a gate arch ----------
  const post = (x, z, h = 0.95) => add(M.wood, 0.11, h, 0.11, { x, y: h / 2, z });
  const rails = (x0, z0, x1, z1) => {
    const len = Math.hypot(x1 - x0, z1 - z0), ang = -Math.atan2(z1 - z0, x1 - x0);
    for (const y of [0.35, 0.72]) add(M.wood, len, 0.07, 0.05, { x: (x0 + x1) / 2, y, z: (z0 + z1) / 2, ry: ang });
    const n = Math.max(1, Math.round(len));
    for (let i = 0; i <= n; i++) post(x0 + (x1 - x0) * i / n, z0 + (z1 - z0) * i / n);
  };
  rails(-GX, GZ1, -0.75, GZ1); rails(0.75, GZ1, GX, GZ1);
  rails(-GX, GZ0, -0.75, GZ0); rails(0.75, GZ0, GX, GZ0);
  rails(-GX, GZ0, -GX, GZ1); rails(GX, GZ0, GX, GZ1);
  for (const s of [-1, 1]) {
    post(s * 0.75, GZ1, 1.5); add(M.straw, 0.17, 0.17, 0.17, { x: s * 0.75, y: 1.58, z: GZ1 });
  }
  add(M.dark, 1.7, 0.1, 0.12, { y: 1.4, z: GZ1 });
  add(M.dark, 0.1, 0.35, 0.1, { y: 1.62, z: GZ1 });

  // ---------- soil beds ----------
  const rowX = [1.4, 2.2, 3.0];
  for (const s of [-1, 1]) for (const rx of rowX)
    add(M.soil, 0.62, 0.16, 4.1, { x: s * rx, y: 0.08, z: 2.15 });
  add(M.soil, 7.7, 0.03, 6.0, { y: 0.015, z: (GZ0 + GZ1) / 2 }); // dark tilled ground under everything

  // ---------- orchard tree trunk ----------
  parts.push([placed(new THREE.CylinderGeometry(0.15, 0.22, 1.7, 7), { x: TREE.x, y: 0.85, z: TREE.z }), M.wood]);
  for (const [bx, bz, rz] of [[0.35, 0.1, -0.7], [-0.3, -0.2, 0.7]])
    parts.push([placed(new THREE.CylinderGeometry(0.06, 0.1, 0.8, 5), { x: TREE.x + bx, y: 1.8, z: TREE.z + bz, rz }), M.wood]);

  // ---------- scarecrow ----------
  const SX = 3.3, SZ = -0.7;
  add(M.wood, 0.1, 1.9, 0.1, { x: SX, y: 0.95, z: SZ });
  add(M.wood, 1.5, 0.08, 0.08, { x: SX, y: 1.35, z: SZ });
  add(M.shirt, 0.5, 0.65, 0.3, { x: SX, y: 1.2, z: SZ });
  for (const s of [-1, 1]) {
    add(M.straw, 0.22, 0.12, 0.12, { x: SX + s * 0.8, y: 1.3, z: SZ });
    add(M.straw, 0.1, 0.35, 0.1, { x: SX + s * 0.2, y: 0.75, z: SZ });
  }
  parts.push([placed(new THREE.IcosahedronGeometry(0.22, 0), { x: SX, y: 1.8, z: SZ }), M.straw]);
  parts.push([placed(new THREE.ConeGeometry(0.34, 0.4, 7), { x: SX, y: 2.12, z: SZ }), M.dark]);
  add(M.dark, 0.7, 0.05, 0.7, { x: SX, y: 1.95, z: SZ });

  // ---------- signpost beside the gate ----------
  add(M.wood, 0.1, 1.5, 0.1, { x: 1.55, y: 0.75, z: 4.95 });
  add(M.wood, 0.9, 0.26, 0.05, { x: 1.55, y: 1.3, z: 5.0, ry: -0.12 });
  add(M.dark, 0.7, 0.04, 0.06, { x: 1.55, y: 1.3, z: 5.02, ry: -0.12 });
  add(M.wood, 0.7, 0.22, 0.05, { x: 1.5, y: 0.95, z: 4.99, ry: 0.15 });

  // ---------- banner pole (fixed; the flag climbs it with the level) ----------
  parts.push([placed(new THREE.CylinderGeometry(0.06, 0.09, 4.4, 6), { x: BANNER.x, y: 2.2, z: BANNER.z }), M.dark]);
  parts.push([placed(new THREE.IcosahedronGeometry(0.15, 0), { x: BANNER.x, y: 4.5, z: BANNER.z }), M.straw]);
  add(M.dark, 0.3, 0.2, 0.3, { x: BANNER.x, y: 0.1, z: BANNER.z });

  group.add(mergeByMaterial(parts));

  // ---------- instanced plants ----------
  const plants = [];
  for (const s of [-1, 1]) rowX.forEach((rx, r) => {
    for (let k = 0; k < 6; k++) plants.push({ x: s * rx, z: 0.5 + 0.7 * k, r, o: rnd(plants.length, seed), a: rnd(plants.length + 50, seed) * 6 });
  });
  const flowerCols = ["#f6f0ff", "#ff7aa8", "#ffe14d"].map(c => new THREE.Color(c));
  const fruitCols = ["#d6392b", "#f08a2b", "#e8c030"].map(c => new THREE.Color(c));
  const CAN = 4, APPLES = 10, STUDS = 10;
  const leaves = new THREE.InstancedMesh(ico, M.white, plants.length * 2 + CAN);
  const blooms = new THREE.InstancedMesh(ico, M.white, plants.length * 4 + APPLES + STUDS);
  for (const m of [leaves, blooms]) { m.castShadow = true; m.receiveShadow = true; m.frustumCulled = false; group.add(m); }

  const d = new THREE.Object3D();
  const col = new THREE.Color();
  const sprout = new THREE.Color("#b6e07a"), leafLo = new THREE.Color("#4f9a36"), leafHi = new THREE.Color("#2f7d3a");
  const setI = (mesh, i, x, y, z, sx, sy, sz, ry = 0) => {
    d.position.set(x, y, z); d.scale.set(Math.max(sx, 1e-4), Math.max(sy, 1e-4), Math.max(sz, 1e-4)); d.rotation.set(0, ry, 0);
    d.updateMatrix(); mesh.setMatrixAt(i, d.matrix);
  };

  // apples around the canopy
  const apples = [];
  for (let i = 0; i < APPLES; i++) {
    const a = i * 2.4 + 0.5, h = 1.9 + rnd(i, seed + 3) * 1.0, rad = 0.95 - Math.abs(h - 2.4) * 0.3;
    apples.push([TREE.x + Math.cos(a) * rad, h, TREE.z + Math.sin(a) * rad]);
  }
  const canopy = [[0, 2.45, 0, 1.05], [0.6, 2.15, 0.3, 0.8], [-0.55, 2.2, -0.2, 0.8], [0.1, 2.95, -0.1, 0.7]];

  let level = 1, flag = null;
  function setGrowth(p) {
    const g = clamp01(p);
    plants.forEach((pl, i) => {
      const gi = clamp01(g * 1.3 - pl.o * 0.3), e = smooth(gi), s = 0.24 + 0.76 * e;
      const y0 = 0.16;
      setI(leaves, i * 2, pl.x, y0 + 0.2 * s, pl.z, 0.32 * s, 0.24 * s, 0.32 * s, pl.a);
      setI(leaves, i * 2 + 1, pl.x + 0.03, y0 + 0.5 * s, pl.z, 0.2 * s, 0.26 * s * (e > 0.04 ? 1 : 0), 0.2 * s, pl.a + 1);
      col.copy(sprout).lerp(leafLo, e); leaves.setColorAt(i * 2, col);
      col.copy(sprout).lerp(leafHi, e); leaves.setColorAt(i * 2 + 1, col);
      const fe = smooth((gi - 0.5) / 0.25), ge = smooth((gi - 0.75) / 0.25);
      for (let j = 0; j < 2; j++) {
        const sg = j ? 1 : -1, b = i * 4 + j * 2;
        setI(blooms, b, pl.x + sg * 0.13, y0 + 0.62 * s, pl.z + sg * 0.05, 0.11 * fe, 0.11 * fe, 0.11 * fe, pl.a);
        blooms.setColorAt(b, flowerCols[(pl.r + j) % 3]);
        setI(blooms, b + 1, pl.x - sg * 0.14, y0 + 0.2 + 0.12 * j, pl.z + sg * 0.15, 0.14 * ge, 0.14 * ge, 0.14 * ge, pl.a);
        blooms.setColorAt(b + 1, fruitCols[pl.r % 3]);
      }
    });
    // orchard tree: grows a little, bears fruit above 0.6
    const tg = 0.62 + 0.38 * smooth(g), fr = smooth((g - 0.6) / 0.25);
    canopy.forEach(([cx, cy, cz, cr], j) => {
      const i = plants.length * 2 + j;
      setI(leaves, i, TREE.x + cx * tg, cy * (0.7 + 0.3 * tg), TREE.z + cz * tg, cr * tg, cr * tg * 0.85, cr * tg, j);
      col.set("#8fc25a").lerp(new THREE.Color(j % 2 ? "#3f8a3a" : "#4f9a36"), smooth(g * 1.5)); leaves.setColorAt(i, col);
    });
    const base = plants.length * 4;
    apples.forEach(([ax, ay, az], j) => {
      const sc = 0.11 * fr;
      setI(blooms, base + j, ax * 1 + 0 * tg, ay, az, sc, sc, sc);
      blooms.setColorAt(base + j, col.set(j % 3 ? "#d6392b" : "#e8c030"));
    });
    for (const m of [leaves, blooms]) { m.instanceMatrix.needsUpdate = true; m.instanceColor.needsUpdate = true; }
  }

  function setLevel(n) {
    level = Math.max(1, Math.min(10, Math.round(n)));
    const t = (level - 1) / 9;
    const w = 0.75 + 0.11 * level, h = 0.55 + 0.07 * level, topY = 2.0 + 0.24 * level;
    const c = new THREE.Color("#7b8794");
    c.lerp(new THREE.Color("#3a6fb0"), smooth(t * 2)).lerp(new THREE.Color(PALETTE.gold), smooth((t - 0.45) * 2));
    const hex = "#" + c.getHexString();
    const shape = new THREE.Shape();
    shape.moveTo(0, 0); shape.lineTo(-w, 0); shape.lineTo(-w + 0.18 + 0.01 * level, -h / 2); shape.lineTo(-w, -h); shape.lineTo(0, -h); shape.closePath();
    const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.03, bevelEnabled: false });
    geo.translate(-0.07, 0, -0.015);
    if (!flag) {
      flag = new THREE.Mesh(geo, mat(hex)); flag.castShadow = true; group.add(flag);
    } else { flag.geometry.dispose(); flag.geometry = geo; flag.material = mat(hex); }
    flag.position.set(BANNER.x, topY, BANNER.z);
    // level studs up the pole
    const base = plants.length * 4 + APPLES;
    for (let i = 0; i < STUDS; i++) {
      const on = i < level ? 0.065 : 0;
      setI(blooms, base + i, BANNER.x, 0.45 + i * 0.12, BANNER.z + 0.1, on, on, on);
      blooms.setColorAt(base + i, col.set(PALETTE.gold));
    }
    blooms.instanceMatrix.needsUpdate = true; blooms.instanceColor.needsUpdate = true;
  }

  setGrowth(0); setLevel(1);
  return { group, windows: house.windows, chimneyTop: house.chimneyTop.clone().add(new THREE.Vector3(0, 0, HOUSE_Z)), setGrowth, setLevel };
}

export function preview(scene) {
  const specs = [
    { color: PALETTE.roofRed, floors: 1, seed: 3, g: 0, l: 1 },
    { color: PALETTE.roofBlue, floors: 2, seed: 7, g: 0.5, l: 4 },
    { color: PALETTE.roofTeal, floors: 3, seed: 11, g: 1, l: 9 },
  ];
  specs.forEach((s, i) => {
    const e = createEstate(s);
    e.setGrowth(s.g); e.setLevel(s.l);
    e.group.position.x = (i - 1) * 14;
    scene.add(e.group);
  });
}
