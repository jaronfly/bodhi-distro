// The director: one continuous camera and every scene parameter as a pure
// function of the canonical position c (0..12, see timeline.js CANON).
// Camera knots are authored as eye + look-at and interpolated in a
// (look, yaw, pitch, log distance) space so dolly moves read as scale changes.
import { sstep, smooth } from './math.js';

const DEG = Math.PI / 180;

// Monotone cubic Hermite through (c, value) knots; flat outside the range.
function curve(knots) {
  const n = knots.length, xs = knots.map((k) => k[0]), ys = knots.map((k) => k[1]);
  const m = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const d0 = i > 0 ? (ys[i] - ys[i - 1]) / (xs[i] - xs[i - 1]) : 0;
    const d1 = i < n - 1 ? (ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) : 0;
    m[i] = i === 0 || i === n - 1 || d0 * d1 <= 0 ? 0 : (d0 + d1) / 2;
  }
  return (c) => {
    if (c <= xs[0]) return ys[0];
    if (c >= xs[n - 1]) return ys[n - 1];
    let i = 1; while (xs[i] < c) i++;
    const h = xs[i] - xs[i - 1], t = (c - xs[i - 1]) / h, t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * ys[i - 1] + (t3 - 2 * t2 + t) * h * m[i - 1] + (-2 * t3 + 3 * t2) * ys[i] + (t3 - t2) * h * m[i];
  };
}
// Eased piecewise track: smoothstep between knots (holds at each knot).
function ease(knots) {
  const n = knots.length;
  return (c) => {
    if (c <= knots[0][0]) return knots[0][1];
    for (let i = 1; i < n; i++) if (c <= knots[i][0]) {
      const [c0, v0] = knots[i - 1], [c1, v1] = knots[i];
      return v0 + (v1 - v0) * smooth((c - c0) / (c1 - c0));
    }
    return knots[n - 1][1];
  };
}

// ---------------------------------------------------------------- camera
// [c, eye, look, fov, fitW (min visible width at the look point), shiftX]
const CAM = [
  [0.00, [0.00, -0.31, 1.95], [0, -0.365, 0.02], 34, 0.9, 0],
  [0.40, [0.02, -0.33, 1.50], [0, -0.36, 0.02], 34, 0.8, 0],
  [0.75, [0.04, -0.20, 1.55], [0, -0.24, 0.02], 36, 0.8, 0],
  [1.00, [0.10, -0.04, 1.85], [0, -0.12, 0.02], 38, 1.0, 0],
  [1.30, [0.25, -0.18, 3.30], [0, -0.40, 0.00], 40, 2.0, 0],
  [1.65, [0.40, -0.25, 4.60], [0, -0.60, 0.00], 40, 2.7, 0],
  [2.00, [0.30, 0.10, 4.10], [0, -0.35, 0.00], 40, 2.7, 0],
  [2.12, [0.30, 0.10, 4.10], [0, -0.35, 0.00], 40, 2.7, 0], // blended to the leaf by focusLeaf
  [2.95, [0.00, 0.25, 2.60], [0, 0.15, 0.00], 40, 1.4, 0],
  [3.05, [0.00, 0.25, 2.60], [0, 0.15, 0.00], 40, 1.4, 0],
  [3.40, [1.40, 1.50, 8.50], [0, 1.30, 0.00], 42, 5.0, 0],
  [3.95, [5.00, 3.00, 17.0], [0, 2.60, 0.00], 42, 12, 0.08],
  [4.25, [3.60, 2.10, 14.5], [0, 3.10, 0.00], 42, 11, 0.14],
  [4.60, [-0.5, 2.40, 14.8], [0, 3.20, 0.00], 42, 11, 0.14],
  [5.00, [-4.2, 1.90, 13.6], [0, 3.30, 0.00], 42, 11, 0.12],
  [5.20, [1.60, 1.40, 9.00], [-3, 5.0, -20], 50, 8, 0],
  [5.50, [2.40, 1.30, 8.60], [-5, 6.5, -30], 52, 8, 0],
  [5.80, [2.40, 1.30, 8.60], [5, 17, -32], 55, 8, 0],
  [6.00, [2.00, 2.20, 8.00], [4, 28, -26], 56, 8, 0],
  [6.35, [0.00, 58.0, -6.0], [0, 112, -82], 56, 40, 0],
  [6.70, [8.00, 80.0, -30], [0, 112, -82], 56, 40, 0],
  [7.00, [14.0, 88.0, -40], [0, 112, -82], 56, 40, 0],
  [7.22, [0.00, 3.00, 48.0], [0, 11, 0], 44, 10, 0],
  [8.00, [-4.0, 1.80, 44.0], [0, 9.0, 0], 44, 10, 0],
  [9.00, [-8.5, 1.70, 41.0], [0, 8.2, 0], 44, 10, 0],
  [10.0, [-11., 1.70, 38.0], [0, 7.5, 0], 44, 10, 0],
  [10.35, [3.00, 1.20, 10.0], [1.5, 0.4, 0], 44, 5, 0],
  [10.70, [2.30, -0.06, 2.60], [2.2, -0.25, 0.02], 38, 1.0, 0],
  [11.0, [2.20, -0.28, 1.90], [2.2, -0.345, 0.02], 34, 0.9, 0],
  [12.0, [2.24, -0.27, 1.80], [2.2, -0.345, 0.02], 34, 0.9, 0],
];

function camTracks() {
  const lx = [], ly = [], lz = [], yaw = [], pit = [], ld = [], fov = [], fw = [], sx = [];
  let prevYaw = 0;
  for (const [c, e, l, f, w, s] of CAM) {
    const o = [e[0] - l[0], e[1] - l[1], e[2] - l[2]], d = Math.hypot(...o);
    let y = Math.atan2(o[0], o[2]);
    while (y - prevYaw > Math.PI) y -= 2 * Math.PI;
    while (y - prevYaw < -Math.PI) y += 2 * Math.PI;
    prevYaw = y;
    lx.push([c, l[0]]); ly.push([c, l[1]]); lz.push([c, l[2]]);
    yaw.push([c, y]); pit.push([c, Math.asin(o[1] / d)]); ld.push([c, Math.log(d)]);
    fov.push([c, f]); fw.push([c, Math.log(w)]); sx.push([c, s]);
  }
  return [lx, ly, lz, yaw, pit, ld, fov, fw, sx].map(curve);
}

// ---------------------------------------------------------------- scalar tracks
const T = {
  sunEl: ease([[0, -9.5], [1, -8], [1.9, -3], [2.2, 4], [3.9, 4], [4.05, 7], [5, 17], [5.38, 1], [5.55, -7], [5.8, -20], [6.2, -26], [7.1, -26], [8, -18], [9, -11], [10, -5], [11, 5], [12, 7]]),
  sunAz: ease([[0, -25], [2, -20], [4, -30], [5, -18], [5.5, -12], [7, -12], [10, 30], [11, 40], [12, 42]]),
  moonEl: ease([[0, -20], [5.35, -8], [5.85, 20], [6.2, 30], [7.2, 34], [8.5, 22], [9.5, 10], [10.6, -10]]),
  moonAz: ease([[0, 55], [5.3, 60], [6, 42], [8.5, 24], [10, 10]]),
  exposure: ease([[0, 1.6], [1, 1.5], [1.9, 1.3], [3.9, 1.2], [4.1, 0.62], [5.1, 0.6], [5.45, 1.2], [5.8, 2.6], [7.1, 2.7], [8, 2.3], [9, 1.9], [10, 1.5], [11, 1.25], [12, 1.2]]),
  aurora: ease([[0, 0], [5.6, 0], [5.85, 1], [6.3, 0.7], [7.05, 0.4], [7.6, 0.18], [8.2, 0]]),
  clouds: ease([[0, 0.25], [2, 0.3], [4, 0.36], [5, 0.42], [5.6, 0.38], [6, 0.26], [7.2, 0.3], [8, 0.4], [9, 0.44], [10, 0.46], [11, 0.3], [12, 0.3]]),
  env: ease([[0, 1], [2.85, 1], [2.95, 0], [3.9, 0], [4.14, 1]]),
  cosmos: ease([[0, 0], [5.95, 0], [6.3, 1], [6.98, 1], [7.2, 0]]),
  spiral: ease([[0, 0], [6.12, 0], [6.62, 1]]),
  season: ease([[0, 1.2], [3.9, 1.2], [3.901, 0.0], [4.03, 0.05], [4.97, 3.6], [6, 3.9], [7, 4.0], [8, 4.25], [9, 4.5], [10, 4.8], [11, 5.1], [12, 5.2]]),
  growth: ease([[0, 0], [0.30, 0], [1.0, 0.075], [1.55, 0.125], [2.0, 0.15], [2.9, 0.15], [2.91, 1]]),
  rootGrow: ease([[0, 0], [0.25, 0], [0.55, 0.06], [1.0, 0.1], [1.95, 1]]),
  rootLight: ease([[0, 0], [1.05, 0], [1.25, 1], [1.4, 1], [1.6, 2], [1.72, 2], [1.92, 3], [2.2, 3]]),
  rootScale: ease([[0, 1], [10.0, 1], [10.01, 2.3]]),
  cut: ease([[0, 0], [2.4, 0], [2.401, 400], [10.12, 400], [10.13, 60], [10.66, 0]]),
  hideUnder: ease([[0, 0], [10.0, 0], [10.01, 1]]),
  wind: ease([[0, 0.25], [2, 0.3], [4.1, 0.45], [4.6, 0.6], [4.8, 1.0], [5, 0.7], [5.6, 0.35], [8, 0.45], [12, 0.35]]),
  seedHero: ease([[0, 1], [1.2, 1], [1.5, 0]]),
  seedSplit: ease([[0, 0], [0.30, 0], [0.48, 1]]),
  seedNew: ease([[0, 0], [10.45, 0], [10.75, 1]]),
  focusLeaf: ease([[0, 0], [2.0, 0], [2.13, 1], [2.9, 1], [2.91, 0]]),
  micro: ease([[0, 0], [2.085, 0], [2.14, 1], [3.0, 1], [3.035, 0]]),
  zoom: ease([[0, 0], [2.1, 0], [2.26, 1.2], [2.42, 2.05], [2.8, 2.2], [2.9, 2.62], [2.96, 3.0]]),
  pad: ease([[0, 0], [2.3, 0], [2.42, 1]]),
  pix: ease([[0, 0], [2.86, 0], [2.93, 1]]),
  markT: ease([[0, 0], [2.91, 0], [2.985, 1]]),
  netMorph: ease([[0, 0], [3.04, 0], [3.32, 1]]),
  netReveal: ease([[0, 0], [3.1, 0], [3.75, 1]]),
  net: ease([[0, 0], [2.99, 0], [3.0, 1], [4.08, 1], [4.3, 0.1], [4.5, 0]]),
  treeVis: ease([[0, 1], [2.9, 1], [2.91, 0], [3.86, 0], [4.12, 1]]),
  calm: ease([[0, 0], [7.0, 0], [7.12, 1], [10.02, 1], [10.2, 0], [11.0, 0], [11.12, 0.8]]),
  grain: ease([[0, 1], [1, 0.85], [2, 0.6], [12, 0.6]]),
};

// Still-frame keyframes (progress within each scene) for reduced motion.
export const STILL_P = { soil: 0.12, roots: 0.95, cell: 0.6, 'to-be': 0.85, tree: 0.66, sky: 0.8, ancestors: 0.62, questions: 0.5, receipts: 0.5, workbench: 0.5, plant: 0.98, access: 0.5 };

export class Director {
  constructor() {
    this.cam = camTracks();
    this.s = { c: 0, look: [0, 0, 0], yaw: 0, pitch: 0, dist: 1, fov: 40, fitW: 1, shiftX: 0 };
    for (const k in T) this.s[k] = 0;
  }
  eval(c) {
    const s = this.s, [lx, ly, lz, yaw, pit, ld, fov, fw, sx] = this.cam;
    s.c = c;
    s.look[0] = lx(c); s.look[1] = ly(c); s.look[2] = lz(c);
    s.yaw = yaw(c); s.pitch = pit(c); s.dist = Math.exp(ld(c));
    s.fov = fov(c); s.fitW = Math.exp(fw(c)); s.shiftX = sx(c);
    for (const k in T) s[k] = T[k](c);
    s.sunEl *= DEG; s.sunAz *= DEG; s.moonEl *= DEG; s.moonAz *= DEG;
    s.night = sstep(-3 * DEG, -13 * DEG, s.sunEl);
    return s;
  }
}
