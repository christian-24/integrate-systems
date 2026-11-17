// Guild halls of Agent Quest: the Testers' Guild (inspector's tower, alchemy lab, status lamp) and the
// Tech Academy (library-observatory with dome, floating rune crystals, turning brass gears).
// createMarketingHall() lives in marketing-hall.js (added by the lead, see preview() below).
import { THREE, mat, glow, PALETTE, placed, mergeByMaterial, rnd } from "./kit.js";

const unit = new THREE.BoxGeometry(1, 1, 1);
const BRASS = "#c9962e";

/** Add a box (centre x,y,z; size w,h,d) to a parts list. */
const box = (parts, m, w, h, d, x, y, z, o = {}) => parts.push([placed(unit, { x, y, z, sx: w, sy: h, sz: d, ...o }), m]);
/** Add any geometry. */
const add = (parts, m, g, o = {}) => parts.push([placed(g, o), m]);

/** Triangular prism: gable roof, ridge along z, width w, height h, length d, base at y = 0. */
function prism(w, h, d) {
  const s = new THREE.Shape(); s.moveTo(-w / 2, 0); s.lineTo(w / 2, 0); s.lineTo(0, h); s.closePath();
  const g = new THREE.ExtrudeGeometry(s, { depth: d, bevelEnabled: false });
  g.translate(0, 0, -d / 2);
  return g;
}
const oct = (r, h) => new THREE.CylinderGeometry(r, r, h, 8);
const cone = (r, h, seg = 8) => new THREE.ConeGeometry(r, h, seg);
const ball = (r) => new THREE.SphereGeometry(r, 10, 8);

/** Arched opening on a +z facing wall: returns pane + frame parts. Wall surface at z. */
function archWindow(parts, panes, frame, x, y, z, w, h) {
  // frame (slightly larger), pane on top
  box(parts, frame, w + 0.24, h, 0.1, x, y, z + 0.03);
  add(parts, frame, new THREE.CylinderGeometry(w / 2 + 0.12, w / 2 + 0.12, 0.1, 8, 1, false, Math.PI / 2, Math.PI), { x, y: y + h / 2, z: z + 0.03, rx: Math.PI / 2 });
  box(parts, panes, w, h, 0.1, x, y, z + 0.06);
  add(parts, panes, new THREE.CylinderGeometry(w / 2, w / 2, 0.1, 8, 1, false, Math.PI / 2, Math.PI), { x, y: y + h / 2, z: z + 0.06, rx: Math.PI / 2 });
  box(parts, frame, w + 0.4, 0.1, 0.3, x, y - h / 2 - 0.05, z + 0.1); // sill
}

// =====================================================================================
// Testers' Guild
// =====================================================================================
const LAMP = { pass: ["#3dff72", 2.2, 0.38], fail: ["#ff3a2e", 2.2, 0.38], none: ["#c88a2a", 0.35, 0.08] };

export function createTestersGuild() {
  const group = new THREE.Group();
  const P = [];
  const stone = mat(PALETTE.stone), plaster = mat(PALETTE.plaster), wood = mat(PALETTE.woodDark);
  const roof = mat(PALETTE.roofTeal), brass = mat(BRASS, { roughness: 0.5 });
  const pane = glow(PALETTE.window, 1.1), glass = glow("#bfeaf0", 0.6);
  const flaskA = glow("#6dff9a", 1.2), flaskB = glow("#c07dff", 1.2);

  // base slab with a step
  box(P, stone, 10.6, 0.4, 8.4, 0, 0.2, 0);
  box(P, stone, 3, 0.2, 1, -3.3, 0.1, 4.6);

  // --- alchemy lab (left) ---
  const lx = -2.2, lz = 0.3;
  box(P, stone, 6.2, 0.9, 5.2, lx, 0.85, lz);
  box(P, plaster, 6, 2.4, 5, lx, 2.5, lz);
  add(P, roof, prism(7, 2.4, 6), { x: lx, y: 3.7, z: lz });
  // timber framing on the front gable wall
  for (const dx of [-3, 3]) box(P, wood, 0.3, 3.3, 0.3, lx + dx, 2.05, lz + 2.55);
  box(P, wood, 6.2, 0.22, 0.3, lx, 3.1, lz + 2.55);
  box(P, wood, 6.2, 0.22, 0.3, lx, 1.5, lz + 2.55);
  // door
  const dz = lz + 2.5;
  box(P, wood, 1.4, 2.0, 0.2, lx - 1.6, 1.4, dz + 0.02);
  add(P, wood, new THREE.CylinderGeometry(0.7, 0.7, 0.2, 8, 1, false, Math.PI / 2, Math.PI), { x: lx - 1.6, y: 2.4, z: dz + 0.02, rx: Math.PI / 2 });
  box(P, wood, 0.9, 1.7, 0.1, lx - 1.6, 1.3, dz + 0.16);
  // windows
  box(P, wood, 1.3, 1.3, 0.12, lx + 1.2, 2.5, dz + 0.04);
  box(P, pane, 1.1, 1.1, 0.12, lx + 1.2, 2.5, dz + 0.08);
  box(P, wood, 0.06, 1.1, 0.14, lx + 1.2, 2.5, dz + 0.1);
  box(P, wood, 1.1, 0.06, 0.14, lx + 1.2, 2.5, dz + 0.1);
  // chimney with a bubbling vent
  box(P, stone, 0.8, 2.2, 0.8, lx - 2.2, 5.0, lz - 1.2);
  box(P, stone, 1.0, 0.2, 1.0, lx - 2.2, 6.15, lz - 1.2);
  // side-window glow
  box(P, pane, 0.1, 1.0, 1.0, lx - 3.05, 2.4, lz);

  // alchemy table out front with flasks
  const tx = lx + 1.4, tz = 3.9;
  box(P, wood, 2.4, 0.15, 1.0, tx, 1.2, tz);
  for (const s of [-1, 1]) box(P, wood, 0.15, 0.8, 0.8, tx + s * 1.0, 0.8, tz);
  box(P, wood, 2.2, 0.1, 0.1, tx, 0.9, tz);
  for (let i = 0; i < 4; i++) {
    const fx = tx - 0.85 + i * 0.56, fm = i % 2 ? flaskB : flaskA;
    add(P, fm, ball(0.2 + 0.04 * (i % 2)), { x: fx, y: 1.5, z: tz });
    add(P, fm, new THREE.CylinderGeometry(0.06, 0.06, 0.3, 6), { x: fx, y: 1.8, z: tz });
  }
  // barrel + crate
  add(P, wood, new THREE.CylinderGeometry(0.4, 0.45, 0.8, 8), { x: lx - 3.6, y: 0.8, z: 3.5 });
  box(P, mat(PALETTE.woodLight), 0.7, 0.6, 0.7, lx - 3.4, 0.7, 2.7, { ry: 0.3 });

  // --- inspector's tower (right) ---
  const tcx = 3.2, tcz = -0.7, tr = 1.75;
  add(P, stone, oct(tr + 0.25, 1.2), { x: tcx, y: 1.0, z: tcz, ry: Math.PI / 8 });
  add(P, plaster, oct(tr, 5.2), { x: tcx, y: 3.6, z: tcz, ry: Math.PI / 8 });
  for (let k = 0; k < 4; k++) { // timber rings
    add(P, wood, oct(tr + 0.05, 0.18), { x: tcx, y: 2.2 + k * 1.2, z: tcz, ry: Math.PI / 8 });
  }
  add(P, wood, oct(2.3, 0.35), { x: tcx, y: 6.4, z: tcz, ry: Math.PI / 8 });        // balcony
  add(P, plaster, oct(1.6, 1.6), { x: tcx, y: 7.4, z: tcz, ry: Math.PI / 8 });
  for (let k = 0; k < 8; k++) { // glowing slits
    const a = k * Math.PI / 4 + Math.PI / 8 + Math.PI / 8;
    box(P, pane, 0.5, 0.8, 0.12, tcx + Math.sin(a) * 1.5, 7.4, tcz + Math.cos(a) * 1.5, { ry: a });
  }
  add(P, roof, cone(2.6, 2.4), { x: tcx, y: 9.4, z: tcz, ry: Math.PI / 8 });
  add(P, brass, cone(0.12, 0.8, 4), { x: tcx, y: 11.0, z: tcz });

  // big brass magnifying lens on the tower front (tilted a touch)
  const lensZ = tcz + tr * 0.924 + 0.25, lensY = 4.9;
  add(P, brass, new THREE.TorusGeometry(1.05, 0.17, 6, 14), { x: tcx, y: lensY, z: lensZ });
  add(P, glass, new THREE.CircleGeometry(0.95, 14), { x: tcx, y: lensY, z: lensZ - 0.02 });
  add(P, glass, new THREE.CircleGeometry(0.95, 14), { x: tcx, y: lensY, z: lensZ + 0.02 });
  box(P, brass, 0.22, 1.5, 0.22, tcx + 0.95, lensY - 1.55, lensZ, { rz: -0.7 });  // handle
  box(P, brass, 0.3, 0.3, 0.5, tcx, lensY - 1.12, lensZ - 0.25);                  // mount
  box(P, wood, 0.15, 0.15, 0.7, tcx, lensY + 1.12, lensZ - 0.3);

  // lamp pedestal in front of the tower
  const px = 5.0, pz = 3.9;
  add(P, stone, new THREE.CylinderGeometry(0.55, 0.7, 1.0, 8), { x: px, y: 0.9, z: pz });
  box(P, wood, 0.22, 2.0, 0.22, px, 2.3, pz);
  box(P, brass, 1.0, 0.14, 1.0, px, 3.2, pz);

  group.add(mergeByMaterial(P));

  // status lamps (per-guild material so each guild keeps its own colour)
  const lampMat = glow("#c88a2a", 0.35).clone();
  const haloMat = new THREE.MeshBasicMaterial({ color: "#c88a2a", transparent: true, opacity: 0.08, depthWrite: false });
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.8, 10, 8), lampMat);
  lamp.position.set(px, 4.1, pz);
  const halo = new THREE.Mesh(new THREE.SphereGeometry(1.45, 10, 8), haloMat);
  halo.position.copy(lamp.position);
  const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.36, 8, 6), lampMat);
  beacon.position.set(tcx, 11.6, tcz);
  group.add(lamp, halo, beacon);
  group.traverse(o => { if (o.isMesh) { o.castShadow = o !== halo; } });

  let status = "none";
  function setStatus(s) {
    const k = LAMP[s] ? s : "none"; status = k;
    const [c, e, o] = LAMP[k];
    lampMat.color.set(c); lampMat.emissive.set(c); lampMat.emissiveIntensity = e;
    haloMat.color.set(c); haloMat.opacity = o;
  }
  setStatus("none");

  function update(dt, t) {
    const [, e, o] = LAMP[status];
    let k = 1;
    if (status === "fail") k = 0.55 + 0.45 * (Math.sin(t * 6) > 0 ? 1 : 0.2);   // urgent blink
    else if (status === "pass") k = 0.85 + 0.15 * Math.sin(t * 2);               // calm breathing
    lampMat.emissiveIntensity = e * k;
    haloMat.opacity = o * k;
    halo.scale.setScalar(status === "none" ? 0.8 : 1 + 0.08 * Math.sin(t * 3));
  }
  return { group, update, setStatus };
}

// =====================================================================================
// Tech Academy
// =====================================================================================
function gearGeometry(r, teeth) {
  const parts = [];
  const body = new THREE.CylinderGeometry(r, r, 0.22, teeth, 1);
  body.rotateX(Math.PI / 2); parts.push(body);
  for (let i = 0; i < teeth; i++) {
    const a = (i / teeth) * Math.PI * 2;
    parts.push(placed(unit, { x: Math.cos(a) * (r + 0.1), y: Math.sin(a) * (r + 0.1), sx: 0.26, sy: 0.2, sz: 0.22, rz: a }));
  }
  // dark-looking hub cross cannot differ in colour (one material), so add raised spokes
  for (let i = 0; i < 2; i++) parts.push(placed(unit, { z: 0.14, sx: r * 1.5, sy: 0.12, sz: 0.1, rz: i * Math.PI / 2 }));
  const merged = parts.map(g => (g.index ? g.toNonIndexed() : g));
  for (const g of merged) for (const n of Object.keys(g.attributes)) if (n !== "position" && n !== "normal") g.deleteAttribute(n);
  return mergeGeoms(merged);
}
function mergeGeoms(list) {
  let n = 0; for (const g of list) n += g.attributes.position.count;
  const pos = new Float32Array(n * 3), nor = new Float32Array(n * 3);
  let o = 0;
  for (const g of list) { pos.set(g.attributes.position.array, o * 3); nor.set(g.attributes.normal.array, o * 3); o += g.attributes.position.count; }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.BufferAttribute(pos, 3)); out.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
  return out;
}

export function createTechAcademy() {
  const group = new THREE.Group();
  const P = [];
  const stone = mat(PALETTE.stone), plaster = mat("#e4d8f0"), wood = mat(PALETTE.woodDark);
  const roof = mat(PALETTE.roofBlue), dome = mat("#3fa391", { metalness: 0.2, roughness: 0.55 });
  const brass = mat(BRASS, { roughness: 0.5 });
  const pane = glow("#ffcf7a", 0.9);
  const bookA = mat("#b8473f"), bookB = mat("#4a7fb8");

  box(P, stone, 10.6, 0.4, 8.4, 0, 0.2, 0);
  box(P, stone, 3.2, 0.2, 1, 0, 0.1, 4.7);

  // rotunda
  const rz = -1.2;
  add(P, stone, oct(3.7, 1.0), { x: 0, y: 0.9, z: rz, ry: Math.PI / 8 });
  add(P, plaster, oct(3.45, 3.4), { x: 0, y: 3.1, z: rz, ry: Math.PI / 8 });
  add(P, wood, oct(3.55, 0.22), { x: 0, y: 4.9, z: rz, ry: Math.PI / 8 });
  add(P, dome, new THREE.SphereGeometry(3.5, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), { x: 0, y: 4.8, z: rz });
  add(P, brass, new THREE.TorusGeometry(3.5, 0.1, 4, 12), { x: 0, y: 4.85, z: rz, rx: Math.PI / 2 });
  add(P, brass, new THREE.CylinderGeometry(0.35, 0.5, 0.5, 6), { x: 0, y: 8.4, z: rz });
  add(P, brass, ball(0.3), { x: 0, y: 8.9, z: rz });
  // observation slit + telescope
  box(P, wood, 0.9, 2.4, 0.2, 0, 6.8, rz + 3.0, { rx: 0.62 });
  add(P, brass, new THREE.CylinderGeometry(0.2, 0.28, 2.6, 7), { x: 1.3, y: 7.3, z: rz + 2.0, rx: 1.0, rz: -0.3 });
  box(P, wood, 0.12, 1.0, 0.12, 1.1, 6.6, rz + 1.7, { rx: 0.2 });
  // rotunda glow windows (round-ish, side faces)
  for (let k = 0; k < 8; k++) {
    if (k === 0 || k === 1 || k === 7) continue; // hidden behind the front wing
    const a = k * Math.PI / 4;
    box(P, wood, 0.8, 1.5, 0.12, Math.sin(a) * 3.2, 3.2, rz + Math.cos(a) * 3.2, { ry: a });
    box(P, pane, 0.62, 1.3, 0.14, Math.sin(a) * 3.22, 3.2, rz + Math.cos(a) * 3.22, { ry: a });
  }
  // buttress pillars
  for (let k = 0; k < 4; k++) {
    const a = k * Math.PI / 2 + Math.PI / 4;
    box(P, stone, 0.5, 4.2, 0.5, Math.sin(a) * 3.6, 2.5, rz + Math.cos(a) * 3.6, { ry: a });
  }

  // front library wing
  const wz = 2.5, wy = 0.4;
  box(P, stone, 7.4, 0.8, 3.6, 0, wy + 0.4, wz);
  box(P, plaster, 7.2, 2.8, 3.4, 0, wy + 0.8 + 1.4, wz);
  box(P, wood, 7.5, 0.25, 3.7, 0, 4.0, wz);
  add(P, roof, prism(8, 2.0, 3.8), { x: 0, y: 4.12, z: wz });
  // arched windows with bookshelves visible inside
  const wallZ = wz + 1.7;
  const winY = 2.35, ww = 0.95, wh = 1.5;
  for (const wx of [-3.0, -1.75, 1.75, 3.0]) {
    archWindow(P, pane, wood, wx, winY, wallZ, ww, wh);
    for (let s = 0; s < 3; s++) {                         // three shelf rows of books
      const sy = winY - wh / 2 + 0.12 + s * 0.52;
      box(P, wood, ww, 0.07, 0.16, wx, sy, wallZ + 0.13);
      for (let b = 0; b < 5; b++) {
        const bw = 0.12 + 0.03 * rnd(b + s * 9 + wx, 4);
        const bh = 0.26 + 0.18 * rnd(b + s * 7 + wx, 2);
        box(P, (b + s) % 2 ? bookA : bookB, bw, bh, 0.12, wx - ww / 2 + 0.12 + b * 0.17, sy + 0.035 + bh / 2, wallZ + 0.14);
      }
    }
  }
  // front arched double door
  box(P, wood, 1.7, 2.0, 0.14, 0, 1.4, wallZ + 0.04);
  add(P, wood, new THREE.CylinderGeometry(0.85, 0.85, 0.14, 8, 1, false, Math.PI / 2, Math.PI), { x: 0, y: 2.4, z: wallZ + 0.04, rx: Math.PI / 2 });
  box(P, stone, 0.08, 2.4, 0.1, 0, 1.6, wallZ + 0.12);
  for (const s of [-1, 1]) add(P, brass, ball(0.07), { x: s * 0.2, y: 1.4, z: wallZ + 0.16 });
  // lantern posts
  for (const s of [-1, 1]) {
    box(P, wood, 0.14, 1.6, 0.14, s * 1.4, 1.2, 4.6);
    add(P, pane, ball(0.2), { x: s * 1.4, y: 2.1, z: 4.6 });
  }
  // books piled by the steps
  box(P, bookA, 0.6, 0.12, 0.45, -2.6, 0.46, 4.4, { ry: 0.3 });
  box(P, bookB, 0.55, 0.12, 0.4, -2.6, 0.58, 4.4, { ry: -0.2 });
  group.add(mergeByMaterial(P));

  // brass gears on the gable, turning in opposite directions
  const g1 = new THREE.Mesh(gearGeometry(0.85, 10), brass); g1.position.set(-1.0, 5.0, wz + 1.95);
  const g2 = new THREE.Mesh(gearGeometry(0.58, 8), brass); g2.position.set(0.55, 4.7, wz + 1.95);
  g1.castShadow = g2.castShadow = true;
  group.add(g1, g2);

  // floating rune crystals orbiting the dome (one merged mesh, one draw call)
  const cparts = [];
  const crystal = glow("#7fd8ff", 1.5);
  for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2;
    const y = (i % 2) * 0.9 - 0.3;
    cparts.push([placed(new THREE.OctahedronGeometry(0.4, 0), { x: Math.cos(a) * 4.5, y, z: Math.sin(a) * 4.5, sy: 1.7, ry: a }), crystal]);
  }
  const crystals = mergeByMaterial(cparts);
  crystals.position.set(0, 6.3, rz);
  group.add(crystals);

  function update(dt, t) {
    g1.rotation.z += dt * 0.5;
    g2.rotation.z -= dt * 0.5 * (0.85 / 0.58);
    crystals.rotation.y = t * 0.35;
    crystals.position.y = 6.3 + Math.sin(t * 1.2) * 0.25;
    crystal.emissiveIntensity = 1.3 + 0.4 * Math.sin(t * 2.5);
  }
  return { group, update };
}

// =====================================================================================
// preview: Testers' Guild and Tech Academy side by side; cycles the lamp status every 2 s.
// The lead adds createMarketingHall() (from ./marketing-hall.js) here, at x = +12, and
// re-centres the row (testers -12 / academy 0 / marketing +12).
// =====================================================================================
export function preview(scene) {
  const testers = createTestersGuild(); testers.group.position.x = -7.5; scene.add(testers.group);
  const academy = createTechAcademy(); academy.group.position.x = 7.5; scene.add(academy.group);
  // <- createMarketingHall() goes here
  const order = ["none", "pass", "fail"];
  let last = -1;
  return (dt, t) => {
    const i = Math.floor(t / 2) % 3;
    if (i !== last) { last = i; testers.setStatus(order[i]); }
    testers.update(dt, t); academy.update(dt, t);
  };
}
