// The island: grass top, rocky cliff, sandy beach, animated sea, instanced scenery.
// Every repeated thing is one THREE.InstancedMesh per part (about 13 draw calls in total).

import { THREE, mat, PALETTE, canvasTexture, rnd } from "./kit.js";

const WATER_Y = -1.9;

// smooth periodic noise on the angle: gives the coast a natural wobble
const wob = th => 0.5 * Math.sin(3 * th + 1) + 0.3 * Math.sin(5 * th + 2) + 0.2 * Math.sin(9 * th + 4);
const COAST = 0.035;

/** A surface of revolution from rings [{r, y, color}], with a wobbling coast and optional jitter. */
function lathe(rings, segs, { jitter = 0, uvScale = 0 } = {}) {
  const pos = [], col = [], uv = [], idx = [];
  const c = new THREE.Color();
  rings.forEach((ring, ri) => {
    for (let s = 0; s <= segs; s++) {
      const th = (s % segs) / segs * Math.PI * 2;
      let r = ring.r * (1 + COAST * wob(th));
      if (jitter && ri > 0) r += (rnd(s % segs, ri) - 0.5) * jitter;
      const y = ring.y + (jitter && ri > 0 ? (rnd(s % segs, ri + 40) - 0.5) * jitter * 0.6 : 0);
      const x = Math.cos(th) * r, z = Math.sin(th) * r;
      pos.push(x, y, z);
      const k = typeof ring.color === "function" ? ring.color(x, z) : ring.color;
      c.set(k); col.push(c.r, c.g, c.b);
      uv.push(x * uvScale, z * uvScale);
    }
  });
  const row = segs + 1;
  for (let ri = 0; ri < rings.length - 1; ri++) for (let s = 0; s < segs; s++) {
    const a = ri * row + s, b = a + 1, d = a + row, e = d + 1;
    idx.push(a, b, d, b, e, d);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

function grassTexture(R) {
  const tile = 14;
  return canvasTexture("nature-grass", 128, (ctx, n) => {
    ctx.fillStyle = "#86bd55"; ctx.fillRect(0, 0, n, n);
    const wrap = (x, y, r, fill) => {
      ctx.fillStyle = fill;
      for (const ox of [-n, 0, n]) for (const oy of [-n, 0, n]) {
        ctx.beginPath(); ctx.arc(x + ox, y + oy, r, 0, 7); ctx.fill();
      }
    };
    for (let i = 0; i < 46; i++) {
      const l = rnd(i, 3) > 0.5;
      wrap(rnd(i, 1) * n, rnd(i, 2) * n, 6 + rnd(i, 4) * 14, l ? "rgba(168,214,96,0.35)" : "rgba(90,150,64,0.30)");
    }
    for (let i = 0; i < 260; i++) {
      const x = rnd(i, 11) * n, y = rnd(i, 12) * n;
      ctx.fillStyle = rnd(i, 13) > 0.5 ? "rgba(70,130,50,0.5)" : "rgba(190,226,120,0.55)";
      ctx.fillRect(x, y, 1, 2 + rnd(i, 14) * 2);
    }
    for (let i = 0; i < 10; i++) wrap(rnd(i, 21) * n, rnd(i, 22) * n, 1.2, "rgba(255,240,170,0.7)");
  }, [R / tile * 2, R / tile * 2]);
}

/** Build an InstancedMesh from item descriptors {x,y,z,ry,s,sx,sy,sz,color}. */
function inst(geo, material, items, { cast = true, receive = false } = {}) {
  const m = new THREE.InstancedMesh(geo, material, Math.max(1, items.length));
  const d = new THREE.Object3D(), c = new THREE.Color();
  items.forEach((it, i) => {
    d.position.set(it.x, it.y || 0, it.z);
    d.rotation.set(it.rx || 0, it.ry || 0, it.rz || 0);
    const s = it.s || 1;
    d.scale.set(it.sx || s, it.sy || s, it.sz || s);
    d.updateMatrix(); m.setMatrixAt(i, d.matrix);
    if (it.color !== undefined) m.setColorAt(i, c.set(it.color));
  });
  m.count = items.length;
  m.instanceMatrix.needsUpdate = true;
  if (m.instanceColor) m.instanceColor.needsUpdate = true;
  m.castShadow = cast; m.receiveShadow = receive; m.frustumCulled = false;
  return m;
}

const jitterColor = (hex, i, seed, h = 0.02, s = 0.08, l = 0.07) =>
  new THREE.Color(hex).offsetHSL((rnd(i, seed) - 0.5) * h, (rnd(i, seed + 1) - 0.5) * s, (rnd(i, seed + 2) - 0.5) * l);

// ---------- part geometries ----------
function merged(list) {
  const gs = list.map(g => g.index ? g.toNonIndexed() : g);
  let n = 0; for (const g of gs) n += g.attributes.position.count;
  const P = new Float32Array(n * 3), N = new Float32Array(n * 3);
  let o = 0;
  for (const g of gs) {
    P.set(g.attributes.position.array, o * 3); N.set(g.attributes.normal.array, o * 3); o += g.attributes.position.count;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.BufferAttribute(P, 3));
  out.setAttribute("normal", new THREE.BufferAttribute(N, 3));
  return out;
}
const at = (g, x, y, z, sx = 1, sy = 1, sz = 1, ry = 0, rz = 0) => {
  g.applyMatrix4(new THREE.Matrix4().compose(new THREE.Vector3(x, y, z),
    new THREE.Quaternion().setFromEuler(new THREE.Euler(0, ry, rz)), new THREE.Vector3(sx, sy, sz)));
  return g;
};
// LOW is set before the first build: fewer sides per cone and sphere for a software renderer
let LOW = false;
const cone = (r, h, seg = 8) => new THREE.ConeGeometry(r, h, LOW ? Math.min(seg, 5) : seg);
const blob = (r, w = 7, h = 5) => new THREE.SphereGeometry(r, LOW ? Math.max(4, w - 2) : w, LOW ? Math.max(3, h - 1) : h);

const GEO = {};
function geos() {
  if (GEO.trunk) return GEO;
  GEO.trunk = at(new THREE.CylinderGeometry(0.16, 0.26, 1.7, 6), 0, 0.85, 0);
  GEO.pine = merged([
    at(cone(1.55, 2.0), 0, 1.7, 0), at(cone(1.2, 1.8), 0, 2.7, 0, 1, 1, 1, 0.4),
    at(cone(0.85, 1.6), 0, 3.6, 0, 1, 1, 1, 0.8), at(cone(0.45, 1.1), 0, 4.4, 0),
  ]);
  GEO.round = merged([
    at(blob(1.45, 7, 5), 0, 2.5, 0, 1, 0.9, 1), at(blob(1.0, 6, 4), 0.95, 2.1, 0.25), at(blob(1.0, 6, 4), -0.85, 2.25, -0.4),
    at(blob(0.85, 6, 4), 0.2, 3.2, -0.2),
  ]);
  GEO.bush = merged([at(blob(0.6, 7, 5), 0, 0.4, 0, 1, 0.8, 1), at(blob(0.45, 7, 5), 0.5, 0.3, 0.1), at(blob(0.42, 7, 5), -0.4, 0.3, -0.2)]);
  GEO.rock = new THREE.IcosahedronGeometry(1, 0);
  GEO.stem = at(new THREE.CylinderGeometry(0.015, 0.02, 0.4, 3), 0, 0.2, 0);
  GEO.head = at(new THREE.SphereGeometry(0.1, 6, 4), 0, 0.42, 0, 1, 0.7, 1);
  GEO.tuft = merged([
    at(cone(0.07, 0.55, 3), 0, 0.27, 0, 1, 1, 1, 0, 0.0), at(cone(0.06, 0.45, 3), 0.1, 0.22, 0.03, 1, 1, 1, 1, -0.3),
    at(cone(0.06, 0.45, 3), -0.09, 0.22, -0.04, 1, 1, 1, 2, 0.3), at(cone(0.05, 0.38, 3), 0.02, 0.19, 0.1, 1, 1, 1, 3, 0.25),
  ]);
  return GEO;
}

/**
 * `detail` 1 is the full island; below 1 (e.g. 0.35 for a renderer without a graphics card) scatters
 * fewer flowers and tufts, uses simpler shapes and an opaque, slower sea.
 */
export function createNature({ radius = 62, keepClear = () => false, detail = 1 } = {}) {
  const R = radius, Rg = R * 0.85, W = R - Rg;
  LOW = detail < 1;
  const g = geos();
  const group = new THREE.Group();

  // ---- grass top (texture + soft large-scale colour variation) ----
  const gs = (x, z) => {
    const n = 0.5 + 0.25 * Math.sin(x * 0.11 + 1) * Math.cos(z * 0.09) + 0.2 * Math.sin((x + z) * 0.23) + 0.12 * Math.sin(x * 0.41 - z * 0.37);
    return new THREE.Color("#c4dd96").lerp(new THREE.Color("#ffffff"), Math.min(1, Math.max(0, n)));
  };
  const gRings = [];
  const NR = 16;
  for (let i = 0; i <= NR; i++) gRings.push({ r: Rg * i / NR, y: i === NR ? -0.02 : 0, color: gs });
  const grassMat = new THREE.MeshStandardMaterial({ map: grassTexture(Rg), vertexColors: true, roughness: 0.95 });
  grassMat.map.magFilter = THREE.LinearFilter;
  grassMat.map.anisotropy = 4;
  const grass = new THREE.Mesh(lathe(gRings, 72, { uvScale: 1 / (14 * 1) }), grassMat);
  grass.receiveShadow = true;
  group.add(grass);

  // ---- cliff and beach ----
  const rim = lathe([
    { r: Rg, y: -0.02, color: "#7fa84c" },
    { r: Rg + 0.2, y: -0.35, color: "#8d8a62" },
    { r: Rg + 0.45, y: -0.9, color: "#8a8272" },
    { r: Rg + 0.8, y: -1.2, color: "#6c665c" },
    { r: Rg + 1.7, y: -1.28, color: "#efdca0" },
    { r: Rg + W * 0.75, y: -1.95, color: "#e8d494" },
    { r: Rg + W * 0.95, y: -2.4, color: "#c9b479" },
    { r: Rg + W * 1.3, y: -4.5, color: "#7d7352" },
  ], 72, { jitter: 0.35 });
  const rimMesh = new THREE.Mesh(rim, mat("#ffffff", { vertexColors: true, roughness: 0.95 }));
  rimMesh.receiveShadow = true; rimMesh.castShadow = true;
  group.add(rimMesh);

  // ---- sea: low-poly plane with CPU waves (41x41 verts) ----
  const SEG = 40, SIZE = R * 8;
  const seaGeo = new THREE.PlaneGeometry(SIZE, SIZE, SEG, SEG);
  seaGeo.rotateX(-Math.PI / 2);
  seaGeo.setAttribute("color", new THREE.BufferAttribute(new Float32Array(seaGeo.attributes.position.count * 3), 3));
  // an opaque sea in low detail: a see-through plane under the whole screen costs a blend per pixel
  const sea = new THREE.Mesh(seaGeo, LOW ? mat("#ffffff", { vertexColors: true, roughness: 0.3 }) : mat("#ffffff", { vertexColors: true, roughness: 0.3, transparent: true, opacity: 0.93 }));
  sea.position.y = WATER_Y; sea.frustumCulled = false; sea.receiveShadow = true;
  group.add(sea);
  const sp = seaGeo.attributes.position, sc = seaGeo.attributes.color;
  const base = new Float32Array(sp.count * 2);
  for (let i = 0; i < sp.count; i++) { base[i * 2] = sp.getX(i); base[i * 2 + 1] = sp.getZ(i); }
  const deep = new THREE.Color("#2b86b8"), shallow = new THREE.Color("#58c4d0"), tmp = new THREE.Color();
  const waves = (x, z, t) => Math.sin(x * 0.18 + t * 0.9) * 0.1 + Math.sin(z * 0.23 - t * 0.7) * 0.09 + Math.sin((x + z) * 0.11 + t * 0.5) * 0.08;
  const updateSea = t => {
    for (let i = 0; i < sp.count; i++) {
      const x = base[i * 2], z = base[i * 2 + 1];
      const w = waves(x, z, t);
      sp.setY(i, w);
      const d = Math.hypot(x, z);
      const k = Math.min(1, Math.max(0, (d - R) / (R * 1.2))) * 0.8 + w * 1.2;
      tmp.copy(shallow).lerp(deep, Math.min(1, Math.max(0, k)));
      sc.setXYZ(i, tmp.r, tmp.g, tmp.b);
    }
    sp.needsUpdate = true; sc.needsUpdate = true;
  };
  updateSea(0);

  // ---- foam ring hugging the shore ----
  const foamR = Rg + W * 0.74;
  const foamGeo = lathe([{ r: foamR, y: 0, color: "#ffffff" }, { r: foamR + 0.55, y: 0, color: "#ffffff" }], 72);
  const foamMat = mat("#ffffff", { transparent: true, opacity: 0.55, roughness: 1, depthWrite: false, flatShading: false });
  const foamMatOwn = foamMat.clone(); // own opacity animation
  const foam = new THREE.Mesh(foamGeo, foamMatOwn);
  foam.position.y = WATER_Y + 0.07; foam.renderOrder = 2;
  group.add(foam);

  // ---- scatter helpers ----
  const taken = []; // {x,z,r}
  const free = (x, z, r) => {
    if (keepClear(x, z) || keepClear(x + r, z) || keepClear(x - r, z) || keepClear(x, z + r) || keepClear(x, z - r)) return false;
    for (const t of taken) { const dx = t.x - x, dz = t.z - z, m = t.r + r; if (dx * dx + dz * dz < m * m) return false; }
    return true;
  };
  const spot = (i, seed, rMin, rMax, rad, reserve = true) => {
    for (let a = 0; a < 14; a++) {
      const th = rnd(i * 17 + a, seed) * Math.PI * 2;
      const lim = (Rg * (1 + COAST * wob(th)) - 1.2);
      const r = Math.min(lim, lim * (rMin + (rMax - rMin) * Math.sqrt(rnd(i * 17 + a, seed + 5))));
      const x = Math.cos(th) * r, z = Math.sin(th) * r;
      if (free(x, z, rad)) { if (reserve) taken.push({ x, z, r: rad }); return { x, z }; }
    }
    return null;
  };
  const scale = Math.max(0.6, R / 62) ** 0.5; // smaller islands: fewer trees
  const nTrees = Math.round(200 * Math.min(1, (R / 62) ** 2 * 1.4));

  // ---- trees ----
  const pines = [], rounds = [], trunks = [];
  const greens = ["#2e7d5b", "#2a6f4e", "#3a8a5f", "#1f6a55", "#33835a"];
  const leafs = ["#5f9e3a", "#6fae45", "#4f9140", "#86b83f", "#68a840"];
  for (let i = 0; i < nTrees; i++) {
    const isPine = rnd(i, 7) < 0.46;
    const s = (isPine ? 0.8 + rnd(i, 8) * 0.8 : 0.75 + rnd(i, 8) * 0.65) * (0.9 + 0.1 * scale);
    const p = spot(i, 100, 0.12, 1.0, s * (isPine ? 1.15 : 1.25));
    if (!p) continue;
    const ry = rnd(i, 9) * 6.28;
    trunks.push({ x: p.x, y: 0, z: p.z, ry, sx: s, sy: s * (isPine ? 0.9 : 1), sz: s, color: jitterColor(PALETTE.wood, i, 30) });
    if (isPine) {
      pines.push({ x: p.x, y: 0, z: p.z, ry, sx: s, sy: s * (0.9 + rnd(i, 12) * 0.35), sz: s, color: jitterColor(greens[i % greens.length], i, 40, 0.03, 0.1, 0.08) });
    } else {
      const q = rnd(i, 13);
      const hex = q < 0.1 ? "#e8913a" : q < 0.16 ? "#ee8fb0" : q < 0.2 ? "#d7c04a" : leafs[i % leafs.length];
      rounds.push({ x: p.x, y: 0, z: p.z, ry, sx: s, sy: s * (0.9 + rnd(i, 14) * 0.3), sz: s, color: jitterColor(hex, i, 50, 0.03, 0.1, 0.08) });
    }
  }
  const white = mat("#ffffff");
  group.add(inst(g.trunk, white, trunks, { receive: true }));
  group.add(inst(g.pine, white, pines, { receive: true }));
  group.add(inst(g.round, white, rounds, { receive: true }));

  // ---- bushes ----
  const bushes = [];
  for (let i = 0; i < 70; i++) {
    const s = 0.7 + rnd(i, 61) * 0.8;
    const p = spot(i, 200, 0.1, 1.0, s * 0.8);
    if (!p) continue;
    const q = rnd(i, 62);
    bushes.push({ x: p.x, y: 0, z: p.z, ry: rnd(i, 63) * 6.28, s, color: jitterColor(q < 0.15 ? "#4a8a3a" : q < 0.3 ? "#9ac04a" : "#5f9e3a", i, 64) });
  }
  group.add(inst(g.bush, white, bushes, { receive: true }));

  // ---- rocks: on the meadow, along the cliff top and a few pebbles on the beach ----
  const rocks = [];
  const stones = ["#9b9384", "#8a8478", "#b0a898", "#7d776c", "#a69c88"];
  for (let i = 0; i < 40; i++) {
    const s = 0.35 + Math.pow(rnd(i, 71), 2) * 1.0;
    const p = spot(i, 300, 0.1, 1.0, s * 0.9);
    if (!p) continue;
    rocks.push({ x: p.x, y: s * 0.15, z: p.z, ry: rnd(i, 72) * 6.28, sx: s * (0.9 + rnd(i, 73) * 0.7), sy: s * (0.55 + rnd(i, 74) * 0.4), sz: s * (0.9 + rnd(i, 75) * 0.5), color: jitterColor(stones[i % 5], i, 76, 0, 0.05, 0.08) });
  }
  for (let i = 0; i < 44; i++) { // cliff-edge boulders
    const th = (i + rnd(i, 81) * 0.8) / 44 * Math.PI * 2;
    const s = 0.7 + rnd(i, 82) * 1.1;
    const r = (Rg + 0.15 + rnd(i, 83) * 0.7) * (1 + COAST * wob(th));
    const x = Math.cos(th) * r, z = Math.sin(th) * r;
    if (keepClear(x, z)) continue;
    rocks.push({ x, y: -0.55 + s * 0.15, z, ry: rnd(i, 84) * 6.28, sx: s * 1.1, sy: s * (0.7 + rnd(i, 85) * 0.5), sz: s, color: jitterColor(i % 3 ? "#9a9384" : "#857f72", i, 86, 0, 0.05, 0.1) });
  }
  for (let i = 0; i < 40; i++) { // beach pebbles and shore rocks
    const th = rnd(i, 91) * Math.PI * 2, s = 0.18 + rnd(i, 92) * (i % 5 === 0 ? 0.9 : 0.3);
    const r = (Rg + 2 + rnd(i, 93) * W * 0.65) * (1 + COAST * wob(th));
    rocks.push({ x: Math.cos(th) * r, y: -1.4 + s * 0.2, z: Math.sin(th) * r, ry: rnd(i, 94) * 6.28, sx: s * 1.2, sy: s * 0.7, sz: s, color: jitterColor("#aaa090", i, 95, 0, 0.05, 0.12) });
  }
  group.add(inst(g.rock, mat("#ffffff"), rocks, { receive: true }));

  // ---- flowers (clumps) ----
  const stems = [], heads = [];
  const petals = ["#ffffff", "#ffd84a", "#ff7a9c", "#c78bff", "#ff9a4a", "#7ec8ff", "#ff5d5d"];
  for (let c = 0; c < Math.round(80 * detail); c++) {
    const p = spot(c, 400, 0.05, 1.0, 0.4, false);
    if (!p) continue;
    const hex = petals[Math.floor(rnd(c, 401) * petals.length)];
    for (let k = 0; k < 5; k++) {
      const x = p.x + (rnd(c * 5 + k, 402) - 0.5) * 1.8, z = p.z + (rnd(c * 5 + k, 403) - 0.5) * 1.8;
      if (keepClear(x, z) || Math.hypot(x, z) > Rg - 1) continue;
      const s = 0.8 + rnd(c * 5 + k, 404) * 0.7;
      stems.push({ x, y: 0, z, s });
      heads.push({ x, y: 0, z, s, color: k === 4 ? "#ffe97a" : hex });
    }
  }
  group.add(inst(g.stem, mat("#4f8f3a"), stems, { cast: false }));
  group.add(inst(g.head, white, heads, { cast: false }));

  // ---- grass tufts ----
  const tufts = [];
  for (let i = 0; i < Math.round(480 * detail); i++) {
    const p = spot(i, 500, 0.0, 1.0, 0.05, false);
    if (!p) continue;
    const s = 0.8 + rnd(i, 501) * 1.0;
    tufts.push({ x: p.x, y: 0, z: p.z, ry: rnd(i, 502) * 6.28, s, color: jitterColor(i % 4 ? "#6aa83f" : "#9ccb4f", i, 503, 0.03, 0.1, 0.1) });
  }
  group.add(inst(g.tuft, white, tufts, { cast: false }));

  let acc = 0;
  const update = (dt, t) => {
    acc += dt;
    if (acc >= (LOW ? 1 / 12 : 1 / 30)) { acc = 0; updateSea(t); } // gentle waves need few updates
    foamMatOwn.opacity = 0.4 + 0.2 * Math.sin(t * 1.3);
    foam.scale.setScalar(1 + 0.004 * Math.sin(t * 0.9));
  };
  return { group, update };
}

export function preview(scene) {
  const keepClear = (x, z) => Math.hypot(x, z) < 5.5 || (Math.abs(x) < 2.2 && Math.abs(z) < 28) || (Math.abs(z) < 2.2 && Math.abs(x) < 28);
  const { group, update } = createNature({ radius: 30, keepClear });
  // the preview's own 200 m ground plane would hide the island: switch it off
  scene.traverse(o => { if (o.isMesh && o.geometry.parameters && o.geometry.parameters.width === 200) o.visible = false; });
  scene.add(group);
  return update;
}
