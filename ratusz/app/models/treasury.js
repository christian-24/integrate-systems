// The village treasury: a stone counting-house with a gold-trimmed slate roof, a vault door, a
// balance-scale sign, coin chests, sacks and a gold coin pile (instanced) that grow with
// setWealth(0..1), a counting table with ledgers and guard lanterns. Front faces +z.
import { THREE, mat, glow, PALETTE, placed, mergeByMaterial, canvasTexture, rnd } from "./kit.js";

const unit = new THREE.BoxGeometry(1, 1, 1);
const cyl8 = new THREE.CylinderGeometry(1, 1, 1, 8);
const cyl6 = new THREE.CylinderGeometry(1, 1, 1, 6);
const cyl12 = new THREE.CylinderGeometry(1, 1, 1, 12);
const cone8 = new THREE.ConeGeometry(1, 1, 8);
const pyr = new THREE.ConeGeometry(1, 1, 4);
const sph = new THREE.SphereGeometry(1, 8, 6);
const torus = new THREE.TorusGeometry(1, 0.1, 5, 12);

let slateMat;
function slate() {
  if (!slateMat) {
    const map = canvasTexture("treasury-slate", 64, (c, s) => {
      c.fillStyle = "#cfd3dc"; c.fillRect(0, 0, s, s);
      const rows = 8, rh = s / rows, cols = 4, cw = s / cols;
      for (let r = 0; r < rows; r++) for (let k = 0; k < cols + 1; k++) {
        const v = 190 + ((r * 7 + k * 5) % 4) * 16, x = k * cw + (r % 2 ? cw / 2 : 0) - cw / 2;
        c.fillStyle = `rgb(${v},${v},${v + 8})`; c.fillRect(x, r * rh, cw - 1, rh - 1);
        c.strokeStyle = "rgba(20,25,45,0.6)"; c.lineWidth = 1.5; c.strokeRect(x, r * rh, cw - 1, rh - 1);
      }
    }, [4, 2]);
    slateMat = new THREE.MeshStandardMaterial({ color: "#4d5f86", map, roughness: 0.85, flatShading: true });
  }
  return slateMat;
}

// chest slots in the order they appear as wealth grows
const CHESTS = [
  { x: 2.8, z: 1.0, y: 0, ry: 0.05 }, { x: 4.0, z: 1.0, y: 0, ry: -0.08 }, { x: 2.8, z: 1.0, y: 0.62, ry: 0.3 },
  { x: 5.0, z: 1.1, y: 0, ry: -0.25 }, { x: 4.0, z: 1.0, y: 0.62, ry: -0.2 }, { x: 2.2, z: 2.1, y: 0, ry: 0.5 },
];
const NCOIN = 280, PILE = { x: 4.0, z: 3.4, R: 1.5, H: 1.0 };

export function createTreasury() {
  const M = {
    stone: mat(PALETTE.stone), stoneD: mat(PALETTE.stoneDark), stoneL: mat(PALETTE.stoneLight),
    roof: slate(), gold: mat(PALETTE.gold, { metalness: 0.4, roughness: 0.4 }),
    wood: mat(PALETTE.wood), dark: mat(PALETTE.woodDark), iron: mat("#4a4d55", { metalness: 0.5, roughness: 0.5 }),
    cloth: mat(PALETTE.cloth), paper: mat("#f4ecd6"), win: glow(PALETTE.window, 1.1), red: mat(PALETTE.roofRed),
  };
  const parts = [];
  const box = (m, w, h, d, o = {}) => parts.push([placed(unit, { ...o, sx: w, sy: h, sz: d }), m]);
  const cyl = (m, rx, h, rz, o = {}, g = cyl8) => parts.push([placed(g, { ...o, sx: rx, sy: h, sz: rz }), m]);
  const ball = (m, rx, ry, rz, o = {}) => parts.push([placed(sph, { ...o, sx: rx, sy: ry, sz: rz }), m]);

  // --- paved forecourt ---
  box(M.stoneL, 11, 0.06, 9.2, { y: 0.03, z: -0.2 });
  box(M.stone, 2.2, 0.08, 4.6, { y: 0.04, z: 2.3 });          // path to the door

  // --- counting-house: x -3.5..3.5, z -5..0 ---
  const W = 7, D = 5, HZ = -2.5, BASE = 0.55, WH = 3.2, top = BASE + WH, fz = HZ + D / 2;
  box(M.stoneD, W + 0.4, BASE, D + 0.4, { y: BASE / 2, z: HZ });
  box(M.stone, W, WH, D, { y: BASE + WH / 2, z: HZ });
  for (let k = 0; k < 6; k++) for (const sx of [-1, 1]) for (const sz of [-1, 1])   // corner quoins
    box(M.stoneL, 0.55, 0.5, 0.55, { x: sx * (W / 2 - 0.02), y: BASE + 0.25 + k * 0.54 + (k % 2) * 0.04, z: HZ + sz * (D / 2 - 0.02) });
  box(M.stoneL, W + 0.2, 0.2, D + 0.2, { y: top - 0.1, z: HZ });            // cornice
  box(M.gold, W + 0.3, 0.1, D + 0.3, { y: top + 0.03, z: HZ });             // gold eave band
  box(M.gold, W + 0.1, 0.07, 0.07, { y: BASE + 0.85, z: fz + 0.04 });       // gold stripe
  // slate hip roof with gold ridge ribs
  const rh = 2.6;
  parts.push([placed(pyr, { y: top + 0.08 + rh / 2, z: HZ, ry: Math.PI / 4, sx: W / 2 * 1.45, sy: rh, sz: D / 2 * 1.45 }), M.roof]);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    const cx = sx * W / 2 * 1.03, cz = sz * D / 2 * 1.03, dir = new THREE.Vector3(-cx, rh, -cz), len = dir.length();
    const g = placed(unit, { sx: 0.1, sy: 0.1, sz: len });
    g.applyMatrix4(new THREE.Matrix4().makeRotationFromQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir.normalize())));
    g.applyMatrix4(new THREE.Matrix4().makeTranslation(cx / 2, top + 0.08 + rh / 2 + 0.03, HZ + cz / 2));
    parts.push([g, M.gold]);
  }
  cyl(M.gold, 0.06, 1.0, 0.06, { y: top + rh + 0.55, z: HZ }, cyl6);          // finial spike (orb is animated)
  // chimney
  box(M.stoneD, 0.7, 1.6, 0.7, { x: -2.1, y: top + 1.2, z: HZ - 1.2 });
  box(M.stoneL, 0.9, 0.12, 0.9, { x: -2.1, y: top + 2.05, z: HZ - 1.2 });

  // --- portico with pediment ---
  const PZ = fz + 1.1;
  box(M.stoneL, 4.0, 0.2, 2.2, { y: 0.1, z: fz + 0.9 });                    // platform
  box(M.stone, 3.2, 0.14, 0.7, { y: 0.07, z: fz + 2.1 });
  for (const s of [-1, 1]) {
    cyl(M.stoneL, 0.24, 2.7, 0.24, { x: s * 1.5, y: 0.2 + 1.35, z: PZ }, cyl8);
    cyl(M.gold, 0.3, 0.12, 0.3, { x: s * 1.5, y: 0.26, z: PZ });
    cyl(M.gold, 0.3, 0.12, 0.3, { x: s * 1.5, y: 2.9, z: PZ });
  }
  box(M.stoneL, 3.7, 0.3, 0.55, { y: 3.1, z: PZ });                         // architrave
  box(M.gold, 3.8, 0.07, 0.6, { y: 3.28, z: PZ });
  const tri = new THREE.Shape();
  tri.moveTo(-1.95, 0); tri.lineTo(1.95, 0); tri.lineTo(0, 0.95); tri.closePath();
  parts.push([placed(new THREE.ExtrudeGeometry(tri, { depth: 0.5, bevelEnabled: false }), { y: 3.32, z: PZ - 0.25 }), M.stoneL]);
  parts.push([placed(new THREE.ExtrudeGeometry(tri, { depth: 0.06, bevelEnabled: false }), { y: 3.34, z: PZ + 0.26, sx: 0.8, sy: 0.7 }), M.gold]);
  // balance-scale sign on the pediment
  const SY = 4.75, SZ = PZ + 0.1;
  cyl(M.gold, 0.06, 1.2, 0.06, { y: 4.0, z: SZ }, cyl6);
  box(M.gold, 1.7, 0.07, 0.07, { y: SY, z: SZ });
  ball(M.gold, 0.12, 0.12, 0.12, { y: SY + 0.02, z: SZ });
  for (const s of [-1, 1]) {
    for (const a of [-0.3, 0.3]) box(M.gold, 0.02, 0.62, 0.02, { x: s * 0.8 + a * 0.5, y: SY - 0.3, z: SZ, rz: a * 0.6 });
    cyl(M.gold, 0.4, 0.07, 0.4, { x: s * 0.8, y: SY - 0.62, z: SZ }, cyl8);
    ball(M.gold, 0.1, 0.05, 0.1, { x: s * 0.8, y: SY - 0.56, z: SZ });
  }
  // --- vault door ---
  const VZ = fz + 0.06, VY = BASE + 1.45;
  box(M.stoneL, 2.7, 2.9, 0.1, { y: BASE + 1.45, z: fz + 0.04 });
  box(M.stoneD, 2.3, 2.5, 0.12, { y: BASE + 1.45, z: fz + 0.06 });
  cyl(M.iron, 1.0, 0.18, 1.0, { y: VY, z: VZ + 0.1, rx: Math.PI / 2 }, cyl12);
  parts.push([placed(torus, { y: VY, z: VZ + 0.2, sx: 1.0, sy: 1.0, sz: 1.5 }), M.gold]);
  for (const a of [0, 1.047, 2.094]) box(M.gold, 1.5, 0.09, 0.1, { y: VY, z: VZ + 0.22, rz: a });
  ball(M.gold, 0.2, 0.2, 0.16, { y: VY, z: VZ + 0.26 });
  for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; ball(M.gold, 0.06, 0.06, 0.06, { x: Math.cos(a) * 0.82, y: VY + Math.sin(a) * 0.82, z: VZ + 0.22 }); }
  // --- barred windows with glow ---
  for (const x of [-2.55, 2.55]) {
    box(M.stoneL, 0.95, 1.25, 0.1, { x, y: BASE + 1.8, z: fz + 0.03 });
    box(M.win, 0.7, 1.0, 0.06, { x, y: BASE + 1.8, z: fz + 0.07 });
    for (const dx of [-0.2, 0, 0.2]) box(M.iron, 0.04, 1.0, 0.04, { x: x + dx, y: BASE + 1.8, z: fz + 0.14 });
    box(M.stoneL, 1.1, 0.12, 0.2, { x, y: BASE + 1.1, z: fz + 0.1 });
  }
  // --- coin sacks left of the portico ---
  for (const [x, z, s] of [[-3.0, 0.6, 0.5], [-3.7, 0.9, 0.45], [-3.35, 1.55, 0.42]]) {
    ball(M.cloth, s, s * 1.1, s, { x, y: s * 0.95, z });
    cyl(M.dark, s * 0.4, s * 0.2, s * 0.4, { x, y: s * 1.9, z }, cyl6);
  }
  // --- counting table with ledgers, stool, candle ---
  const TX = -4.0, TZ = 3.1;
  box(M.wood, 2.0, 0.1, 1.0, { x: TX, y: 0.95, z: TZ });
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) box(M.dark, 0.12, 0.9, 0.12, { x: TX + sx * 0.85, y: 0.47, z: TZ + sz * 0.38 });
  box(M.red, 0.55, 0.12, 0.4, { x: TX - 0.5, y: 1.06, z: TZ - 0.1, ry: 0.2 });
  box(M.paper, 0.5, 0.06, 0.36, { x: TX - 0.5, y: 1.1, z: TZ - 0.1, ry: 0.2 });
  box(M.dark, 0.5, 0.1, 0.38, { x: TX + 0.2, y: 1.05, z: TZ + 0.1, ry: -0.3 });
  box(M.paper, 0.44, 0.05, 0.32, { x: TX + 0.2, y: 1.12, z: TZ + 0.1, ry: -0.3 });
  for (let i = 0; i < 4; i++) cyl(M.gold, 0.1, 0.035, 0.1, { x: TX + 0.65, y: 1.03 + i * 0.035, z: TZ + 0.25 }, cyl6);
  cyl(M.dark, 0.35, 0.1, 0.35, { x: TX + 0.1, y: 0.55, z: TZ + 1.0 });
  for (const a of [0, 2.1, 4.2]) cyl(M.dark, 0.05, 0.55, 0.05, { x: TX + 0.1 + Math.cos(a) * 0.2, y: 0.27, z: TZ + 1.0 + Math.sin(a) * 0.2 }, cyl6);
  cyl(M.cloth, 0.06, 0.18, 0.06, { x: TX + 0.75, y: 1.12, z: TZ - 0.25 }, cyl6);
  ball(M.win, 0.05, 0.08, 0.05, { x: TX + 0.75, y: 1.27, z: TZ - 0.25 });
  // --- guard lanterns flanking the path ---
  for (const s of [-1, 1]) {
    const x = s * 1.8, z = 4.0;
    cyl(M.iron, 0.07, 2.2, 0.07, { x, y: 1.1, z }, cyl6);
    cyl(M.stoneD, 0.25, 0.3, 0.25, { x, y: 0.15, z });
    box(M.win, 0.26, 0.34, 0.26, { x, y: 2.35, z });
    box(M.iron, 0.36, 0.06, 0.36, { x, y: 2.56, z });
    parts.push([placed(cone8, { x, y: 2.7, z, sx: 0.26, sy: 0.22, sz: 0.26 }), M.gold]);
  }
  // gold bars by the door and bollards at the forecourt corners
  for (let i = 0; i < 3; i++) box(M.gold, 0.5, 0.18, 0.22, { x: -2.2, y: 0.2 + i * 0.18, z: 0.9, ry: 0.1 * i });
  for (const [x, z] of [[-5, 4.1], [-5, -4.5], [5, -4.5]]) { cyl(M.stoneD, 0.22, 0.8, 0.22, { x, y: 0.4, z }, cyl6); ball(M.gold, 0.16, 0.14, 0.16, { x, y: 0.85, z }); }

  const group = mergeByMaterial(parts);

  // --- animated / wealth-driven bits ---
  const orbMat = glow(PALETTE.gold, 0.3).clone();
  const orb = new THREE.Mesh(sph, orbMat);
  orb.position.set(0, top + rh + 1.2, HZ); orb.scale.setScalar(0.28);
  const haloMat = new THREE.MeshBasicMaterial({ color: "#ffd873", transparent: true, opacity: 0, depthWrite: false });
  const halo = new THREE.Mesh(sph, haloMat);
  halo.position.copy(orb.position); halo.scale.setScalar(0.7);
  group.add(orb, halo);

  // coins (instanced), sorted low to high so a growing pile fills up from the ground
  const coinMat = new THREE.MeshStandardMaterial({ color: PALETTE.gold, emissive: "#c8861a", emissiveIntensity: 0.15, metalness: 0.5, roughness: 0.35, flatShading: true });
  const coins = new THREE.InstancedMesh(cyl6, coinMat, NCOIN);
  const list = [];
  for (let i = 0; i < NCOIN; i++) {
    const a = rnd(i, 3) * Math.PI * 2, r = PILE.R * Math.sqrt(rnd(i, 5));
    const h = PILE.H * Math.max(0, 1 - (r / PILE.R) ** 2);
    list.push({ x: PILE.x + Math.cos(a) * r, z: PILE.z + Math.sin(a) * r * 0.85, y: 0.06 + h * Math.pow(rnd(i, 9), 0.6), a, r, i });
  }
  list.sort((p, q) => p.y - q.y);
  const m4 = new THREE.Matrix4(), qt = new THREE.Quaternion(), e = new THREE.Euler(), p = new THREE.Vector3(), sc = new THREE.Vector3(0.17, 0.035, 0.17);
  list.forEach((c, n) => {
    const slope = (c.r / PILE.R) * 0.5;
    e.set(Math.sin(c.a) * slope + (rnd(c.i, 11) - 0.5) * 0.4, rnd(c.i, 13) * 6.28, -Math.cos(c.a) * slope + (rnd(c.i, 15) - 0.5) * 0.4);
    qt.setFromEuler(e); p.set(c.x, c.y, c.z); m4.compose(p, qt, sc); coins.setMatrixAt(n, m4);
  });
  coins.castShadow = true; coins.receiveShadow = true; coins.frustumCulled = false;
  group.add(coins);

  // chests: wooden bodies, lids and gold bands as three instanced meshes
  const NCH = CHESTS.length;
  const bodies = new THREE.InstancedMesh(unit, M.wood, NCH), lids = new THREE.InstancedMesh(cyl8, M.dark, NCH), bands = new THREE.InstancedMesh(unit, M.gold, NCH * 2);
  const S = new THREE.Vector3(), yAxis = new THREE.Vector3(0, 1, 0);
  CHESTS.forEach((c, n) => {
    const yq = new THREE.Quaternion().setFromAxisAngle(yAxis, c.ry);
    p.set(c.x, c.y + 0.33, c.z); S.set(1.0, 0.56, 0.65); m4.compose(p, yq, S); bodies.setMatrixAt(n, m4);
    const lq = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, Math.PI / 2)).premultiply(yq);
    p.set(c.x, c.y + 0.61, c.z); S.set(0.2, 1.0, 0.33); m4.compose(p, lq, S); lids.setMatrixAt(n, m4);
    for (const s of [-1, 1]) {
      const o = new THREE.Vector3(s * 0.33, 0, 0).applyQuaternion(yq);
      p.set(c.x + o.x, c.y + 0.4, c.z + o.z); S.set(0.1, 0.8, 0.69); m4.compose(p, yq, S); bands.setMatrixAt(n * 2 + (s > 0 ? 1 : 0), m4);
    }
  });
  for (const m of [bodies, lids, bands]) { m.castShadow = m.receiveShadow = true; m.frustumCulled = false; group.add(m); }

  let wealth = 0;
  function setWealth(level) {
    wealth = Math.max(0, Math.min(1, +level || 0));
    coins.count = Math.round(NCOIN * wealth);
    const nc = Math.round(NCH * wealth);
    bodies.count = lids.count = nc; bands.count = nc * 2;
    halo.visible = wealth > 0.05;
  }
  function update(dt, t) {
    const glint = Math.max(0, Math.sin(t * 1.7)) ** 6;
    coinMat.emissiveIntensity = 0.12 + 0.5 * glint * wealth;
    orbMat.emissiveIntensity = 0.25 + 1.8 * wealth + 0.25 * wealth * Math.sin(t * 2.3);
    haloMat.opacity = wealth * (0.2 + 0.07 * Math.sin(t * 2.3));
    halo.scale.setScalar(0.6 + 0.9 * wealth + 0.05 * Math.sin(t * 2.3));
    orb.rotation.y = t;
  }
  setWealth(0); update(0, 0);
  return { group, update, setWealth };
}

export function preview(scene) {
  const list = [0, 0.5, 1].map((w, i) => {
    const t = createTreasury(); t.setWealth(w); t.group.position.x = (i - 1) * 13; scene.add(t.group); return t;
  });
  return (dt, t) => list.forEach(x => x.update(dt, t));
}
