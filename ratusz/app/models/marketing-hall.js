// The heralds' house (marketing): violet-roofed guild hall, big notice board with parchment posters,
// long swaying banners, a bell tower and messenger birds on the ridge. Front faces +z.
import { THREE, mat, glow, PALETTE, placed, mergeByMaterial, canvasTexture, rnd } from "./kit.js";

const unit = new THREE.BoxGeometry(1, 1, 1);
const cyl8 = new THREE.CylinderGeometry(1, 1, 1, 8);
const cone8 = new THREE.ConeGeometry(1, 1, 8);
const sph = new THREE.SphereGeometry(1, 8, 6);

let violetRoof;
function roofMat() {
  if (!violetRoof) {
    const map = canvasTexture("marketing-tiles", 64, (c, s) => {
      c.fillStyle = "#e6e6e6"; c.fillRect(0, 0, s, s);
      const rows = 4, rh = s / rows, cols = 4, cw = s / cols;
      for (let r = 0; r < rows; r++) for (let k = -1; k < cols + 1; k++) {
        const cx = k * cw + (r % 2 ? cw / 2 : 0) + cw / 2, cy = r * rh;
        const v = 205 + ((r * 7 + k * 13) % 4) * 14;
        c.fillStyle = `rgb(${v},${v},${v})`;
        c.beginPath(); c.moveTo(cx - cw / 2, cy); c.lineTo(cx + cw / 2, cy); c.lineTo(cx + cw / 2, cy + rh * 0.55);
        c.arc(cx, cy + rh * 0.55, cw / 2, 0, Math.PI, false); c.closePath(); c.fill();
        c.strokeStyle = "rgba(50,30,60,0.55)"; c.lineWidth = 2; c.stroke();
      }
    }, [4, 3]);
    violetRoof = new THREE.MeshStandardMaterial({ color: "#9a66cc", map, roughness: 0.8, flatShading: true });
  }
  return violetRoof;
}

export function createMarketingHall() {
  const wood = mat(PALETTE.wood), parch = mat("#f2e6c0"), violetD = mat("#6d46a0"), pink = mat("#e8657a"), bird = mat("#f4f0ea"), gold = mat(PALETTE.gold);
  const M = {
    wood, dark: mat(PALETTE.woodDark), light: wood,
    plaster: mat("#f1e4ca"), stone: mat(PALETTE.stone), stoneD: mat(PALETTE.stone),
    roof: roofMat(), gold,
    parch, parch2: parch, violet: violetD, violetD,
    pink, teal: pink, win: glow(PALETTE.window, 1.1), leaf: mat(PALETTE.leaf),
    bird, birdD: bird, beak: gold, inkM: mat(PALETTE.woodDark),
  };
  const parts = [];
  const box = (m, w, h, d, o = {}) => parts.push([placed(unit, { ...o, sx: w, sy: h, sz: d }), m]);
  const cyl = (m, rx, h, rz, o = {}) => parts.push([placed(cyl8, { ...o, sx: rx, sy: h, sz: rz }), m]);
  const ball = (m, r, o = {}) => parts.push([placed(sph, { ...o, sx: r, sy: r, sz: r }), m]);

  // --- main hall: x -4.5..2.5 (7 wide), z -4.2..0.3 ---
  const HX = 7.0, HD = 4.5, HZ = -1.95, HC = -1.0, BASE = 0.5, WH = 2.7;
  const fz = HZ + HD / 2;
  box(M.stone, HX + 0.3, BASE, HD + 0.3, { x: HC, y: BASE / 2, z: HZ });
  box(M.plaster, HX, WH, HD, { x: HC, y: BASE + WH / 2, z: HZ });
  for (let i = 0; i <= 5; i++) {
    const x = HC - HX / 2 + (i * HX) / 5;
    box(M.violetD, 0.2, WH + 0.1, 0.2, { x, y: BASE + WH / 2, z: fz });
    box(M.violetD, 0.2, WH + 0.1, 0.2, { x, y: BASE + WH / 2, z: HZ - HD / 2 });
  }
  for (const y of [BASE + 0.05, BASE + WH - 0.1]) {
    box(M.violetD, HX + 0.2, 0.2, 0.22, { x: HC, y, z: fz });
    box(M.violetD, HX + 0.2, 0.2, 0.22, { x: HC, y, z: HZ - HD / 2 });
    for (const s of [-1, 1]) box(M.violetD, 0.22, 0.2, HD + 0.2, { x: HC + s * HX / 2, y, z: HZ });
  }
  // door (arched look: lintel + wooden door), centred at x = HC + 1.4
  const dx = HC + 1.6;
  box(M.dark, 1.5, 2.1, 0.16, { x: dx, y: BASE + 1.05, z: fz + 0.02 });
  box(M.wood, 1.2, 1.9, 0.14, { x: dx, y: BASE + 0.95, z: fz + 0.08 });
  box(M.dark, 0.05, 1.9, 0.16, { x: dx, y: BASE + 0.95, z: fz + 0.1 });
  parts.push([placed(cyl8, { x: dx, y: BASE + 1.9, z: fz + 0.08, rx: Math.PI / 2, sx: 0.6, sy: 0.14, sz: 0.6 }), M.wood]);
  box(M.stone, 2.2, 0.2, 1.1, { x: dx, y: 0.1, z: fz + 0.7 });
  for (const s of [-1, 1]) box(M.violetD, 0.16, 2.7, 0.16, { x: dx + s * 0.95, y: BASE + 1.2, z: fz + 1.1 });
  box(M.roof, 2.4, 0.12, 1.6, { x: dx, y: BASE + 2.8, z: fz + 0.55, rx: 0.3 });
  // lanterns either side of the door
  for (const s of [-1, 1]) {
    box(M.dark, 0.04, 0.16, 0.04, { x: dx + s * 0.95, y: BASE + 2.35, z: fz + 1.1 });
    box(M.win, 0.2, 0.26, 0.2, { x: dx + s * 0.95, y: BASE + 2.1, z: fz + 1.1 });
  }
  // windows (left of door and sides)
  for (const x of [HC - 2.8, HC - 1.4]) {
    box(M.win, 0.8, 1.0, 0.05, { x, y: BASE + 1.5, z: fz + 0.03 });
    box(M.dark, 0.98, 0.09, 0.1, { x, y: BASE + 2.04, z: fz + 0.05 });
    box(M.dark, 0.98, 0.09, 0.1, { x, y: BASE + 0.96, z: fz + 0.05 });
    box(M.dark, 0.06, 1.0, 0.1, { x, y: BASE + 1.5, z: fz + 0.05 });
    box(M.stone, 1.1, 0.08, 0.22, { x, y: BASE + 0.88, z: fz + 0.1 });
  }
  for (const s of [-1, 1]) {
    box(M.win, 0.05, 1.0, 0.8, { x: HC + s * (HX / 2 + 0.03), y: BASE + 1.5, z: HZ });
    box(M.dark, 0.1, 1.0, 0.06, { x: HC + s * (HX / 2 + 0.05), y: BASE + 1.5, z: HZ });
  }
  // roof, ridge along x
  const rh = 1.9, rw = HD / 2 + 0.55, ang = Math.atan2(rh, rw), L = Math.hypot(rw, rh) + 0.05, RX = HX + 1.0;
  const by = BASE + WH;
  for (const s of [-1, 1]) box(M.roof, RX, 0.16, L, { x: HC, y: by + rh / 2 + 0.08, z: HZ + s * rw / 2, rx: s * ang });
  box(M.gold, RX + 0.1, 0.14, 0.2, { x: HC, y: by + rh + 0.14, z: HZ });
  const tri = new THREE.Shape();
  tri.moveTo(-HD / 2, 0); tri.lineTo(HD / 2, 0); tri.lineTo(0, rh - 0.05); tri.closePath();
  parts.push([placed(new THREE.ExtrudeGeometry(tri, { depth: HX, bevelEnabled: false }), { x: HC - HX / 2, y: by - 0.02, z: HZ, ry: Math.PI / 2 }), M.plaster]);
  for (const s of [-1, 1]) {
    box(M.violetD, 0.1, 0.14, HD, { x: HC + s * (HX / 2 + 0.03), y: by, z: HZ });
    box(M.win, 0.04, 0.6, 0.6, { x: HC + s * (HX / 2 + 0.03), y: by + 0.7, z: HZ, rx: Math.PI / 4 });
  }

  // --- bell tower at the right back corner ---
  const TX = HC + HX / 2 + 0.9, TZ = HZ - 0.8, TS = 2.2, TH = 5.2;
  box(M.stone, TS + 0.3, BASE, TS + 0.3, { x: TX, y: BASE / 2, z: TZ });
  box(M.plaster, TS, TH - BASE, TS, { x: TX, y: (TH + BASE) / 2, z: TZ });
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) box(M.violetD, 0.22, TH, 0.22, { x: TX + sx * TS / 2, y: TH / 2, z: TZ + sz * TS / 2 });
  for (const y of [1.9, 3.5]) box(M.violetD, TS + 0.2, 0.14, TS + 0.2, { x: TX, y, z: TZ });
  box(M.win, 0.5, 0.9, 0.05, { x: TX, y: 2.7, z: TZ + TS / 2 + 0.02 });
  box(M.dark, 0.64, 0.08, 0.1, { x: TX, y: 3.2, z: TZ + TS / 2 + 0.03 });
  // open belfry
  const bt = TH, bh = 1.7;
  box(M.violetD, TS + 0.5, 0.2, TS + 0.5, { x: TX, y: bt + 0.1, z: TZ });
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) box(M.wood, 0.2, bh, 0.2, { x: TX + sx * (TS / 2 - 0.05), y: bt + 0.2 + bh / 2, z: TZ + sz * (TS / 2 - 0.05) });
  for (const sx of [-1, 1]) box(M.wood, 0.14, 0.14, TS, { x: TX + sx * (TS / 2 - 0.05), y: bt + 0.2 + bh - 0.3, z: TZ });
  for (const sz of [-1, 1]) box(M.wood, TS, 0.14, 0.14, { x: TX, y: bt + 0.2 + bh - 0.3, z: TZ + sz * (TS / 2 - 0.05) });
  box(M.dark, TS - 0.2, 0.1, 0.1, { x: TX, y: bt + 0.2 + bh - 0.1, z: TZ });
  parts.push([placed(cone8, { x: TX, y: bt + bh + 1.4, z: TZ, ry: Math.PI / 8, sx: TS * 0.95, sy: 2.4, sz: TS * 0.95 }), M.roof]);
  cyl(M.dark, 0.05, 0.9, 0.05, { x: TX, y: bt + bh + 3.0, z: TZ });
  ball(M.gold, 0.16, { x: TX, y: bt + bh + 3.5, z: TZ });
  // horn on the tower front
  parts.push([placed(cone8, { x: TX, y: 4.2, z: TZ + TS / 2 + 0.4, rx: Math.PI / 2, sx: 0.28, sy: 0.8, sz: 0.28 }), M.gold]);

  // --- big notice board on posts, in front of the hall (left) ---
  const NX = HC - 2.6, NZ = fz + 3.6, BW = 3.8, BHt = 2.2;
  for (const s of [-1, 1]) box(M.dark, 0.2, 3.3, 0.2, { x: NX + s * (BW / 2 + 0.05), y: 1.65, z: NZ });
  box(M.light, BW + 0.2, BHt, 0.14, { x: NX, y: 2.0, z: NZ });
  box(M.wood, BW - 0.2, BHt - 0.2, 0.06, { x: NX, y: 2.0, z: NZ + 0.1 });
  box(M.dark, BW + 0.5, 0.2, 0.3, { x: NX, y: 3.4, z: NZ });
  box(M.roof, BW + 0.9, 0.1, 0.9, { x: NX, y: 3.65, z: NZ + 0.05, rx: 0.35 });
  box(M.roof, BW + 0.9, 0.1, 0.9, { x: NX, y: 3.65, z: NZ - 0.05, rx: -0.35 });
  // posters (parchment, with ink lines and wax seals)
  const posters = [
    [-1.45, 2.45, 0.9, 1.0, M.parch, 0.04], [-0.3, 2.5, 0.8, 1.2, M.parch2, -0.03], [0.85, 2.4, 1.0, 0.9, M.parch, 0.02],
    [1.5, 1.6, 0.8, 0.8, M.parch2, -0.05], [-1.5, 1.35, 0.85, 0.8, M.parch2, -0.04], [-0.45, 1.3, 0.9, 0.9, M.parch, 0.03], [0.55, 1.35, 0.7, 0.9, M.parch, 0.05],
  ];
  posters.forEach(([px, py, pw, ph, m, rz], i) => {
    box(m, pw, ph, 0.03, { x: NX + px, y: py, z: NZ + 0.15, rz });
    const seal = [M.pink, M.teal, M.violet][i % 3];
    box(seal, pw * 0.7, 0.07, 0.02, { x: NX + px, y: py + ph * 0.28, z: NZ + 0.17, rz });
    for (let k = 0; k < 3; k++) box(M.inkM, pw * (0.5 + rnd(i * 3 + k, 4) * 0.25), 0.04, 0.02, { x: NX + px, y: py - 0.02 - k * 0.14, z: NZ + 0.17, rz });
    box(M.pink, 0.1, 0.1, 0.03, { x: NX + px, y: py + ph / 2 - 0.05, z: NZ + 0.19 });
  });

  // --- crates and a barrel of leaflets, flowers ---
  box(M.light, 0.7, 0.7, 0.7, { x: HC + 3.6, y: 0.35, z: fz + 1.0, ry: 0.3 });
  box(M.parch, 0.5, 0.06, 0.4, { x: HC + 3.6, y: 0.73, z: fz + 1.0, ry: 0.5 });
  cyl(M.wood, 0.3, 0.7, 0.3, { x: HC + 3.4, y: 0.35, z: fz + 2.0 });
  cyl(M.dark, 0.31, 0.06, 0.31, { x: HC + 3.4, y: 0.3, z: fz + 2.0 });
  for (const [x, z, s] of [[HC - HX / 2 - 0.3, fz + 0.2, 0.38], [HC + 4.6, fz - 0.3, 0.34]]) {
    ball(M.leaf, s, { x, y: s * 0.7, z, sy: s * 0.85 });
    box(M.pink, 0.1, 0.1, 0.1, { x: x + 0.14, y: s * 1.2, z: z + 0.22 });
  }
  // banner poles (banners are animated separately)
  for (const x of [HC - 3.2, HC + 3.3]) {
    box(M.gold, 0.1, 0.1, 0.1, { x, y: 4.0, z: fz + 0.5 });
  }
  box(M.dark, 6.6, 0.1, 0.1, { x: HC, y: 4.05, z: fz + 0.55 });
  // birds on the ridge (static bodies)
  const birds = [[HC - 2.2, 0.3], [HC - 0.7, -0.4], [HC + 2.0, 0.2]];
  const ry = by + rh + 0.24;
  birds.forEach(([x, rot], i) => {
    parts.push([placed(sph, { x, y: ry + 0.17, z: HZ, sx: 0.15, sy: 0.14, sz: 0.2, ry: rot }), M.bird]);
    parts.push([placed(sph, { x: x + Math.sin(rot) * 0.17, y: ry + 0.33, z: HZ + Math.cos(rot) * 0.17, sx: 0.09, sy: 0.09, sz: 0.09 }), M.bird]);
    parts.push([placed(cone8, { x: x + Math.sin(rot) * 0.3, y: ry + 0.32, z: HZ + Math.cos(rot) * 0.3, rx: Math.PI / 2, ry: rot, sx: 0.035, sy: 0.12, sz: 0.035 }), M.beak]);
    parts.push([placed(unit, { x: x - Math.sin(rot) * 0.25, y: ry + 0.15, z: HZ - Math.cos(rot) * 0.25, ry: rot, rx: -0.3, sx: 0.12, sy: 0.04, sz: 0.28 }), M.birdD]);
    // letter tied to the first bird
    if (i === 1) box(M.parch, 0.1, 0.07, 0.14, { x, y: ry + 0.05, z: HZ + 0.12 });
  });

  const group = mergeByMaterial(parts);

  // --- animated: banners, bell ---
  const banners = [];
  const mk = (key, bg, fg, emblem) => new THREE.MeshStandardMaterial({
    side: THREE.DoubleSide, roughness: 0.9,
    map: canvasTexture(key, 64, (c, s) => {
      c.fillStyle = bg; c.fillRect(0, 0, s, s);
      c.fillStyle = "#e2b347"; c.fillRect(0, 0, s, 4); c.fillRect(0, s - 4, s, 4);
      c.fillStyle = fg; emblem(c, s);
    }),
  });
  const horn = (c, s) => { c.beginPath(); c.moveTo(s * 0.2, s * 0.5); c.lineTo(s * 0.8, s * 0.25); c.lineTo(s * 0.8, s * 0.75); c.closePath(); c.fill(); c.fillRect(s * 0.1, s * 0.42, s * 0.14, s * 0.16); };
  const star = (c, s) => { c.beginPath(); for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? s * 0.14 : s * 0.34; c.lineTo(s / 2 + Math.cos(a) * r, s / 2 + Math.sin(a) * r); } c.closePath(); c.fill(); };
  const m1 = mk("mk-b1", "#9a6ad8", "#f2e6c0", horn), mats = [m1, m1, m1];
  [HC - 3.2, HC, HC + 3.3].forEach((x, i) => {
    if (i === 1) return;
    const geo = new THREE.PlaneGeometry(0.9, 3.0, 3, 8);
    const b = new THREE.Mesh(geo, mats[i]);
    b.position.set(x, 4.05 - 1.5, fz + 0.62); b.castShadow = true;
    group.add(b); banners.push({ b, geo, base: geo.attributes.position.array.slice(), i });
  });
  // bell inside the belfry
  const bell = new THREE.Group();
  bell.position.set(TX, bt + 0.2 + bh - 0.1, TZ);
  const bellMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.5, 0.7, 8), M.gold);
  bellMesh.position.y = -0.4; bellMesh.castShadow = true;
  bell.add(bellMesh); group.add(bell);

  function update(dt, t) {
    for (const { b, geo, base, i } of banners) {
      const p = geo.attributes.position;
      for (let n = 0; n < p.count; n++) {
        const y = base[n * 3 + 1], x = base[n * 3];
        const k = (1.5 - y) / 3;     // 0 at top, 1 at bottom
        p.setZ(n, Math.sin(t * 2.2 + k * 3 + i + x * 2) * 0.16 * k);
      }
      p.needsUpdate = true;
    }
    bell.rotation.z = Math.sin(t * 1.6) * 0.22;
  }
  update(0, 0);
  return { group, update };
}

export function preview(scene) {
  const { group, update } = createMarketingHall();
  scene.add(group);
  return update;
}
