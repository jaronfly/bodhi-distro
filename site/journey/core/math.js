// Small, allocation-free math for the CPU side: PRNG, value noise, easing, and
// quaternion / column-major mat4 helpers that write into caller-owned arrays.

export const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
export const sat = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (t) => t * t * (3 - 2 * t);
export const sstep = (a, b, x) => smooth(sat((x - a) / (b - a)));

export function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hash(n) {
  n = Math.imul(n ^ (n >>> 16), 0x7feb352d);
  n = Math.imul(n ^ (n >>> 15), 0x846ca68b);
  return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
}
export function noise1(x) {
  const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
  return lerp(hash(i), hash(i + 1), u);
}
export function noise2(x, y) {
  const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
  const ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
  const h = (a, b) => hash(Math.imul(a, 1597334677) ^ Math.imul(b, 381201580));
  return lerp(lerp(h(ix, iy), h(ix + 1, iy), ux), lerp(h(ix, iy + 1), h(ix + 1, iy + 1), ux), uy);
}
export function fbm2(x, y, oct = 4) {
  let s = 0, a = 0.5;
  for (let i = 0; i < oct; i++) { s += a * noise2(x, y); const nx = 1.6 * x - 1.2 * y; y = 1.2 * x + 1.6 * y; x = nx; a *= 0.5; }
  return s;
}

// ---- vectors as plain arrays (only used at build time)
export const v3 = {
  add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
  sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]],
  mul: (a, s) => [a[0] * s, a[1] * s, a[2] * s],
  dot: (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
  cross: (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]],
  len: (a) => Math.hypot(a[0], a[1], a[2]),
  norm: (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; },
};

// ---- quaternions [x, y, z, w]
export function qFromUnit(a, b) { // rotation taking unit a to unit b
  const d = v3.dot(a, b);
  if (d < -0.99999) { const ax = Math.abs(a[0]) < 0.9 ? v3.norm(v3.cross([1, 0, 0], a)) : v3.norm(v3.cross([0, 0, 1], a)); return [ax[0], ax[1], ax[2], 0]; }
  const c = v3.cross(a, b); const q = [c[0], c[1], c[2], 1 + d]; const l = Math.hypot(...q); return q.map((x) => x / l);
}
export function qMul(a, b) {
  return [
    a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
    a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
    a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
    a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2],
  ];
}
export const qInv = (q) => [-q[0], -q[1], -q[2], q[3]];
export function qRot(q, v) {
  const [x, y, z, w] = q; const t = v3.mul(v3.cross([x, y, z], v), 2);
  return v3.add(v3.add(v, v3.mul(t, w)), v3.cross([x, y, z], t));
}
export function qAxis(ax, ang) { const s = Math.sin(ang / 2); return [ax[0] * s, ax[1] * s, ax[2] * s, Math.cos(ang / 2)]; }
export function qFromBasis(X, Y, Z) { // columns X, Y, Z (orthonormal)
  const m00 = X[0], m11 = Y[1], m22 = Z[2], tr = m00 + m11 + m22;
  let q;
  if (tr > 0) { const s = 0.5 / Math.sqrt(tr + 1); q = [(Y[2] - Z[1]) * s, (Z[0] - X[2]) * s, (X[1] - Y[0]) * s, 0.25 / s]; }
  else if (m00 > m11 && m00 > m22) { const s = 2 * Math.sqrt(1 + m00 - m11 - m22); q = [0.25 * s, (Y[0] + X[1]) / s, (Z[0] + X[2]) / s, (Y[2] - Z[1]) / s]; }
  else if (m11 > m22) { const s = 2 * Math.sqrt(1 + m11 - m00 - m22); q = [(Y[0] + X[1]) / s, 0.25 * s, (Z[1] + Y[2]) / s, (Z[0] - X[2]) / s]; }
  else { const s = 2 * Math.sqrt(1 + m22 - m00 - m11); q = [(Z[0] + X[2]) / s, (Z[1] + Y[2]) / s, 0.25 * s, (X[1] - Y[0]) / s]; }
  const l = Math.hypot(...q); return q.map((x) => x / l);
}

// ---- 3x3 rotation (row-major in a Float32Array(9) slot) and rigid transforms
// A rigid transform is stored as R (9, row-major) + t (3) = 12 floats at an offset.
export function rotFromQ(q, out, o) {
  const [x, y, z, w] = q;
  out[o] = 1 - 2 * (y * y + z * z); out[o + 1] = 2 * (x * y - z * w); out[o + 2] = 2 * (x * z + y * w);
  out[o + 3] = 2 * (x * y + z * w); out[o + 4] = 1 - 2 * (x * x + z * z); out[o + 5] = 2 * (y * z - x * w);
  out[o + 6] = 2 * (x * z - y * w); out[o + 7] = 2 * (y * z + x * w); out[o + 8] = 1 - 2 * (x * x + y * y);
}
