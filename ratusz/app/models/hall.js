// The Hall of Progress: grand guild hall with clock tower, golden spire, plaza, steps, banners,
// lanterns, a fountain and a notice board. Static parts are merged per material.
import { THREE, mat, glow, PALETTE, placed, mergeByMaterial, canvasTexture, rnd } from "./kit.js";

const PI = Math.PI;

// ---------- textures ----------
function stoneTex() {
  return canvasTexture("hall-stone", 64, (c, s) => {
    c.fillStyle = "#7d766a"; c.fillRect(0, 0, s, s);
    const rows = 4, rh = s / rows;
    for (let r = 0; r < rows; r++) {
      const bw = s / 2, off = (r % 2) * bw / 2;
      for (let k = -1; k < 3; k++) {
        const sh = 0.82 + rnd(r * 7 + k, 3) * 0.3;
        c.fillStyle = `rgb(${180 * sh | 0},${172 * sh | 0},${156 * sh | 0})`;
        c.fillRect(k * bw + off + 1, r * rh + 1, bw - 2, rh - 2);
      }
    }
  });
}
function roofTex() {
  return canvasTexture("hall-roof", 64, (c, s) => {
    c.fillStyle = "#7a2a24"; c.fillRect(0, 0, s, s);
    const rows = 8, rh = s / rows, tw = s / 4;
    for (let r = 0; r < rows; r++) {
      const off = (r % 2) * tw / 2;
      for (let k = -1; k < 5; k++) {
        const sh = 0.85 + rnd(r * 5 + k, 9) * 0.3;
        c.fillStyle = `rgb(${200 * sh | 0},${70 * sh | 0},${58 * sh | 0})`;
        c.fillRect(k * tw + off + 1, r * rh, tw - 2, rh - 1);
        c.fillStyle = "rgba(60,15,10,0.45)"; c.fillRect(k * tw + off + 1, r * rh + rh - 3, tw - 2, 2);
      }
    }
  });
}
function pavingTex() {
  return canvasTexture("hall-paving", 64, (c, s) => {
    c.fillStyle = "#6f695e"; c.fillRect(0, 0, s, s);
    const n = 4, h = s / n;
    for (let r = 0; r < n; r++) for (let k = -1; k < n; k++) {
      const sh = 0.8 + rnd(r * 11 + k, 5) * 0.4, off = (r % 2) * h / 2;
      c.fillStyle = `rgb(${186 * sh | 0},${176 * sh | 0},${158 * sh | 0})`;
      c.fillRect(k * h + off + 1.5, r * h + 1.5, h - 3, h - 3);
    }
  }, [9, 9]);
}
function bannerTex() {
  return canvasTexture("hall-banner", 64, (c, s) => {
    c.fillStyle = "#b8352f"; c.fillRect(0, 0, s, s);
    c.strokeStyle = PALETTE.gold; c.lineWidth = 5; c.strokeRect(4, 4, s - 8, s - 8);
    c.fillStyle = PALETTE.gold;
    c.beginPath(); c.moveTo(s / 2, 12); c.lineTo(s - 16, s / 2); c.lineTo(s / 2, s - 12); c.lineTo(16, s / 2); c.closePath(); c.fill();
    c.fillStyle = "#b8352f"; c.beginPath(); c.arc(s / 2, s / 2, 8, 0, PI * 2); c.fill();
  });
}
const texMat = (map, extra = {}) => new THREE.MeshStandardMaterial({ color: "#ffffff", map, roughness: 0.85, flatShading: true, ...extra });

export function createHall() {
  const group = new THREE.Group();
  const parts = [];
  let M = null; // optional outer transform for a sub-assembly
  const P = (g, m) => { if (M) g.applyMatrix4(M); parts.push([g, m]); };

  const mPave = texMat(pavingTex());
  const mStone = texMat(stoneTex());
  const mRoof = texMat(roofTex());
  const mStoneL = mat(PALETTE.stoneLight);
  const mPlaster = mat(PALETTE.plaster);
  const mDark = mat(PALETTE.woodDark);
  const mWood = mat(PALETTE.wood);
  const mBlue = mat(PALETTE.roofBlue);
  const mGold = mat(PALETTE.gold, { roughness: 0.35, metalness: 0.3 });
  const mWin = glow(PALETTE.window, 1.1);
  const mWater = mat("#5fb8d8", { roughness: 0.2, flatShading: false });
  const mLeaf = mat(PALETTE.leaf);

  // box with its base at y0 (or centred when o.c), uv scaled to world size when o.tile
  const B = (w, h, d, x, y0, z, m, o = {}) => {
    const g = new THREE.BoxGeometry(w, h, d);
    if (o.tile) {
      const uv = g.attributes.uv, sz = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];
      for (let i = 0; i < uv.count; i++) { const f = i >> 2; uv.setXY(i, uv.getX(i) * sz[f][0] / o.tile, uv.getY(i) * sz[f][1] / o.tile); }
    }
    P(placed(g, { x, y: o.c ? y0 : y0 + h / 2, z, rx: o.rx, ry: o.ry, rz: o.rz }), m);
  };
  const C = (r, h, seg, x, y0, z, m, o = {}) => P(placed(new THREE.CylinderGeometry(o.rt ?? r, r, h, seg), { x, y: y0 + h / 2, z, rx: o.rx, ry: o.ry, rz: o.rz }), m);
  const S = (r, x, y, z, m, sy = 1) => P(placed(new THREE.SphereGeometry(r, 8, 6), { x, y, z, sy }), m);

  // ---------- plaza ----------
  P(placed(new THREE.CylinderGeometry(9.5, 9.7, 0.1, 24), { y: 0.05 }), mStone);
  P(placed(new THREE.CylinderGeometry(9, 9, 0.16, 24), { y: 0.08 }), mPave);
  P(placed(new THREE.RingGeometry(6, 6.3, 24), { y: 0.165, rx: -PI / 2 }), mGold);
  P(placed(new THREE.RingGeometry(3.2, 3.4, 24), { y: 0.166, rx: -PI / 2 }), mGold);

  // ---------- base, steps ----------
  const BX = 6.7, BZ0 = -4, BZ1 = 4;
  B(BX * 2, 1.2, BZ1 - BZ0, 0, 0, (BZ0 + BZ1) / 2, mStone, { tile: 2 });
  B(BX * 2 + 0.3, 0.15, BZ1 - BZ0 + 0.3, 0, 1.2, 0, mStoneL);
  B(7, 0.4, 1.8, 0, 0, 4.9, mStone, { tile: 2 });
  B(6.4, 0.8, 1.2, 0, 0, 4.6, mStone, { tile: 2 });
  B(5.8, 1.2 - 0.0, 0.6, 0, 0, 4.3, mStone, { tile: 2 });
  for (const s of [-1, 1]) { // step cheeks
    B(0.5, 0.9, 2.0, s * 3.7, 0, 4.8, mStoneL);
    B(0.6, 0.12, 2.1, s * 3.7, 0.9, 4.8, mStoneL);
  }

  // ---------- main block ----------
  const W0 = 1.35, WH = 4.0, WT = W0 + WH; // wall y range 1.35..5.35
  B(11.6, WH, 5.4, 0, W0, 0, mPlaster);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) B(0.45, WH, 0.45, sx * 5.8, W0, sz * 2.7, mStoneL); // quoins
  B(11.8, 0.22, 0.22, 0, WT - 0.25, 2.72, mDark); // timber band front
  B(11.8, 0.22, 0.22, 0, WT - 0.25, -2.72, mDark);
  B(0.22, 0.22, 5.6, -5.82, WT - 0.25, 0, mDark); B(0.22, 0.22, 5.6, 5.82, WT - 0.25, 0, mDark);
  for (const x of [-4.2, -3.5, 3.5, 4.2, -5.0, 5.0]) B(0.16, WH - 0.5, 0.16, x * 1.0, W0, 2.74, mDark);
  // windows (front: |x| 2.9 ; sides)
  const win = (cx, y0, cz, w, h, axis) => {
    const fx = axis === "z" ? 1 : 0;
    const dim = (a, th) => fx ? [a, th] : [th, a];
    let [ww, dd] = dim(w + 0.22, 0.1); B(ww, h + 0.22, dd, cx, y0 - 0.11, cz, mDark);
    [ww, dd] = dim(w, 0.14); B(ww, h, dd, cx, y0, cz, mWin);
    [ww, dd] = dim(0.07, 0.2); B(ww, h, dd, cx, y0, cz, mDark);
    [ww, dd] = dim(w, 0.2); B(ww, 0.07, dd, cx, y0 + h / 2, cz, mDark, { c: false });
    [ww, dd] = dim(w + 0.5, 0.36); B(ww, 0.22, dd, cx, y0 - 0.33, cz + (fx ? 0.12 : 0), mDark);
    [ww, dd] = dim(w + 0.4, 0.3); B(ww, 0.2, dd, cx, y0 - 0.11, cz + (fx ? 0.12 : 0), mLeaf);
  };
  for (const s of [-1, 1]) {
    win(s * 2.95, 2.4, 2.72, 0.85, 1.35, "z");
    win(s * 4.75, 2.4, 2.72, 0.85, 1.35, "z");
    win(s * 5.8, 2.4, -1.2, 0.85, 1.35, "x");
    win(s * 5.8, 2.4, 1.2, 0.85, 1.35, "x");
  }
  // gable ends + roof
  const shape = new THREE.Shape(); shape.moveTo(-2.7, 0); shape.lineTo(2.7, 0); shape.lineTo(0, 2.1); shape.closePath();
  const gab = new THREE.ExtrudeGeometry(shape, { depth: 11.6, bevelEnabled: false }); gab.translate(0, 0, -5.8);
  P(placed(gab, { y: WT, ry: PI / 2 }), mPlaster);
  const RISE = 2.2, HALF = 3.3, slope = Math.hypot(HALF, RISE), ang = Math.atan2(RISE, HALF);
  for (const s of [-1, 1]) B(12.8, 0.22, slope + 0.1, 0, WT + RISE / 2 + 0.11, s * HALF / 2, mRoof, { c: true, rx: s * ang, tile: 2 });
  B(13.0, 0.2, 0.34, 0, WT + RISE + 0.2, 0, mDark, { c: true });
  for (const s of [-1, 1]) {
    P(placed(new THREE.ConeGeometry(0.2, 0.8, 6), { x: s * 6.55, y: WT + RISE + 0.6 }), mGold);
    S(0.15, s * 6.55, WT + RISE + 1.05, 0, mGold);
  }

  // ---------- clock tower ----------
  const TZ = 1.4, TH = 9.1, TW = 3.4, TF = TZ + TW / 2;
  B(TW, TH - 1.2, TW, 0, 1.2, TZ, mPlaster);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) B(0.34, TH - 1.2, 0.34, sx * TW / 2, 1.2, TZ + sz * TW / 2, mStoneL);
  B(TW + 0.5, 0.3, TW + 0.5, 0, TH, TZ, mStoneL);
  B(TW + 0.2, 0.2, TW + 0.2, 0, 5.95, TZ, mStoneL); // band
  P(placed(new THREE.ConeGeometry(2.83, 1.7, 4), { y: TH + 0.3 + 0.85, z: TZ, ry: PI / 4 }), mBlue);
  S(0.3, 0, TH + 2.1, TZ, mGold);
  P(placed(new THREE.ConeGeometry(0.22, 1.5, 6), { y: TH + 2.35 + 0.75, z: TZ }), mGold);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) { // corner finials
    P(placed(new THREE.ConeGeometry(0.16, 0.6, 5), { x: sx * 1.95, y: TH + 0.6, z: TZ + sz * 1.95 }), mGold);
  }
  // belfry windows on the sides, arch door and wall lanterns on the front
  for (const s of [-1, 1]) {
    B(0.14, 1.2, 0.8, s * (TW / 2 + 0.02), 7.5, TZ, mWin);
    B(0.2, 0.12, 1.0, s * (TW / 2 + 0.02), 8.7, TZ, mDark);
  }
  B(2.0, 2.7, 0.14, 0, 1.2, TF + 0.01, mStoneL); C(1.0, 0.14, 8, 0, 3.9, TF + 0.01, mStoneL, { rx: PI / 2 });
  B(1.6, 2.6, 0.2, 0, 1.2, TF + 0.04, mDark); C(0.8, 0.2, 8, 0, 3.8, TF + 0.04, mDark, { rx: PI / 2 });
  B(0.06, 3.4, 0.24, 0, 1.2, TF + 0.06, mGold);
  B(0.18, 0.18, 0.08, 0.3, 2.3, TF + 0.18, mGold);
  for (const s of [-1, 1]) {
    B(0.06, 0.06, 0.4, s * 1.35, 3.0, TF + 0.2, mDark);
    B(0.26, 0.38, 0.26, s * 1.35, 2.62, TF + 0.4, mWin);
    P(placed(new THREE.ConeGeometry(0.22, 0.2, 4), { x: s * 1.35, y: 3.1, z: TF + 0.4, ry: PI / 4 }), mGold);
  }
  // clock face (front)
  const CY = 7.5;
  C(1.15, 0.1, 12, 0, CY - 0.05, TF + 0.02, mGold, { rx: PI / 2, ry: 0 });
  C(1.0, 0.12, 12, 0, CY - 0.06, TF + 0.04, mPlaster, { rx: PI / 2 });
  for (let i = 0; i < 12; i++) {
    const a = i / 12 * PI * 2;
    B(i % 3 ? 0.07 : 0.12, i % 3 ? 0.16 : 0.24, 0.05, Math.sin(a) * 0.82, CY + Math.cos(a) * 0.82, TF + 0.12, mDark, { c: true, rz: -a });
  }

  // ---------- fountain ----------
  M = new THREE.Matrix4().makeTranslation(-6.1, 0.16, 5.2);
  C(1.25, 0.55, 8, 0, 0, 0, mStoneL, { rt: 1.35 });
  C(1.05, 0.5, 8, 0, 0.05, 0, mWater);
  C(0.22, 1.2, 6, 0, 0.1, 0, mStoneL, { rt: 0.16 });
  C(0.65, 0.2, 8, 0, 0.95, 0, mStoneL, { rt: 0.3 });
  C(0.5, 0.06, 8, 0, 1.12, 0, mWater);
  S(0.2, 0, 1.4, 0, mWater);
  // ---------- notice board ----------
  M = new THREE.Matrix4().compose(new THREE.Vector3(6.3, 0.16, 5.0), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -0.55, 0)), new THREE.Vector3(1, 1, 1));
  for (const s of [-1, 1]) B(0.18, 2.8, 0.18, s * 1.25, 0, 0, mDark);
  B(2.8, 1.7, 0.12, 0, 0.9, 0, mWood);
  B(3.0, 0.14, 0.4, 0, 2.6, 0.02, mDark, { c: false });
  P(placed(new THREE.BoxGeometry(3.3, 0.12, 0.7), { y: 2.85, z: 0.02, rx: -0.3 }), mDark);
  for (let i = 0; i < 7; i++) {
    const px = -1.05 + (i % 4) * 0.7 + rnd(i, 2) * 0.15, py = i < 4 ? 1.95 : 1.4;
    B(0.5, 0.36 + rnd(i, 4) * 0.12, 0.03, px, py, 0.08, mPlaster, { rz: (rnd(i, 7) - 0.5) * 0.25, c: false });
    S(0.04, px, py + 0.4, 0.1, mGold);
  }
  B(2.8, 0.1, 0.1, 0, 0.75, 0.06, mDark);
  // barrels
  C(0.38, 0.75, 8, 1.9, 0, 0.9, mWood, { rt: 0.32 }); C(0.38, 0.75, 8, 2.5, 0, 0.5, mWood, { rt: 0.32 });
  M = null;

  // ---------- lamp posts & hedges ----------
  const lamp = (x, z, h = 2.3) => {
    C(0.07, h, 6, x, 0.16, z, mDark, { rt: 0.07 });
    B(0.32, 0.4, 0.32, x, 0.16 + h, z, mWin);
    P(placed(new THREE.ConeGeometry(0.28, 0.25, 4), { x, y: 0.16 + h + 0.5, z, ry: PI / 4 }), mGold);
    C(0.16, 0.2, 6, x, 0.16, z, mStoneL, { rt: 0.2 });
  };
  for (let k = 0; k < 8; k++) { const a = (k + 0.5) / 8 * PI * 2; lamp(Math.cos(a) * 7.7, Math.sin(a) * 7.7); }
  for (const s of [-1, 1]) {
    lamp(s * 3.7, 5.6, 1.6);
    S(0.55, s * 5.2, 0.55, 5.2, mLeaf, 0.9); S(0.45, s * 5.2, 0.35, 6.0, mLeaf, 0.8);
    S(0.5, s * 6.2, 0.45, -3.2, mLeaf, 0.9);
  }

  // ---------- banners (moving) ----------
  const bannerMat = texMat(bannerTex(), { side: THREE.DoubleSide, flatShading: false });
  const banners = [];
  for (const s of [-1, 1]) {
    const geo = new THREE.PlaneGeometry(1.3, 2.7, 2, 9);
    geo.translate(0, -1.35, 0);
    const mesh = new THREE.Mesh(geo, bannerMat);
    mesh.position.set(s * 4.75, 5.2, 2.9);
    mesh.castShadow = true;
    group.add(mesh);
    banners.push({ mesh, base: geo.attributes.position.array.slice(), ph: s });
    parts.push([placed(new THREE.CylinderGeometry(0.05, 0.05, 1.7, 6), { x: s * 4.75, y: 5.25, z: 2.88, rz: PI / 2 }), mGold]);
    parts.push([placed(new THREE.SphereGeometry(0.1, 6, 5), { x: s * 4.75 - 0.85, y: 5.25, z: 2.88 }), mGold]);
    parts.push([placed(new THREE.SphereGeometry(0.1, 6, 5), { x: s * 4.75 + 0.85, y: 5.25, z: 2.88 }), mGold]);
  }
  // rods merge into the gold mesh: rebuild is avoided by a tiny extra merged group sharing mGold
  group.add(mergeByMaterial(parts));

  // ---------- clock hands ----------
  const handGeo = (w, l) => { const g = new THREE.BoxGeometry(w, l, 0.04); g.translate(0, l / 2 - 0.06, 0); return g; };
  const minute = new THREE.Mesh(handGeo(0.07, 0.8), mDark);
  const hour = new THREE.Mesh(handGeo(0.11, 0.52), mDark);
  minute.position.set(0, CY, TF + 0.14); hour.position.set(0, CY, TF + 0.11);
  group.add(minute, hour);

  function update(dt, t) {
    for (const b of banners) {
      const p = b.mesh.geometry.attributes.position, a = p.array;
      for (let i = 0; i < p.count; i++) {
        const y = b.base[i * 3 + 1], k = Math.min(1, -y / 2.7);
        a[i * 3 + 2] = Math.sin(t * 2.2 + y * 2.2 + b.ph) * 0.14 * k;
        a[i * 3] = b.base[i * 3] * (1 - 0.04 * k * Math.sin(t * 2.2 + y * 2 + b.ph));
      }
      p.needsUpdate = true;
    }
    const m = t * 0.25;
    minute.rotation.z = -m * PI * 2;
    hour.rotation.z = -m * PI * 2 / 12 - 0.9;
  }
  update(0, 0);
  return { group, update };
}

export function preview(scene) {
  const hall = createHall();
  scene.add(hall.group);
  return hall.update;
}
