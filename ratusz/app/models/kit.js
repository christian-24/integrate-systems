// Shared helpers for every Agent Quest 3D model. Import from "./kit.js" in a model file.
// Rule of thumb: one material per colour (cached here), static parts merged into one mesh per
// material (mergeByMaterial), and only parts that move stay separate.

import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

export { THREE };

// ---------- materials, cached so the whole village shares them ----------
const cache = new Map();
/** A flat-shaded standard material; the same arguments always return the same material. */
export function mat(color, opts = {}) {
  const key = color + JSON.stringify(opts);
  if (!cache.has(key)) cache.set(key, new THREE.MeshStandardMaterial({ color, roughness: 0.85, flatShading: true, ...opts }));
  return cache.get(key);
}
/** A glowing material (windows, lanterns, gems); `intensity` is the emissive strength. */
export function glow(color, intensity = 1.2) {
  return mat(color, { emissive: color, emissiveIntensity: intensity, flatShading: false, roughness: 0.4 });
}

// ---------- the shared palette (use these; add a few accents of your own at most) ----------
export const PALETTE = {
  wood: "#8a5a34", woodDark: "#5e3b22", woodLight: "#b07a4a",
  stone: "#9b9384", stoneDark: "#6c665c", stoneLight: "#c4bdae",
  plaster: "#efe2c6", plasterShade: "#d9c9a8",
  roofRed: "#c8463a", roofBlue: "#3a6fb0", roofTeal: "#2f7f86", roofViolet: "#7a4fa0", roofThatch: "#d9b45a",
  gold: "#e2b347", leaf: "#5f9e3a", pine: "#2e7d5b", grass: "#7fb84e", dirt: "#b08a5a",
  skin: "#f1c9a0", window: "#ffb347", cloth: "#e8dcc0",
};

// ---------- geometry ----------
/** Place a geometry: returns a clone moved, rotated (radians, XYZ) and scaled. */
export function placed(geometry, { x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1 } = {}) {
  const g = geometry.clone();
  const m = new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, ry, rz)), new THREE.Vector3(sx, sy, sz));
  g.applyMatrix4(m);
  return g;
}

/**
 * Merge static parts into as few meshes as possible: one mesh per material.
 * `parts` is a list of [geometry, material] pairs (geometry already placed).
 * Returns a THREE.Group of meshes that cast and receive shadows.
 */
export function mergeByMaterial(parts) {
  const byMat = new Map();
  for (const [geo, material] of parts) {
    const g = geo.index ? geo.toNonIndexed() : geo;
    // every merged geometry needs the same attributes
    for (const name of Object.keys(g.attributes)) if (!["position", "normal", "uv"].includes(name)) g.deleteAttribute(name);
    if (!g.attributes.uv) g.setAttribute("uv", new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    if (!byMat.has(material)) byMat.set(material, []);
    byMat.get(material).push(g);
  }
  const group = new THREE.Group();
  for (const [material, geos] of byMat) {
    const mesh = new THREE.Mesh(mergeGeometries(geos, false), material);
    mesh.castShadow = true; mesh.receiveShadow = true;
    group.add(mesh);
  }
  return group;
}

/** Cast and receive shadows on every mesh under `object`. */
export function shadowed(object) {
  object.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return object;
}

// ---------- small canvas textures (cached), for surfaces that need detail ----------
const texCache = new Map();
/**
 * A tiling texture drawn once on a canvas: draw(ctx, size) paints a size x size tile.
 * Use for roof tiles, planks, stone courses, grass. Keep size 64 or 128.
 */
export function canvasTexture(key, size, draw, repeat = [1, 1]) {
  if (!texCache.has(key)) {
    const c = document.createElement("canvas"); c.width = c.height = size;
    draw(c.getContext("2d"), size);
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace;
    t.magFilter = THREE.NearestFilter; t.anisotropy = 4;
    texCache.set(key, t);
  }
  const t = texCache.get(key).clone(); t.needsUpdate = true; t.repeat.set(...repeat);
  return t;
}

/** A seeded random number in [0, 1): deterministic models, no Math.random. */
export const rnd = (i, s = 1) => { const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453; return x - Math.floor(x); };
