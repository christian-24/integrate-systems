// Chibi fantasy adventurers: createCharacter({ role, small }) -> { group, setState, update }.
// 11 meshes per character: cloak, trim, head, hat, eyes, 2 sleeves, 2 boots, staff, gem/lantern.
import { THREE, mat, glow, PALETTE, placed, mergeByMaterial, shadowed } from "./kit.js";

const ROLE_COLOR = { backend: "#c8463a", testers: "#2f9fa8", marketing: "#9a6ad8", finance: "#d4a017" };
const ROLE_DARK = { backend: "#8e2f27", testers: "#1f6f77", marketing: "#6b43a3", finance: "#8f6a0c" };
const ROLE_GEM = { backend: "#ff8a5c", testers: "#5ff0e0", marketing: "#d9a0ff", finance: "#fff3a0" };

const cyl = (rt, rb, h, s = 8) => new THREE.CylinderGeometry(rt, rb, h, s);
const sph = (r, w = 10, h = 8) => new THREE.SphereGeometry(r, w, h);
const cone = (r, h, s = 8) => new THREE.ConeGeometry(r, h, s);

// shared geometries (built once)
let G = null;
function geos() {
  if (G) return G;
  G = {
    head: sph(0.34),
    sleeve: placed(cyl(0.075, 0.095, 0.4), { y: -0.17 }),
    boot: placed(cyl(0.1, 0.12, 0.45), { y: -0.22 }),
    staff: cyl(0.025, 0.035, 1.5, 6),
    gem: new THREE.OctahedronGeometry(0.13, 0),
    lantern: sph(0.12, 8, 6),
  };
  return G;
}

export function createCharacter({ role = "backend", small = false } = {}) {
  const g = geos();
  const cloakCol = ROLE_COLOR[role] || ROLE_COLOR.backend;
  const darkCol = ROLE_DARK[role] || ROLE_DARK.backend;
  const gemCol = small ? "#ffd070" : (ROLE_GEM[role] || "#ffd070");

  const group = new THREE.Group();
  const rig = new THREE.Group(); // everything that sits down together
  group.add(rig);

  // ---- body (cloak + trim merged) ----
  const body = new THREE.Group();
  body.position.y = 0.45;
  const bodyMesh = mergeByMaterial([
    [placed(cyl(0.2, 0.37, 0.66), { y: 0.3 }), mat(cloakCol)],
    [placed(cyl(0.24, 0.24, 0.07), { y: 0.3 }), mat(PALETTE.woodDark)],
    [placed(cyl(0.26, 0.26, 0.06), { y: 0.57 }), mat(PALETTE.plaster)],
    [placed(cyl(0.38, 0.38, 0.05), { y: 0.0 }), mat(PALETTE.woodDark)],
    [placed(cyl(0.06, 0.06, 0.08, 6), { y: 0.3, z: 0.24 }), mat(PALETTE.gold)],
  ]);
  body.add(bodyMesh);
  rig.add(body);

  // ---- legs ----
  const mkLeg = x => {
    const p = new THREE.Group();
    p.position.set(x, 0.45, 0);
    const m = new THREE.Mesh(g.boot, mat("#7a4b2a"));
    p.add(m);
    rig.add(p);
    return p;
  };
  const legL = mkLeg(-0.13), legR = mkLeg(0.13);

  // ---- head (skin, hat, eyes) ----
  const head = new THREE.Group();
  head.position.y = 1.05;
  head.add(mergeByMaterial([
    [placed(g.head, { y: 0.3, sy: 0.95 }), mat(PALETTE.skin)],
    [placed(sph(0.07, 6, 5), { y: 0.26, z: 0.29, sz: 0.8 }), mat(PALETTE.skin)],
    [placed(cone(0.36, 0.55), { y: 0.82, rx: -0.12 }), mat(darkCol)],
    [placed(cyl(0.42, 0.42, 0.05), { y: 0.56 }), mat(darkCol)],
    [placed(cone(0.12, 0.3, 6), { y: 1.17, z: -0.07, rx: -0.9 }), mat(darkCol)],
    [placed(sph(0.045, 6, 5), { x: -0.11, y: 0.33, z: 0.26 }), mat("#2a1d1a")],
    [placed(sph(0.045, 6, 5), { x: 0.11, y: 0.33, z: 0.26 }), mat("#2a1d1a")],
    [placed(sph(0.05, 6, 5), { x: -0.2, y: 0.24, z: 0.2, sz: 0.4 }), mat("#f08a7c")],
    [placed(sph(0.05, 6, 5), { x: 0.2, y: 0.24, z: 0.2, sz: 0.4 }), mat("#f08a7c")],
  ]));
  rig.add(head);

  // ---- arms ----
  const mkArm = x => {
    const p = new THREE.Group();
    p.position.set(x, 1.0, 0);
    p.add(new THREE.Mesh(g.sleeve, mat(darkCol)));
    rig.add(p);
    return p;
  };
  const armL = mkArm(-0.3), armR = mkArm(0.3);

  // ---- staff with gem (session) or lantern (subagent), held in right hand ----
  const staff = new THREE.Group();
  staff.position.set(0.02, -0.38, 0.06);
  const pole = new THREE.Mesh(g.staff, mat(PALETTE.wood));
  pole.position.y = 0.3;
  staff.add(pole);
  const gem = new THREE.Mesh(small ? g.lantern : g.gem, glow(gemCol, small ? 1.6 : 1.4));
  gem.position.y = small ? 0.9 : 1.1;
  if (small) { gem.position.set(0.0, 0.88, 0.0); }
  staff.add(gem);
  armR.add(staff);

  // lanterns glow brightly when small: no per-instance lights (performance)
  if (small) group.scale.setScalar(0.65);
  shadowed(group);

  // ---- animation ----
  let state = "waiting";
  const P = { sit: 0, lx: 0, rx: 0, alx: 0, arx: 0, alz: 0, arz: 0, hx: 0, hy: 0, hz: 0, bob: 0, lean: 0 };
  let sx = 1;
  const ease = (k, key, target) => { P[key] += (target - P[key]) * k; };

  function setState(s) { state = s; }

  function update(dt, t, moving) {
    const k = 1 - Math.exp(-dt * 10);
    const sitting = state === "resting" || state === "done";
    const walk = !!moving;
    const ph = t * 9;
    const tg = { sit: 0, lx: 0, rx: 0, alx: 0, arx: -0.1, alz: 0.12, arz: -0.12, hx: 0, hy: 0, hz: 0, bob: 0, lean: 0 };
    let gemPulse = 1 + Math.sin(t * 2) * 0.08;
    let breathe = 1;

    if (walk) {
      const s = Math.sin(ph);
      tg.lx = s * 0.75; tg.rx = -s * 0.75;
      tg.alx = -s * 0.7; tg.arx = s * 0.35;
      tg.bob = Math.abs(Math.cos(ph)) * 0.07;
      tg.hz = s * 0.06; tg.hy = Math.sin(ph * 0.5) * 0.1;
      tg.lean = 0.08;
    } else if (sitting) {
      tg.sit = 1;
      tg.lx = -1.45; tg.rx = -1.45;
      tg.alx = -0.5; tg.arx = -0.5;
      tg.alz = 0.2; tg.arz = -0.2;
      const nod = Math.sin(t * 1.4);
      tg.hx = state === "resting" ? 0.45 + nod * 0.18 : 0.12 + nod * 0.12;
      tg.hy = state === "done" ? Math.sin(t * 0.6) * 0.3 : 0;
      tg.lean = 0.1;
      breathe = 1 + Math.sin(t * 1.4) * 0.025;
      gemPulse = 0.7 + Math.sin(t * 1.4) * 0.05;
    } else if (state === "working") {
      const sw = Math.sin(t * 7);
      tg.arx = -2.3 + sw * 0.55; // raised staff, casting / hammering
      tg.arz = -0.1;
      tg.alx = -0.6 + Math.sin(t * 7 + 1.5) * 0.3;
      tg.hx = 0.12 + sw * 0.07;
      tg.hy = Math.sin(t * 1.3) * 0.15;
      tg.bob = Math.max(0, -sw) * 0.04;
      tg.lean = 0.12 + sw * 0.05;
      gemPulse = 1.25 + Math.sin(t * 14) * 0.35;
    } else {
      // waiting: breathing, looking around
      breathe = 1 + Math.sin(t * 2) * 0.025;
      tg.hy = Math.sin(t * 0.9) * 0.7 * (Math.sin(t * 0.37) > -0.2 ? 1 : 0.3);
      tg.hx = Math.sin(t * 0.6) * 0.08;
      tg.arx = -0.1 + Math.sin(t * 2) * 0.03;
      tg.alx = Math.sin(t * 2 + 1) * 0.04;
      tg.lean = Math.sin(t * 0.5) * 0.02;
    }

    for (const key in tg) ease(k, key, tg[key]);
    sx += (breathe - sx) * k;

    rig.position.y = -0.36 * P.sit + P.bob;
    rig.position.z = 0.0 + 0.14 * P.sit;
    rig.rotation.x = P.lean;
    legL.rotation.x = P.lx; legR.rotation.x = P.rx;
    legL.rotation.z = -0.05 * P.sit; legR.rotation.z = 0.05 * P.sit;
    armL.rotation.set(P.alx, 0, P.alz);
    armR.rotation.set(P.arx, 0, P.arz);
    head.rotation.set(P.hx, P.hy, P.hz);
    body.scale.set(1, sx, 1);
    head.position.y = 1.05 + (sx - 1) * 0.6;
    gem.scale.setScalar(gemPulse);
    gem.rotation.y = t * 1.5;
  }

  update(0.016, 0, false);
  return { group, setState, update };
}

export function preview(scene) {
  const roles = ["backend", "testers", "marketing"];
  const states = ["working", "waiting", "resting", "done"];
  const list = [];
  let i = 0;
  for (const small of [false, true]) {
    for (const role of roles) {
      const c = createCharacter({ role, small });
      c.group.position.x = (i - 2.5) * 2.2;
      scene.add(c.group);
      list.push({ c, i, x: c.group.position.x });
      i++;
    }
  }
  return function update(dt, t) {
    for (const { c, i, x } of list) {
      const tt = t + i * 1.1;
      const cyc = Math.floor(tt / 3);
      // every other cycle starts with a walk (first 1.8s), then settles into a state
      const within = tt - cyc * 3;
      const walkNow = cyc % 2 === 0 && within < 1.8;
      c.setState(states[cyc % states.length]);
      c.update(dt, t, walkNow);
      const dz = walkNow ? Math.sin(within / 1.8 * Math.PI) * 1.2 : 0;
      c.group.position.z = dz;
      c.group.position.x = x;
    }
  };
}
