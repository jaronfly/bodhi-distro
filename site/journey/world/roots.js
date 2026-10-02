// Roots. A 3D root system grown by a stochastic branching process (taproot with
// gravitropism, laterals at golden-angle azimuths, fine roots), revealed by
// arc length so it grows from the seed outward. It is drawn pressed against the
// cut face, like roots behind the glass of a rhizotron, and lights up as a graph
// in three stages: persistence (the taproot), continuity (laterals, nodes and
// pulses) and rapport (mycorrhizal links that turn the tree into a network).
import * as THREE from '../vendor/three.module.min.js';
import { COMMON } from '../shaders/common.js';
import { rng, v3 } from '../core/math.js';
import { SEED } from './tree.js';

const GOLDEN = Math.PI * (3 - Math.sqrt(5));

export function buildRoots() {
  const R = rng(1987);
  const segs = []; // [p0, p1, r0, r1, s0, s1, stage]
  const nodes = []; // [pos, order, stage]
  let maxS = 0;
  const grow = (P, D, len, r, stage, s0, depth) => {
    const step = stage === 0 ? 0.045 : 0.038, n = Math.max(2, Math.round(len / step));
    let s = s0, az = R() * 6.28;
    for (let i = 0; i < n; i++) {
      const g = stage === 0 ? 0.22 : 0.025 + 0.03 * depth;
      D = v3.norm(v3.add(D, [(R() - 0.5) * 0.5, -g + (R() - 0.5) * 0.2, (R() - 0.5) * 0.3]));
      const Q = v3.add(P, v3.mul(D, step));
      const r1 = r * (1 - 0.8 * (i + 1) / n);
      segs.push([P, Q, r * (1 - 0.8 * i / n), r1, s, s + step, stage]);
      s += step; maxS = Math.max(maxS, s);
      if (stage === 0 && i >= 2 && i < n - 3 && R() < 0.7) {
        const k = R() < 0.35 ? 2 : 1;
        for (let j = 0; j < k; j++) {
          az += GOLDEN * 2;
          const side = Math.cos(az) >= 0 ? 1 : -1;
          const out = [side * (0.7 + 0.3 * R()), -0.05 - R() * 0.35, Math.sin(az) * 0.5];
          nodes.push([Q, s, 1]);
          grow(Q, v3.norm(out), (1.25 - i / n * 0.7) * (0.6 + R() * 0.6), r * 0.55, 1, s, 1);
        }
      } else if (stage === 1 && depth < 3 && i >= 1 && R() < 0.33) {
        az += GOLDEN * 2;
        const out = v3.norm(v3.add(D, [Math.cos(az) * 1.3, -0.25 + (R() - 0.5) * 0.6, Math.sin(az) * 0.6]));
        nodes.push([Q, s, 2]);
        grow(Q, out, (0.16 + R() * 0.28) / depth, r * 0.6, 1, s, depth + 1);
      }
      P = Q;
    }
    nodes.push([P, s, stage === 0 ? 0 : 2]);
  };
  grow(SEED, [0.02, -1, 0], 1.25, 0.0065, 0, 0, 0);
  // mycorrhizal links between nearby tips of different laterals
  const tips = nodes.filter((n) => n[2] === 2);
  const links = [];
  for (let i = 0; i < tips.length; i++) for (let j = i + 1; j < tips.length; j++) {
    const a = tips[i][0], b = tips[j][0];
    const dx = a[0] - b[0], dy = a[1] - b[1];
    const d = Math.hypot(dx, dy);
    if (d > 0.06 && d < 0.22 && Math.abs(tips[i][1] - tips[j][1]) > 0.15 && links.length < 70 && R() < 0.5) links.push([a, b, Math.max(tips[i][1], tips[j][1])]);
  }
  return { segs, nodes, links, maxS };
}

const VERT = /* glsl */`
attribute vec4 aP; // p0.xy, p1.xy (flattened)
attribute vec4 aZ; // z0, z1, r0, r1
attribute vec4 aS; // s0, s1 (normalised arc length), stage, link flag
uniform float uGrow, uCut, uScale, uFlat;
uniform vec3 uSeed;
varying vec2 vUv; varying float vS; varying float vStage; varying float vLink; varying float vW; varying float vAlong;
void main(){
  float s0 = aS.x, s1 = aS.y;
  float t = clamp((uGrow - s0) / max(s1 - s0, 1e-4), 0.0, 1.0);
  vec2 p0 = aP.xy, p1 = mix(aP.xy, aP.zw, t);
  vec2 d = p1 - p0; float L = length(d); vec2 dir = L > 1e-6 ? d / L : vec2(0.0, -1.0);
  vec2 nrm = vec2(-dir.y, dir.x);
  float r = mix(aZ.z, aZ.w, position.x) * (aS.w > 0.5 ? 0.35 : 1.0);
  float wpx = r * 2.0 + 0.016;      // glow margin
  vec2 p = mix(p0, p1, position.x) + nrm * position.y * wpx;
  p = uSeed.xy + (p - uSeed.xy) * uScale;
  float z = uCut + 0.006 + mix(aZ.x, aZ.y, position.x) * uFlat;
  vUv = vec2(position.x, position.y * wpx / max(r, 1e-4));
  vS = mix(s0, s0 + (s1 - s0) * t, position.x); vStage = aS.z; vLink = aS.w; vW = r; vAlong = position.x * L;
  gl_Position = t <= 0.0 ? vec4(0.0, 0.0, 2.0, 1.0) : projectionMatrix * viewMatrix * vec4(p, z, 1.0);
}`;
const FRAG = /* glsl */`
${COMMON}
uniform float uLight, uTime, uVis, uGrow;
uniform vec3 uAmbR;
varying vec2 vUv; varying float vS; varying float vStage; varying float vLink; varying float vW; varying float vAlong;
void main(){
  float x = abs(vUv.y);
  float core = 1.0 - smoothstep(0.7, 1.05, x);
  float glow = exp(-x * x * 0.03) * 0.5 + exp(-x * 0.35) * 0.5;
  // stage lighting: 1 taproot, 2 laterals + pulses, 3 links
  float lit = vLink > 0.5 ? smoothstep(2.0, 3.0, uLight) : vStage < 0.5 ? smoothstep(0.0, 1.0, uLight) : smoothstep(1.0, 2.0, uLight) * (vStage > 1.5 ? 0.6 : 1.0);
  float pulse = 0.0;
  if (uLight > 1.0) { float ph = fract(vS * 2.2 - uTime * 0.12); pulse = exp(-pow((ph - 0.5) * 9.0, 2.0)) * smoothstep(1.0, 2.0, uLight); }
  vec3 root = mix(BONE * 0.16, LICHEN * 0.12, vStage * 0.5) ;
  vec3 c = root * core * (1.0 - vLink);
  vec3 g = mix(SPROUT, BONE, vLink * 0.3) * (glow * (0.05 + 0.3 * lit) + core * lit * 0.35 + pulse * (0.6 * core + 0.25 * glow));
  if (vLink > 0.5) g *= step(0.5, fract(vAlong * 90.0)) * 0.9 + 0.1;
  // the growing tip is brightest
  float tip = exp(-max(uGrow - vS, 0.0) * 40.0) * (1.0 - vLink);
  c += g + SPROUT * tip * core * 0.8;
  gl_FragColor = vec4(c * uVis, 1.0);
}`;

export class Roots {
  constructor() {
    const { segs, nodes, links, maxS } = buildRoots();
    this.nodes = nodes; this.maxS = maxS;
    const all = segs.map((s) => [s[0], s[1], s[2], s[3], s[4] / maxS, s[5] / maxS, s[6], 0])
      .concat(links.map(([a, b, s]) => [a, b, 0.003, 0.003, s / maxS, s / maxS + 0.12, 2, 1]));
    const n = all.length;
    const aP = new Float32Array(n * 4), aZ = new Float32Array(n * 4), aS = new Float32Array(n * 4);
    all.forEach(([p0, p1, r0, r1, s0, s1, st, lk], i) => {
      aP.set([p0[0], p0[1], p1[0], p1[1]], i * 4);
      aZ.set([p0[2] - SEED[2], p1[2] - SEED[2], r0, r1], i * 4);
      aS.set([s0, s1, st, lk], i * 4);
    });
    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([0, -1, 0, 1, -1, 0, 0, 1, 0, 1, 1, 0], 3));
    g.setIndex([0, 1, 2, 2, 1, 3]);
    g.setAttribute('aP', new THREE.InstancedBufferAttribute(aP, 4));
    g.setAttribute('aZ', new THREE.InstancedBufferAttribute(aZ, 4));
    g.setAttribute('aS', new THREE.InstancedBufferAttribute(aS, 4));
    g.instanceCount = n;
    this.u = {
      uGrow: { value: 0 }, uCut: { value: 0 }, uScale: { value: 1 }, uFlat: { value: 0.02 }, uSeed: { value: new THREE.Vector3(...SEED) },
      uLight: { value: 0 }, uTime: { value: 0 }, uVis: { value: 1 }, uAmbR: { value: new THREE.Vector3() },
    };
    this.mesh = new THREE.Mesh(g, new THREE.ShaderMaterial({
      uniforms: this.u, vertexShader: VERT, fragmentShader: FRAG,
      // max blending: overlapping segment ends and crossings never double up
      transparent: true, depthWrite: false, blending: THREE.CustomBlending,
      blendEquation: THREE.MaxEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
    }));
    this.mesh.frustumCulled = false; this.mesh.renderOrder = 5;
    // node positions for the pixel overlay (normalised order, stage)
    this.nodePos = nodes.map((n) => n[0]);
    this.nodeOrder = nodes.map((n) => n[1] / maxS);
    this.nodeStage = nodes.map((n) => n[2]);
  }
  addTo(scene) { scene.add(this.mesh); }
  update(s, time) {
    const u = this.u;
    u.uGrow.value = s.rootGrow; u.uCut.value = s.cut; u.uScale.value = s.rootScale;
    u.uLight.value = s.rootLight; u.uTime.value = time;
    u.uVis.value = s.env;
    this.mesh.visible = s.cut < 100 && s.rootGrow > 0;
  }
}
