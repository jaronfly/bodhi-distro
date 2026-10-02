// The tree. A sacred-fig-like broad crown generated once (branch azimuths step by
// the golden angle), grown by a growth parameter g (seed -> sprout -> sapling ->
// tree), swayed by a spring-damped branch hierarchy, and dressed in instanced
// heart-shaped leaves that live through the seasons and fall with real physics.
import * as THREE from '../vendor/three.module.min.js';
import { COMMON, SKYLUT } from '../shaders/common.js';
import { rng, v3, qFromUnit, qMul, qInv, qRot, qAxis, qFromBasis, rotFromQ, sstep, sat, noise1 } from '../core/math.js';

export const SEED = [0, -0.35, 0.02];
const GOLDEN = Math.PI * (3 - Math.sqrt(5));
const UP = [0, 1, 0];
export const WIND_DIR = v3.norm([1, 0, -0.35]);

// ---------------------------------------------------------------- generation
function generate(tier) {
  const R = rng(20260930);
  const B = { parent: [], at: [], wq: [], pos: [], dir: [], len: [], r0: [], r1: [], depth: [], birth: [], dur: [], trunk: [] };
  const L = []; // leaves: [bone, t, azimuth, size, rand, juvenile, cot]
  const leafPer = tier === 'high' ? 0.62 : 0.36;
  const add = (parent, at, P, D, len, r0, r1, depth, birth, dur) => {
    const i = B.parent.length;
    const pq = parent < 0 ? [0, 0, 0, 1] : B.wq[parent];
    const pd = parent < 0 ? UP : B.dir[parent];
    B.parent.push(parent); B.at.push(at); B.wq.push(qMul(qFromUnit(pd, D), pq));
    B.pos.push(P); B.dir.push(D); B.len.push(len); B.r0.push(r0); B.r1.push(r1);
    B.depth.push(depth); B.birth.push(birth); B.dur.push(dur);
    return i;
  };
  const perp = (D, a) => { // unit vector perpendicular to D at azimuth a
    const ref = Math.abs(D[1]) < 0.95 ? UP : [1, 0, 0];
    const x = v3.norm(v3.cross(ref, D)), y = v3.cross(D, x);
    return v3.add(v3.mul(x, Math.cos(a)), v3.mul(y, Math.sin(a)));
  };
  const leaves = (bone, n, juvenile) => {
    for (let k = 0; k < n; k++) if (R() < leafPer || juvenile) L.push([bone, 0.25 + 0.75 * (k + R() * 0.6) / n, R() * 6.283, 0.85 + R() * 0.3, R(), juvenile, 0]);
  };
  const branch = (parent, at, P, D, len, r, depth, birth, spread) => {
    const nseg = [5, 5, 4, 3][depth], sl = len / nseg;
    let prev = parent, a = at, az = R() * 6.283;
    for (let s = 0; s < nseg; s++) {
      const out = v3.norm([D[0], 0, D[2]]);
      const trop = [0.02, 0.06, 0.1, 0.12][depth], droop = [0, 0.05, 0.1, 0.16][depth] * (s / nseg);
      if (s > 0) D = v3.norm(v3.add(v3.add(D, v3.mul(UP, trop - droop)), v3.add(v3.mul(out, spread * 0.08), [(R() - 0.5) * 0.22, (R() - 0.5) * 0.12, (R() - 0.5) * 0.22])));
      const r0 = r * (1 - 0.55 * s / nseg), r1 = r * (1 - 0.55 * (s + 1) / nseg);
      const bd = depth === 0 ? 0.0 + s * 0.011 : birth + s * [0, 0.01, 0.014, 0.02][depth];
      const idx = add(prev, a, P, D, sl, r0, r1, depth, bd, depth === 0 ? 0.016 : 0.04 + depth * 0.02);
      if (depth === 0) B.trunk.push(idx);
      // children
      if (depth === 0 && s >= 2) {
        const n = 2;
        for (let c = 0; c < n; c++) {
          az += GOLDEN * 1.6 + (R() - 0.5) * 0.3;
          const ang = 0.95 + R() * 0.35 - (s - 2) * 0.12;
          const cd = v3.norm(v3.add(v3.mul(D, Math.cos(ang)), v3.mul(perp(D, az), Math.sin(ang))));
          const t = 0.55 + R() * 0.45;
          branch(idx, t, v3.add(P, v3.mul(D, sl * t)), cd, (3.4 + R() * 0.9) * (1 - (s - 2) * 0.12), r0 * 0.6, 1, s === 2 ? 0.2 + c * 0.01 : 0.074 + c * 0.006 + (s - 3) * 0.008, 1);
        }
      } else if (depth === 1 && s >= 1) {
        const n = R() < 0.55 ? 2 : 1;
        for (let c = 0; c < n; c++) {
          az += GOLDEN + (R() - 0.5) * 0.4;
          const ang = 0.6 + R() * 0.45, t = 0.3 + R() * 0.6;
          const cd = v3.norm(v3.add(v3.mul(D, Math.cos(ang)), v3.mul(perp(D, az), Math.sin(ang))));
          branch(idx, t, v3.add(P, v3.mul(D, sl * t)), cd, (1.3 + R() * 0.8) * (1 - s * 0.08), r1 * 0.6, 2, 0.13 + s * 0.05 + R() * 0.06, 0.7);
        }
        leaves(idx, 3, true);
      } else if (depth === 2 && s >= 1) {
        const n = 2;
        for (let c = 0; c < n; c++) {
          az += GOLDEN + (R() - 0.5) * 0.4;
          const ang = 0.5 + R() * 0.5, t = 0.25 + R() * 0.7;
          const cd = v3.norm(v3.add(v3.mul(D, Math.cos(ang)), v3.mul(perp(D, az), Math.sin(ang))));
          branch(idx, t, v3.add(P, v3.mul(D, sl * t)), cd, 0.55 + R() * 0.45, r1 * 0.62, 3, birth + 0.08 + s * 0.04 + R() * 0.05, 0.4);
        }
        leaves(idx, 2, true);
      } else if (depth === 3) {
        leaves(idx, 6, false);
      }
      P = v3.add(P, v3.mul(D, sl)); prev = idx; a = 1;
    }
    if (depth === 2) leaves(prev, 4, false);
  };
  branch(-1, 0, [0, 0, 0], v3.norm([0.04, 1, -0.02]), 2.45, 0.34, 0, 0, 0);
  // two cotyledons ride the trunk's top bone until the sapling outgrows them
  const top = B.trunk[4];
  L.push([top, 1, 0.0, 0.55, 0.5, 1, 1], [top, 1, Math.PI, 0.55, 0.9, 1, 1]);
  return { B, L };
}

// ---------------------------------------------------------------- shaders
const BONE_FETCH = /* glsl */`
uniform sampler2D uBones;
mat4 boneM(int i){ return mat4(texelFetch(uBones, ivec2(0, i), 0), texelFetch(uBones, ivec2(1, i), 0), texelFetch(uBones, ivec2(2, i), 0), texelFetch(uBones, ivec2(3, i), 0)); }
vec4 boneD(int i){ return texelFetch(uBones, ivec2(4, i), 0); }
`;
const TREE_U = /* glsl */`
uniform vec3 uSunCol, uAmb, uMoonCol, uMoonDir, uVoid;
uniform float uEnv, uVis, uCut, uHideUnder, uYouth, uSnow, uTime, uWind, uSeason, uStill;
`;

const BARK_VERT = /* glsl */`
${BONE_FETCH}
attribute float aBone;
varying vec3 vW; varying vec3 vN; varying vec2 vB; varying float vDepth;
void main(){
  int i = int(aBone);
  mat4 M = boneM(i); vec4 D = boneD(i);
  float r = mix(D.y, D.z, position.y);
  float L = D.x;
  vec3 lp = vec3(position.x * r, position.y * (L + r * 0.6) - r * 0.3, position.z * r);
  if (L <= 0.0) lp = vec3(0.0);
  vec4 w = M * vec4(lp, 1.0);
  vW = w.xyz; vN = normalize(mat3(M) * vec3(position.x, 0.0, position.z));
  vB = vec2(atan(position.z, position.x), position.y * L * 8.0 + float(i) * 1.7); vDepth = D.w;
  gl_Position = projectionMatrix * viewMatrix * w;
}`;
const BARK_FRAG = /* glsl */`
${COMMON}
${SKYLUT}
${TREE_U}
varying vec3 vW; varying vec3 vN; varying vec2 vB; varying float vDepth;
void main(){
  if (h21(ivec2(gl_FragCoord.xy)) > uVis) discard;
  if (uHideUnder > 0.5 && vW.y < -0.01 && vW.z > uCut - 0.02) discard;
  vec3 n = normalize(vN);
  float ridge = vnoise(vec2(vB.x * 5.0, vB.y * 0.6)) * 0.6 + vnoise(vec2(vB.x * 14.0, vB.y * 2.0)) * 0.4;
  vec3 bark = mix(vec3(0.016, 0.014, 0.012), mix(MOSS, LICHEN, 0.3) * 0.22, ridge);
  // young stems: pale underground, green above
  vec3 young = mix(BONE * 0.55, mix(SPROUT, CANOPY, 0.5) * 0.6, smoothstep(-0.02, 0.03, vW.y));
  vec3 a = mix(bark, young, uYouth);
  a = mix(a, BONE * 0.6, uSnow * smoothstep(0.35, 0.8, n.y));
  float ndl = max(dot(n, uSunDir), 0.0) * 0.85 + 0.15 * max(dot(n, uSunDir) + 0.4, 0.0);
  vec3 c = a * (uSunCol * ndl + uAmb * (0.55 + 0.45 * n.y) + uMoonCol * max(dot(n, uMoonDir), 0.0));
  c = aerial(c, vW, 0.0045);
  gl_FragColor = vec4(mix(uVoid, c, uEnv), 1.0);
}`;

// Leaf colour through the year (ys in [0,4): spring, summer, autumn, winter).
const LEAF_COLOR = /* glsl */`
vec3 leafColor(float ys, float r){
  float r2 = fract(r * 7.137), r3 = fract(r * 3.71);
  vec3 g = mix(CANOPY * 0.9, mix(CANOPY, SPROUT, 0.35), r3 * 0.6);
  g = mix(g, SPROUT * 0.95, (1.0 - smoothstep(0.35, 1.1, ys)) * 0.75);
  vec3 au = r2 < 0.45 ? mix(CLAY, SAFFRON, 0.25) : r2 < 0.8 ? mix(SAFFRON, CANOPY, 0.35) : r2 < 0.9 ? SAFFRON : mix(CLAY, MOSS, 0.55);
  return mix(g, au, smoothstep(1.95 + 0.4 * r, 2.3 + 0.4 * r, ys));
}`;

const LEAF_VERT = /* glsl */`
${COMMON}
${BONE_FETCH}
${TREE_U}
${LEAF_COLOR}
attribute vec4 aA; // bone, t, size, rand
attribute vec4 aQ; // local orientation
attribute vec4 aB; // local offset xyz, detach threshold
attribute float aJ; // 1 juvenile, 2 cotyledon
uniform float uTreeScale, uLeafSize, uGrowth, uCotVis;
varying vec3 vW; varying vec3 vN; varying vec2 vL; varying vec3 vCol; varying float vR;
vec3 qrot(vec4 q, vec3 v){ return v + 2.0 * cross(q.xyz, cross(q.xyz, v) + q.w * v); }
void main(){
  int bi = int(aA.x);
  mat4 M = boneM(bi); vec4 D = boneD(bi);
  float ys = mod(uSeason, 4.0), r = aA.w;
  float grow = smoothstep(0.02 + 0.35 * r, 0.3 + 0.4 * r, ys) * step(ys, aB.w);
  float vis = grow * smoothstep(0.35, 0.9, D.w);
  if (aJ > 1.5) vis = uCotVis; else if (aJ > 0.5) vis *= 1.0 - smoothstep(0.3, 0.42, uGrowth);
  // flutter about the petiole: per-leaf oscillator driven by the wind (kinematic approximation)
  float ph = uStill > 0.5 ? r * 6.0 : uTime * (3.0 + 4.0 * r) + r * 40.0;
  float fl = uWind * (0.12 + 0.3 * r) * sin(ph) + uWind * 0.25;
  vec3 p = position;
  float cf = cos(fl), sf = sin(fl);
  p = vec3(p.x, p.y * cf - p.z * sf, p.y * sf + p.z * cf);
  float sz = aA.z * uLeafSize / uTreeScale * vis;
  vec3 lp = vec3(0.0, aA.y * D.x, 0.0) + aB.xyz * vis / uTreeScale + qrot(aQ, p * sz);
  vec4 w = M * vec4(lp, 1.0);
  vec3 n = vec3(0.0, cf, sf);
  vN = normalize(mat3(M) * qrot(aQ, n));
  vW = w.xyz; vL = position.xz; vR = r;
  vCol = leafColor(ys, r);
  if (aJ > 1.5) vCol = mix(SPROUT, CANOPY, 0.3);
  gl_Position = vis < 0.001 ? vec4(0.0, 0.0, 2.0, 1.0) : projectionMatrix * viewMatrix * w;
}`;

const LEAF_FRAG = /* glsl */`
${COMMON}
${SKYLUT}
${TREE_U}
varying vec3 vW; varying vec3 vN; varying vec2 vL; varying vec3 vCol; varying float vR;
float veins(vec2 P){
  float ay = abs(P.y);
  float mid = 1.0 - smoothstep(0.006, 0.014, ay) ;
  float phi = P.x - ay * 0.95 - ay * ay * 1.6;
  float k = phi / 0.075, dv = abs(k - floor(k + 0.5)) * 0.075 / (1.0 + 3.0 * ay);
  float sec = (1.0 - smoothstep(0.003, 0.008, dv)) * smoothstep(0.02, 0.05, ay) * (1.0 - smoothstep(0.26, 0.36, ay));
  return max(mid * step(0.02, P.x), sec * 0.8);
}
void main(){
  if (h21(ivec2(gl_FragCoord.xy)) > uVis) discard;
  vec3 V = normalize(cameraPosition - vW);
  vec3 n = normalize(vN); if (!gl_FrontFacing) n = -n;
  float vn = veins(vL);
  vec3 a = vCol * (0.85 + 0.25 * vnoise(vL * 60.0)) ;
  a = mix(a, a * 1.45 + SPROUT * 0.04, vn * 0.6);
  float ndl = dot(n, uSunDir);
  float diff = max(ndl, 0.0);
  // translucency: sunlight through the blade when the viewer faces the sun (thin-slab approximation)
  float back = max(-ndl, 0.0) * pow(sat(dot(-V, uSunDir)) , 2.0);
  vec3 trans = vCol * vec3(1.1, 1.25, 0.6) * back * (1.0 - vn * 0.7) * 1.4;
  float spec = pow(max(dot(reflect(-uSunDir, n), V), 0.0), 24.0) * 0.25;
  vec3 c = a * (uSunCol * diff + uAmb * (0.5 + 0.5 * n.y) + uMoonCol * max(dot(n, uMoonDir), 0.0)) + uSunCol * (trans + spec * vec3(0.8, 0.9, 0.8));
  c = aerial(c, vW, 0.0045);
  gl_FragColor = vec4(mix(uVoid, c, uEnv), 1.0);
}`;

// Falling leaves use the same fragment shader with a per-instance colour.
const FALL_VERT = /* glsl */`
${COMMON}
${TREE_U}
${LEAF_COLOR}
attribute vec4 aF; // rand, landed, fade, unused
varying vec3 vW; varying vec3 vN; varying vec2 vL; varying vec3 vCol; varying float vR;
void main(){
  vec4 w = modelMatrix * instanceMatrix * vec4(position, 1.0);
  vW = w.xyz; vN = normalize(mat3(instanceMatrix) * vec3(0.0, 1.0, 0.0)); vL = position.xz; vR = aF.x;
  vCol = leafColor(3.0, aF.x) * mix(1.0, 0.55, aF.y) * aF.z;
  gl_Position = aF.z < 0.01 ? vec4(0.0, 0.0, 2.0, 1.0) : projectionMatrix * viewMatrix * w;
}`;

// Heart-shaped leaf with a drip tip, folded along the midrib. Blade along +x, normal +y.
function leafGeometry() {
  const N = 12, pos = [], idx = [];
  // cordate base, broadest near a third, long drip tip
  const width = (t) => 0.36 * Math.pow(Math.sin(Math.PI * Math.pow(t, 0.72)), 0.85) * (1 - 0.35 * t * t);
  for (let i = 0; i <= N; i++) {
    const t = i / N, w = width(t);
    const arch = -0.12 * (t - 0.4) * (t - 0.4) + 0.02;
    pos.push(t, arch - w * 0.18, -w, t, arch + 0.015, 0, t, arch - w * 0.18, w);
  }
  for (let i = 0; i < N; i++) {
    const a = i * 3;
    idx.push(a, a + 3, a + 1, a + 1, a + 3, a + 4, a + 1, a + 4, a + 2, a + 2, a + 4, a + 5);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}

// ---------------------------------------------------------------- the tree object
export class Tree {
  constructor(shared, quality) {
    const { B, L } = generate(quality.tier);
    const n = B.parent.length; this.n = n; this.B = B;
    // Rest pose in parent frames.
    this.restQ = B.wq.map((q, i) => (B.parent[i] < 0 ? q : qMul(qInv(B.wq[B.parent[i]]), q)));
    this.rest = new Float32Array(n * 9);
    for (let i = 0; i < n; i++) rotFromQ(this.restQ[i], this.rest, i * 9);
    // Spring parameters per depth: natural frequency (Hz), damping ratio, gain (rad per unit wind).
    const F = [0.3, 0.55, 0.95, 1.7], Z = [0.3, 0.22, 0.16, 0.12], G = [0.01, 0.045, 0.08, 0.14];
    this.w = new Float32Array(n); this.z = new Float32Array(n); this.gain = new Float32Array(n);
    for (let i = 0; i < n; i++) { const d = B.depth[i]; this.w[i] = F[d] * 2 * Math.PI * (0.9 + 0.2 * ((i * 0.618) % 1)); this.z[i] = Z[d]; this.gain[i] = G[d]; }
    this.th = new Float32Array(n * 2); this.om = new Float32Array(n * 2);
    this.R = new Float32Array(n * 9); this.T = new Float32Array(n * 3); this.lenCur = new Float32Array(n);
    this.tex = new THREE.DataTexture(new Float32Array(n * 5 * 4), 5, n, THREE.RGBAFormat, THREE.FloatType);
    this.tex.needsUpdate = true;

    this.u = Object.assign({}, shared, {
      uBones: { value: this.tex }, uVis: { value: 1 }, uCut: { value: 0 }, uHideUnder: { value: 0 },
      uYouth: { value: 1 }, uSnow: { value: 0 }, uWind: { value: 0.3 }, uSeason: { value: 1 },
      uTreeScale: { value: 1 }, uLeafSize: { value: 0.17 }, uGrowth: { value: 0 }, uCotVis: { value: 0 },
    });

    // Bark: one tapered cylinder per bone.
    const cyl = new THREE.CylinderGeometry(1, 1, 1, 9, 2, true); cyl.translate(0, 0.5, 0);
    const bg = new THREE.InstancedBufferGeometry(); bg.setIndex(cyl.index); bg.setAttribute('position', cyl.attributes.position);
    bg.setAttribute('aBone', new THREE.InstancedBufferAttribute(Float32Array.from({ length: n }, (_, i) => i), 1));
    bg.instanceCount = n;
    this.bark = new THREE.Mesh(bg, new THREE.ShaderMaterial({ uniforms: this.u, vertexShader: BARK_VERT, fragmentShader: BARK_FRAG }));
    this.bark.frustumCulled = false;

    // Leaves: local placement relative to their bone, computed from the rest pose.
    const nl = L.length; this.nl = nl;
    const aA = new Float32Array(nl * 4), aQ = new Float32Array(nl * 4), aB = new Float32Array(nl * 4), aJ = new Float32Array(nl);
    const R = rng(4);
    this.leafBone = new Int32Array(nl); this.leafT = new Float32Array(nl); this.leafOff = new Float32Array(nl * 3);
    this.leafQ = new Float32Array(nl * 4); this.leafSize = new Float32Array(nl); this.leafRand = new Float32Array(nl);
    this.detach = new Float32Array(nl); this.juvenile = new Uint8Array(nl);
    for (let i = 0; i < nl; i++) {
      const [bone, t, az, size, rand, juv, cot] = L[i];
      const D = B.dir[bone], wq = B.wq[bone];
      const ref = Math.abs(D[1]) < 0.95 ? UP : [1, 0, 0];
      const px = v3.norm(v3.cross(ref, D)), py = v3.cross(D, px);
      const out = v3.add(v3.mul(px, Math.cos(az)), v3.mul(py, Math.sin(az)));
      let X, Y;
      if (cot) { X = v3.norm(v3.add(out, [0, 0.25, 0])); Y = v3.norm(v3.sub(UP, v3.mul(X, v3.dot(UP, X)))); }
      else {
        const droop = 0.35 + R() * 0.7;
        X = v3.norm(v3.add(v3.mul(out, Math.cos(droop)), v3.add(v3.mul(UP, -Math.sin(droop) * 0.8), v3.mul(D, 0.25))));
        let up = v3.norm(v3.add(UP, [(R() - 0.5) * 0.8, 0, (R() - 0.5) * 0.8]));
        Y = v3.norm(v3.sub(up, v3.mul(X, v3.dot(up, X))));
      }
      const Zv = v3.cross(X, Y);
      const lq = qMul(qInv(wq), qFromBasis(X, Y, Zv));
      const off = qRot(qInv(wq), v3.mul(out, cot ? 0.004 : 0.03 * size));
      aA.set([bone, t, size * (cot ? 0.5 : 1), rand], i * 4);
      aQ.set(lq, i * 4);
      const det = cot ? 99 : 2.35 + 0.35 * rand + 0.45 * R();
      aB.set([off[0], off[1], off[2], det], i * 4);
      aJ[i] = cot ? 2 : juv ? 1 : 0;
      this.leafBone[i] = bone; this.leafT[i] = t; this.leafOff.set(off, i * 3); this.leafQ.set(lq, i * 4);
      this.leafSize[i] = size; this.leafRand[i] = rand; this.detach[i] = det; this.juvenile[i] = juv ? 1 : 0;
    }
    const lg = leafGeometry();
    const ig = new THREE.InstancedBufferGeometry(); ig.setIndex(lg.index); ig.setAttribute('position', lg.attributes.position);
    ig.setAttribute('aA', new THREE.InstancedBufferAttribute(aA, 4));
    ig.setAttribute('aQ', new THREE.InstancedBufferAttribute(aQ, 4));
    ig.setAttribute('aB', new THREE.InstancedBufferAttribute(aB, 4));
    ig.setAttribute('aJ', new THREE.InstancedBufferAttribute(aJ, 1));
    ig.instanceCount = nl;
    this.leafMat = new THREE.ShaderMaterial({ uniforms: this.u, vertexShader: LEAF_VERT, fragmentShader: LEAF_FRAG, side: THREE.DoubleSide });
    this.leaves = new THREE.Mesh(ig, this.leafMat);
    this.leaves.frustumCulled = false;

    this.fall = new FallingLeaves(this, lg, quality);
    this.prevYs = -1;
    this.scale = 1; this.rg = 1; this._m = new Float32Array(9);
    this.focus = this.pickFocusLeaf();
  }

  addTo(scene) { scene.add(this.bark, this.leaves, this.fall.mesh); }

  // Growth: overall scale, radius growth and per-bone reveal.
  growthParams(g) {
    this.scale = 0.24 + 0.76 * sstep(0.15, 1.0, g);
    this.u.uLeafSize.value = 0.17 + 0.15 * sstep(0.3, 1.0, g);
    this.rg = 0.1 + 0.9 * Math.pow(g, 1.5);
  }

  // Choose the leaf the cell dive falls into: a sapling leaf facing the camera.
  pickFocusLeaf() {
    let best = -1, score = -1e9;
    for (let i = 0; i < this.nl; i++) {
      const b = this.leafBone[i];
      if (!this.juvenile[i] || this.B.birth[b] > 0.09 || this.B.depth[b] !== 1) continue;
      const q = qMul(this.B.wq[b], Array.from(this.leafQ.subarray(i * 4, i * 4 + 4)));
      const n = qRot(q, UP), P = this.B.pos[b];
      const s = n[2] * 1.2 + n[1] * 0.5 + P[2] * 0.4 - Math.abs(P[0]) * 0.3 + this.leafSize[i];
      if (s > score) { score = s; best = i; }
    }
    return best;
  }

  // One simulation + upload step. dt = 0 means a still pose (no dynamics).
  update(s, time, dt) {
    const B = this.B, n = this.n, g = s.growth;
    this.growthParams(g);
    const S = this.scale, rgw = this.rg;
    const R = this.R, T = this.T, rest = this.rest, th = this.th, om = this.om;
    const d = this.tex.image.data;
    const wind = s.wind;
    const steps = dt > 0 ? Math.min(3, Math.ceil(dt / (1 / 60))) : 0, h = steps ? Math.min(dt, 0.05) / steps : 0;
    // hook: the young shoot bends over while it is still underground
    const tipAbove = SEED[1] + S * this.trunkRevealLen(g);
    const hook = 1.5 * (1 - sstep(-0.02, 0.06, tipAbove)) * (g > 0 ? 1 : 0);
    const m = this._m;
    for (let i = 0; i < n; i++) {
      const p = B.parent[i];
      const rev = sat((g - B.birth[i]) / B.dur[i]);
      const L = B.len[i] * rev; this.lenCur[i] = L;
      // parent frame
      let px = 0, py = 0, pz = 0;
      if (p >= 0) {
        const at = B.at[i] * this.lenCur[p], o = p * 9;
        px = T[p * 3] + R[o + 1] * at; py = T[p * 3 + 1] + R[o + 4] * at; pz = T[p * 3 + 2] + R[o + 7] * at;
      }
      // rest rotation times parent
      const o = i * 9, ro = i * 9;
      if (p >= 0) mul3(R, p * 9, rest, ro, m, 0); else for (let k = 0; k < 9; k++) m[k] = rest[ro + k];
      // spring-damped deflection (2 DOF about the bone's local x and z axes)
      let tx = th[i * 2], tz = th[i * 2 + 1];
      if (steps && L > 0) {
        const dx = m[1], dy = m[4], dz = m[7];
        const wx = px * S, wz = pz * S;
        const gust = 0.55 + 0.45 * noise1(time * 0.33 - (wx * WIND_DIR[0] + wz * WIND_DIR[2]) * 0.09) + 0.25 * (noise1(time * 1.7 + i * 0.37) - 0.5);
        const f = wind * gust;
        // torque axis = dir x wind, taken into the bone frame (m^T * axis)
        const ax = dy * WIND_DIR[2] - dz * WIND_DIR[1], ay = dz * WIND_DIR[0] - dx * WIND_DIR[2], az = dx * WIND_DIR[1] - dy * WIND_DIR[0];
        const lx = m[0] * ax + m[3] * ay + m[6] * az, lz = m[2] * ax + m[5] * ay + m[8] * az;
        const w = this.w[i], z = this.z[i], k = this.gain[i] * f;
        let ox = om[i * 2], oz = om[i * 2 + 1];
        for (let st = 0; st < steps; st++) {
          ox += (w * w * (k * lx - tx) - 2 * z * w * ox) * h; tx += ox * h;
          oz += (w * w * (k * lz - tz) - 2 * z * w * oz) * h; tz += oz * h;
        }
        om[i * 2] = ox; om[i * 2 + 1] = oz; th[i * 2] = tx; th[i * 2 + 1] = tz;
      } else if (!steps) { tx = 0; tz = 0; }
      let bx = tx, bz = tz;
      if (hook > 0 && B.depth[i] === 0) { const ti = B.trunk.indexOf(i); if (ti >= 2) bz += hook * (ti === 4 ? 0.7 : ti === 3 ? 0.35 : 0.1); }
      // R_i = m * Rdef(bx, bz)
      const ang = Math.hypot(bx, bz);
      if (ang > 1e-6) {
        const ux = bx / ang, uz = bz / ang, c = Math.cos(ang), sn = Math.sin(ang), t1 = 1 - c;
        const r00 = c + ux * ux * t1, r01 = -uz * sn, r02 = ux * uz * t1;
        const r10 = uz * sn, r11 = c, r12 = -ux * sn;
        const r20 = uz * ux * t1, r21 = ux * sn, r22 = c + uz * uz * t1;
        for (let row = 0; row < 3; row++) {
          const a0 = m[row * 3], a1 = m[row * 3 + 1], a2 = m[row * 3 + 2];
          R[o + row * 3] = a0 * r00 + a1 * r10 + a2 * r20;
          R[o + row * 3 + 1] = a0 * r01 + a1 * r11 + a2 * r21;
          R[o + row * 3 + 2] = a0 * r02 + a1 * r12 + a2 * r22;
        }
      } else for (let k = 0; k < 9; k++) R[o + k] = m[k];
      T[i * 3] = px; T[i * 3 + 1] = py; T[i * 3 + 2] = pz;
      // upload: world = seed + S * (R | T), column-major into 4 texels, then (len, r0, r1, reveal)
      const b = i * 20;
      d[b] = R[o] * S; d[b + 1] = R[o + 3] * S; d[b + 2] = R[o + 6] * S; d[b + 3] = 0;
      d[b + 4] = R[o + 1] * S; d[b + 5] = R[o + 4] * S; d[b + 6] = R[o + 7] * S; d[b + 7] = 0;
      d[b + 8] = R[o + 2] * S; d[b + 9] = R[o + 5] * S; d[b + 10] = R[o + 8] * S; d[b + 11] = 0;
      d[b + 12] = SEED[0] + px * S; d[b + 13] = SEED[1] + py * S; d[b + 14] = SEED[2] + pz * S; d[b + 15] = 1;
      const taper = rev < 1 ? rev : 1;
      d[b + 16] = L; d[b + 17] = B.r0[i] * rgw * (0.4 + 0.6 * taper); d[b + 18] = B.r1[i] * rgw * taper; d[b + 19] = rev;
    }
    this.tex.needsUpdate = true;

    const u = this.u, ys = ((s.season % 4) + 4) % 4;
    u.uTreeScale.value = S; u.uGrowth.value = g;
    u.uYouth.value = 1 - sstep(0.12, 0.4, g);
    u.uCotVis.value = sstep(-0.01, 0.03, tipAbove) * (1 - sstep(0.12, 0.2, g));
    u.uVis.value = s.treeVis; u.uCut.value = s.cut; u.uHideUnder.value = s.hideUnder;
    u.uWind.value = wind; u.uSeason.value = s.season;
    u.uSnow.value = sstep(3.15, 3.45, ys) * (1 - sstep(3.9, 4.0, ys));
    this.bark.visible = this.leaves.visible = s.treeVis > 0.002;
    this.fall.update(s, ys, time, dt);
  }

  trunkRevealLen(g) {
    let L = 0; for (const i of this.B.trunk) L += this.B.len[i] * sat((g - this.B.birth[i]) / this.B.dur[i]);
    return L;
  }

  // World pose of leaf i (position into out3, basis columns into X/Y/Z arrays).
  leafWorld(i, out, X, Y) {
    const b = this.leafBone[i], o = b * 9, S = this.scale, R = this.R, T = this.T;
    const lq = this.leafQ.subarray(i * 4, i * 4 + 4);
    const t = this.leafT[i] * this.lenCur[b];
    const lp = [this.leafOff[i * 3] / S, t + this.leafOff[i * 3 + 1] / S, this.leafOff[i * 3 + 2] / S];
    const mulR = (v) => [R[o] * v[0] + R[o + 1] * v[1] + R[o + 2] * v[2], R[o + 3] * v[0] + R[o + 4] * v[1] + R[o + 5] * v[2], R[o + 6] * v[0] + R[o + 7] * v[1] + R[o + 8] * v[2]];
    const wp = mulR(lp);
    out[0] = SEED[0] + S * (T[b * 3] + wp[0]); out[1] = SEED[1] + S * (T[b * 3 + 1] + wp[1]); out[2] = SEED[2] + S * (T[b * 3 + 2] + wp[2]);
    const x = mulR(qRot(lq, [1, 0, 0])), y = mulR(qRot(lq, [0, 1, 0]));
    X[0] = x[0]; X[1] = x[1]; X[2] = x[2]; Y[0] = y[0]; Y[1] = y[1]; Y[2] = y[2];
  }
}

function mul3(A, ao, Bm, bo, out, oo) {
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    out[oo + r * 3 + c] = A[ao + r * 3] * Bm[bo + c] + A[ao + r * 3 + 1] * Bm[bo + 3 + c] + A[ao + r * 3 + 2] * Bm[bo + 6 + c];
  }
}

// ---------------------------------------------------------------- falling leaves
// Each detached leaf is a rigid thin plate: gravity, quadratic drag split into
// normal and tangential parts, and a pitching torque that turns the blade
// broadside to the relative wind. Under-damped, it flutters and glides like a
// real leaf. Pooled; landed leaves stay on the ground until the pool recycles them.
class FallingLeaves {
  constructor(tree, geo, quality) {
    this.tree = tree;
    const P = quality.tier === 'high' ? 220 : 110; this.P = P;
    this.pos = new Float32Array(P * 3); this.vel = new Float32Array(P * 3);
    this.q = new Float32Array(P * 4); this.w = new Float32Array(P * 3);
    this.state = new Uint8Array(P); this.age = new Float32Array(P); this.rand = new Float32Array(P);
    this.size = new Float32Array(P); this.src = new Int32Array(P).fill(-1);
    this.attached = new Uint8Array(tree.nl);
    const ig = new THREE.InstancedBufferGeometry(); ig.setIndex(geo.index); ig.setAttribute('position', geo.attributes.position);
    this.aF = new THREE.InstancedBufferAttribute(new Float32Array(P * 4), 4); this.aF.setUsage(THREE.DynamicDrawUsage);
    ig.setAttribute('aF', this.aF);
    const mat = new THREE.ShaderMaterial({ uniforms: tree.u, vertexShader: FALL_VERT, fragmentShader: LEAF_FRAG, side: THREE.DoubleSide });
    this.mesh = new THREE.InstancedMesh(ig, mat, P);
    this.mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.mesh.frustumCulled = false;
    this._p = [0, 0, 0]; this._X = [0, 0, 0]; this._Y = [0, 0, 0];
    this.m4 = new THREE.Matrix4(); this.qq = new THREE.Quaternion(); this.vp = new THREE.Vector3(); this.vs = new THREE.Vector3();
    this.cursor = 0; this.lastYs = -1;
  }

  slot() {
    // free slot first, then the oldest landed leaf
    for (let k = 0; k < this.P; k++) { const i = (this.cursor + k) % this.P; if (this.state[i] === 0) { this.cursor = i + 1; return i; } }
    let best = -1, age = -1;
    for (let i = 0; i < this.P; i++) if (this.state[i] === 2 && this.age[i] > age) { age = this.age[i]; best = i; }
    return best;
  }

  spawn(li) {
    const k = this.slot(); if (k < 0) return;
    const t = this.tree; t.leafWorld(li, this._p, this._X, this._Y);
    const X = this._X, Y = this._Y, Z = v3.cross(X, Y);
    const q = qFromBasis(X, Y, Z);
    this.pos.set(this._p, k * 3); this.vel.set([0, 0, 0], k * 3); this.q.set(q, k * 4);
    this.w.set([(Math.random() - 0.5) * 2, (Math.random() - 0.5) * 2, (Math.random() - 0.5) * 2], k * 3);
    this.state[k] = 1; this.age[k] = 0; this.rand[k] = t.leafRand[li]; this.size[k] = t.leafSize[li] * t.u.uLeafSize.value; this.src[k] = li;
  }

  step(k, h, time, wind) {
    const p = this.pos, v = this.vel, q = this.q, w = this.w, o3 = k * 3, o4 = k * 4;
    const qx = q[o4], qy = q[o4 + 1], qz = q[o4 + 2], qw = q[o4 + 3];
    // blade normal = q * (0,1,0)
    const nx = 2 * (qx * qy - qz * qw), ny = 1 - 2 * (qx * qx + qz * qz), nz = 2 * (qy * qz + qx * qw);
    const gust = wind * (0.5 + 0.8 * noise1(time * 0.4 - p[o3] * 0.1 + k));
    const rx = v[o3] - WIND_DIR[0] * gust, ry = v[o3 + 1], rz = v[o3 + 2] - WIND_DIR[2] * gust;
    const vn = rx * nx + ry * ny + rz * nz, sp = Math.hypot(rx, ry, rz) + 1e-6;
    const tx = rx - vn * nx, ty = ry - vn * ny, tz = rz - vn * nz, tl = Math.hypot(tx, ty, tz);
    const KN = 6.5, KT = 0.35;
    const ax = -KN * Math.abs(vn) * vn * nx - KT * tl * tx;
    const ay = -KN * Math.abs(vn) * vn * ny - KT * tl * ty - 9.81;
    const az = -KN * Math.abs(vn) * vn * nz - KT * tl * tz;
    v[o3] += ax * h; v[o3 + 1] += ay * h; v[o3 + 2] += az * h;
    p[o3] += v[o3] * h; p[o3 + 1] += v[o3 + 1] * h; p[o3 + 2] += v[o3 + 2] * h;
    // pitching torque ~ sin(2 alpha): turns the normal toward +/- the relative wind
    const hx = rx / sp, hy = ry / sp, hz = rz / sp, dn = nx * hx + ny * hy + nz * hz;
    const cx = ny * hz - nz * hy, cy = nz * hx - nx * hz, cz = nx * hy - ny * hx;
    const KT2 = 9 * sp * sp * dn, DAMP = 1.1;
    w[o3] += (KT2 * cx - DAMP * w[o3]) * h; w[o3 + 1] += (KT2 * cy - DAMP * w[o3 + 1] + 0.6 * (this.rand[k] - 0.5)) * h; w[o3 + 2] += (KT2 * cz - DAMP * w[o3 + 2]) * h;
    // integrate orientation: q += 0.5 * (w, 0) * q
    const wx = w[o3], wy = w[o3 + 1], wz = w[o3 + 2];
    let nqx = qx + 0.5 * h * (wx * qw + wy * qz - wz * qy);
    let nqy = qy + 0.5 * h * (wy * qw + wz * qx - wx * qz);
    let nqz = qz + 0.5 * h * (wz * qw + wx * qy - wy * qx);
    let nqw = qw + 0.5 * h * (-wx * qx - wy * qy - wz * qz);
    const l = Math.hypot(nqx, nqy, nqz, nqw); q[o4] = nqx / l; q[o4 + 1] = nqy / l; q[o4 + 2] = nqz / l; q[o4 + 3] = nqw / l;
    if (p[o3 + 1] < 0.006) { // landed: lie flat, keep heading
      p[o3 + 1] = 0.004 + 0.002 * this.rand[k]; this.state[k] = 2;
      const yaw = Math.atan2(2 * (qw * qy + qx * qz), 1 - 2 * (qy * qy + qx * qx));
      q.set([0, Math.sin(yaw / 2), 0, Math.cos(yaw / 2)], o4);
      if (ny < 0) { const qf = qMul(q.subarray(o4, o4 + 4), [1, 0, 0, 0]); q.set(qf, o4); }
    }
  }

  // Still pose for reduced motion: deterministic, from the season alone.
  stillPose(ys) {
    const t = this.tree; let k = 0;
    this.state.fill(0);
    if (ys < 2.35 || ys > 3.6) return;
    const order = [];
    for (let i = 0; i < t.nl; i++) if (!t.juvenile[i] && ys > t.detach[i]) order.push(i);
    order.sort((a, b) => t.detach[b] - t.detach[a]);
    for (const li of order) {
      if (k >= this.P) break;
      t.leafWorld(li, this._p, this._X, this._Y);
      const f = sat((ys - t.detach[li]) / 0.25), r = t.leafRand[li];
      const y0 = this._p[1];
      const px = this._p[0] + WIND_DIR[0] * f * 1.8 + (r - 0.5) * f * 1.2, pz = this._p[2] + WIND_DIR[2] * f * 1.8 + (((r * 7) % 1) - 0.5) * f * 1.2;
      const landed = f >= 1;
      const py = landed ? 0.005 : y0 * (1 - f);
      this.pos.set([px, py, pz], k * 3);
      const q = landed ? [0, Math.sin(r * 3), 0, Math.cos(r * 3)] : v3.norm([Math.sin(r * 9), Math.cos(r * 5), Math.sin(r * 13)]).concat([0]);
      if (!landed) { const a = r * 5, s = Math.sin(a); q[0] *= s; q[1] *= s; q[2] *= s; q[3] = Math.cos(a); }
      this.q.set(q, k * 4); this.state[k] = landed ? 2 : 1; this.rand[k] = r; this.size[k] = t.leafSize[li] * t.u.uLeafSize.value; this.age[k] = 0;
      k++;
    }
  }

  update(s, ys, time, dt) {
    const t = this.tree, still = dt <= 0;
    if (still) this.stillPose(ys);
    else {
      // detect leaves whose detach threshold we just crossed going forward
      const fwd = this.lastYs >= 0 && ys > this.lastYs && ys - this.lastYs < 1;
      let spawned = 0;
      for (let i = 0; i < t.nl; i++) {
        const b = t.leafBone[i];
        const on = s.treeVis > 0.5 && ys < t.detach[i] && ys > 0.3 && t.B.birth[b] < s.growth && !(t.juvenile[i] && s.growth > 0.36) ? 1 : 0;
        if (this.attached[i] && !on && fwd && ys >= t.detach[i] && spawned < 12) { this.spawn(i); spawned++; }
        this.attached[i] = on;
      }
      this.lastYs = ys;
      const steps = Math.min(4, Math.max(1, Math.ceil(dt / (1 / 90)))), h = Math.min(dt, 0.05) / steps;
      for (let k = 0; k < this.P; k++) {
        if (this.state[k] === 1) { for (let st = 0; st < steps; st++) { this.step(k, h, time, s.wind); if (this.state[k] !== 1) break; } }
        if (this.state[k]) this.age[k] += dt;
      }
      // winter clears the litter, spring starts clean
      if (ys < 0.3 || ys > 3.5) for (let k = 0; k < this.P; k++) if (this.state[k] === 2) this.state[k] = 0;
    }
    const a = this.aF.array, m = this.m4;
    for (let k = 0; k < this.P; k++) {
      const on = this.state[k] && s.treeVis > 0.01 && s.env > 0.01;
      const fade = on ? (this.state[k] === 2 ? 1 - sstep(3.2, 3.45, ys) : 1) : 0;
      a[k * 4] = this.rand[k]; a[k * 4 + 1] = this.state[k] === 2 ? 1 : 0; a[k * 4 + 2] = fade; a[k * 4 + 3] = 0;
      this.qq.set(this.q[k * 4], this.q[k * 4 + 1], this.q[k * 4 + 2], this.q[k * 4 + 3]);
      this.vp.set(this.pos[k * 3], this.pos[k * 3 + 1], this.pos[k * 3 + 2]);
      const sz = this.size[k] || 0.1; this.vs.set(sz, sz, sz);
      m.compose(this.vp, this.qq, this.vs); this.mesh.setMatrixAt(k, m);
    }
    this.aF.needsUpdate = true; this.mesh.instanceMatrix.needsUpdate = true;
    this.mesh.visible = s.treeVis > 0.01;
  }
}
