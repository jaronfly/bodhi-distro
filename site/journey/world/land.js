// Land: a terrain disc (flat near the tree, rolling farther out), the soil cut
// face (a relief raymarch into a height field, lit by the seed), a treeline
// on the horizon, and wind-blown grass.
import * as THREE from '../vendor/three.module.min.js';
import { COMMON, SKYLUT } from '../shaders/common.js';
import { rng, fbm2, sstep } from '../core/math.js';

export function groundH(x, z) {
  const r = Math.hypot(x, z);
  const hills = (fbm2(x * 0.011 + 3.1, z * 0.011 - 1.7) - 0.47) * 30 * sstep(26, 90, r);
  const ridge = sstep(260, 620, r) * (fbm2(x * 0.0035 + 9, z * 0.0035) * 170 - 20);
  return hills + ridge;
}

const LIGHTING = /* glsl */`
uniform vec3 uSunCol, uAmb, uMoonCol, uMoonDir, uVoid;
uniform float uEnv, uCut, uSnow, uSeason, uTime, uWind;
uniform vec4 uCanopy; // xyz centre, radius
uniform float uCanopyDen;
float canopyShadow(vec3 p){
  // Analytic canopy shadow: project along the sun onto the crown's height and test
  // against a disc, with dapple noise. An approximation, not a shadow map.
  if (uSunDir.y < 0.02 || uCanopyDen < 0.01) return 1.0;
  vec3 c = p + uSunDir * ((uCanopy.y - p.y) / uSunDir.y);
  float d = length(c.xz - uCanopy.xz) / uCanopy.w;
  float dap = 0.55 + 0.45 * vnoise(c.xz * 3.5);
  return 1.0 - uCanopyDen * smoothstep(1.0, 0.55, d) * mix(0.8, 1.0, dap) * 0.85;
}`;

const TERRAIN_VERT = /* glsl */`
varying vec3 vW; varying vec3 vN;
void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vN = normal; gl_Position = projectionMatrix * viewMatrix * w; }`;

const TERRAIN_FRAG = /* glsl */`
${COMMON}
${SKYLUT}
${LIGHTING}
varying vec3 vW; varying vec3 vN;
void main(){
  if (vW.z > uCut) discard;
  vec3 n = normalize(vN);
  float n1 = fbm3(vW.xz * 0.25), n2 = vnoise(vW.xz * 2.7), n3 = vnoise(vW.xz * 0.03);
  float ys = mod(uSeason, 4.0);
  vec3 g = mix(MOSS * 0.5, CANOPY * 0.5, sat(n1 * 1.1 + n3 * 0.3)) * (0.75 + 0.4 * n2);
  g = mix(g, SPROUT * 0.28, 0.35 * smoothstep(0.1, 0.8, ys) * (1.0 - smoothstep(1.2, 1.8, ys)) * n1);
  g = mix(g, mix(SAFFRON, MOSS, 0.6) * 0.3, smoothstep(2.0, 2.6, ys) * (1.0 - smoothstep(3.3, 3.9, ys)) * 0.6);
  float snow = uSnow * smoothstep(0.25, 0.5, n1 + 0.25 * n2 + n.y * 0.2);
  g = mix(g, BONE * 0.62, snow);
  float sh = canopyShadow(vW);
  float ndl = max(dot(n, uSunDir), 0.0);
  vec3 c = g * (uSunCol * ndl * sh + uAmb * (0.6 + 0.4 * n.y) * mix(0.7, 1.0, sh) + uMoonCol * max(dot(n, uMoonDir), 0.0));
  c = aerial(c, vW, 0.0028);
  gl_FragColor = vec4(mix(uVoid, c, uEnv), 1.0);
}`;

const FACE_VERT = /* glsl */`
varying vec3 vW;
void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;

const FACE_FRAG = /* glsl */`
${COMMON}
${SKYLUT}
${LIGHTING}
varying vec3 vW;
uniform vec4 uSeedA, uSeedB;
uniform float uFaceAmb;
const float DEPTH = 0.04;
float hf(vec2 q){
  float s1 = smoothstep(0.6, 0.8, vnoise(q * 8.0 + 3.1));
  float s2 = smoothstep(0.64, 0.82, vnoise(q * 21.0 - 7.3)) * 0.85;
  float gr = vnoise(q * 120.0);
  return max(max(s1, s2) * (0.82 + 0.18 * gr), 0.2 + 0.45 * gr * gr);
}
vec3 albedo(vec2 q, float h){
  float y = q.y + (fbm3(q * vec2(0.8, 1.7)) - 0.5) * 0.24;
  vec3 c = vec3(0.014, 0.012, 0.009);
  c = mix(c, UNDER * 0.95 + vec3(0.004, 0.002, 0.0), smoothstep(-0.1, -0.24, y));
  c = mix(c, mix(MOSS, CLAY, 0.18) * 0.7, smoothstep(-0.55, -0.72, y));
  c = mix(c, mix(MOSS, LICHEN, 0.3) * 0.62, smoothstep(-1.2, -1.45, y));
  c = mix(c, UNDER * 0.6, smoothstep(-2.4, -2.9, y));
  float stone = smoothstep(0.55, 0.8, h);
  c = mix(c, mix(LICHEN * 0.34, SAGE * 0.26, vnoise(q * 40.0)), stone);
  // a thin living fringe right under the soil line
  c = mix(c, CANOPY * 0.12, smoothstep(-0.035, 0.0, q.y + (vnoise(q * vec2(40.0, 4.0)) - 0.5) * 0.02));
  return c * (0.62 + 0.7 * vnoise(q * 300.0));
}
float lightTerm(vec3 hp, vec3 n, vec4 L, vec2 q, float hh){
  if (L.w <= 0.0) return 0.0;
  vec3 ld = L.xyz - hp; float dist = length(ld); ld /= dist;
  float ndl = max(dot(n, ld), 0.0);
  // soft shadow: march toward the light across the height field (4 taps)
  float sh = 1.0;
  vec2 dxy = ld.xy / max(ld.z, 0.08) * (DEPTH * 0.25);
  float rayD = DEPTH * (1.0 - hh);
  for (int i = 1; i <= 4; i++){
    rayD -= DEPTH * 0.25 * sign(ld.z);
    float s = DEPTH * (1.0 - hf(q + dxy * float(i)));
    sh = min(sh, sat(1.0 - (rayD - s) * 60.0));
  }
  return L.w * ndl * mix(0.25, 1.0, sh) / (1.0 + dist * dist * 260.0);
}
void main(){
  vec3 V = normalize(vW - cameraPosition);
  float dz = max(-V.z, 0.3);
  vec2 q = vW.xy, st = V.xy / dz * (DEPTH / 12.0);
  float d = 0.0, hh = hf(q);
  for (int i = 0; i < 12; i++){
    if (d >= DEPTH * (1.0 - hh)) break;
    d += DEPTH / 12.0; q += st; hh = hf(q);
  }
  // one bisection step between the last two samples
  vec2 qm = q - st * 0.5; float hm = hf(qm);
  if (d - DEPTH / 24.0 >= DEPTH * (1.0 - hm)) { q = qm; hh = hm; d -= DEPTH / 24.0; }
  vec3 hp = vec3(q, uCut - d);
  float e = 0.0015;
  vec2 gr = vec2(hf(q + vec2(e, 0.0)) - hf(q - vec2(e, 0.0)), hf(q + vec2(0.0, e)) - hf(q - vec2(0.0, e))) / (2.0 * e);
  vec3 n = normalize(vec3(-gr * DEPTH, 1.0));
  vec3 alb = albedo(q, hh);
  float ao = mix(0.35, 1.0, hh);
  vec3 seed = SAFFRON * (lightTerm(hp, n, uSeedA, q, hh) + lightTerm(hp, n, uSeedB, q, hh));
  vec3 amb = (uAmb * 1.6 + uFaceAmb * vec3(0.012, 0.016, 0.02)) * (0.35 + 0.65 * sat(n.y * 0.5 + 0.5)) * exp(min(hp.y, 0.0) * 2.6);
  vec3 c = alb * (seed * 2.2 + amb) * ao;
  c = aerial(c, hp, 0.0045);
  gl_FragColor = vec4(mix(uVoid, c, uEnv), 1.0);
}`;

const TL_VERT = /* glsl */`
varying vec3 vW; varying vec3 vN;
void main(){ vec4 w = modelMatrix * instanceMatrix * vec4(position, 1.0); vW = w.xyz; vN = normalize(mat3(modelMatrix * instanceMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * w; }`;
const TL_FRAG = /* glsl */`
${COMMON}
${SKYLUT}
${LIGHTING}
varying vec3 vW; varying vec3 vN;
void main(){
  vec3 n = normalize(vN);
  vec3 a = mix(MOSS * 0.3, CANOPY * 0.22, vnoise(vW.xz * 0.2));
  a = mix(a, BONE * 0.5, uSnow * smoothstep(0.3, 0.8, n.y));
  vec3 c = a * (uSunCol * max(dot(n, uSunDir), 0.0) * 0.8 + uAmb * 0.8 + uMoonCol * 0.5);
  c = aerial(c, vW, 0.0045);
  gl_FragColor = vec4(mix(uVoid, c, uEnv), 1.0);
}`;

const GRASS_VERT = /* glsl */`
${COMMON}
attribute vec4 aG; // x, z, height, phase
uniform float uTime, uWind, uSnow, uSeason, uStill;
varying vec3 vW; varying float vT; varying float vR;
void main(){
  float h = abs(aG.z) * (1.0 - 0.75 * uSnow) * (aG.z < 0.0 && uCut > 100.0 ? 0.0 : 1.0);
  float t = position.y; vT = t; vR = aG.w;
  // wind: a travelling gust front plus per-blade phase (kinematic approximation)
  float gust = uStill > 0.5 ? 0.35 : 0.5 + 0.5 * sin(uTime * 1.3 - aG.x * 0.35 + aG.w * 6.0) * sin(uTime * 0.37 + aG.y * 0.2);
  float bend = uWind * (0.25 + 0.55 * gust) * t * t;
  float ang = aG.w * 6.2831;
  vec3 side = vec3(cos(ang), 0.0, sin(ang));
  vec3 p = vec3(aG.x, 0.0, aG.y) + side * position.x * 0.012 * (1.0 - t) + vec3(0.8, 0.0, -0.6) * bend * h;
  p.y = t * h * (1.0 - 0.3 * bend);
  vW = p;
  gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.0);
}`;
const GRASS_FRAG = /* glsl */`
${COMMON}
${SKYLUT}
${LIGHTING}
varying vec3 vW; varying float vT; varying float vR;
void main(){
  if (vW.z > uCut) discard;
  float ys = mod(uSeason, 4.0);
  vec3 a = mix(MOSS * 0.5, CANOPY * 0.5, vR) * (0.35 + 0.8 * vT);
  a = mix(a, mix(SAFFRON, MOSS, 0.55) * 0.45 * (0.4 + vT), smoothstep(2.1, 2.8, ys) * (1.0 - smoothstep(3.4, 3.95, ys)) * vR);
  float sh = canopyShadow(vW);
  vec3 c = a * (uSunCol * (0.35 + 0.65 * vT) * sh + uAmb * 0.9 + uMoonCol * 0.6);
  c += uSunCol * pow(sat(dot(normalize(vW - cameraPosition), uSunDir)), 6.0) * vT * 0.25 * CANOPY * sh;
  c = aerial(c, vW, 0.0045);
  gl_FragColor = vec4(mix(uVoid, c, uEnv), 1.0);
}`;

export class Land {
  constructor(shared, quality) {
    const u = (extra) => Object.assign({}, shared, {
      uCut: this.cutU, uSnow: this.snowU, uSeason: this.seasonU, uWind: this.windU,
      uCanopy: this.canopyU, uCanopyDen: this.canopyDenU,
    }, extra);
    this.cutU = { value: 0 }; this.snowU = { value: 0 }; this.seasonU = { value: 1 }; this.windU = { value: 0.3 };
    this.canopyU = { value: new THREE.Vector4(0, 4.2, 0, 4.6) }; this.canopyDenU = { value: 0 };

    // Terrain: a polar grid, dense near the tree.
    const NR = 64, NA = 112, pos = [], idx = [];
    for (let i = 0; i <= NR; i++) {
      const r = 1600 * Math.pow(i / NR, 2.4);
      for (let j = 0; j < NA; j++) {
        const a = (j / NA) * Math.PI * 2, x = Math.cos(a) * r, z = Math.sin(a) * r;
        pos.push(x, groundH(x, z), z);
      }
    }
    for (let i = 0; i < NR; i++) for (let j = 0; j < NA; j++) {
      const a = i * NA + j, b = i * NA + ((j + 1) % NA), c = a + NA, d = b + NA;
      idx.push(a, c, b, b, c, d);
    }
    const tg = new THREE.BufferGeometry();
    tg.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    tg.setIndex(idx); tg.computeVertexNormals();
    this.terrain = new THREE.Mesh(tg, new THREE.ShaderMaterial({ uniforms: u(), vertexShader: TERRAIN_VERT, fragmentShader: TERRAIN_FRAG }));
    this.terrain.frustumCulled = false;

    // Cut face: a strip whose top edge follows the terrain at z = cut.
    this.faceSeg = 200;
    const fg = new THREE.BufferGeometry();
    const fp = new Float32Array((this.faceSeg + 1) * 2 * 3), fi = [];
    for (let i = 0; i <= this.faceSeg; i++) {
      const x = -60 + (120 * i) / this.faceSeg;
      fp.set([x, 0, 0, x, -30, 0], i * 6);
      if (i < this.faceSeg) { const a = i * 2; fi.push(a, a + 1, a + 2, a + 2, a + 1, a + 3); }
    }
    fg.setAttribute('position', new THREE.BufferAttribute(fp, 3));
    fg.setIndex(fi);
    this.seedA = { value: new THREE.Vector4(0, -0.35, 0.03, 0) };
    this.seedB = { value: new THREE.Vector4(2.2, -0.33, 0.03, 0) };
    this.faceAmb = { value: 1 };
    this.face = new THREE.Mesh(fg, new THREE.ShaderMaterial({
      uniforms: u({ uSeedA: this.seedA, uSeedB: this.seedB, uFaceAmb: this.faceAmb }),
      vertexShader: FACE_VERT, fragmentShader: FACE_FRAG,
    }));
    this.face.frustumCulled = false;
    this.faceCut = null;

    // Treeline: conifer silhouettes in patches around the horizon.
    const R = rng(11), n = quality.tier === 'high' ? 900 : 450;
    const cone = new THREE.ConeGeometry(1, 1, 6, 1); cone.translate(0, 0.5, 0);
    this.treeline = new THREE.InstancedMesh(cone, new THREE.ShaderMaterial({ uniforms: u(), vertexShader: TL_VERT, fragmentShader: TL_FRAG }), n);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
    let k = 0;
    while (k < n) {
      const a = R() * Math.PI * 2, r = 70 + Math.pow(R(), 0.7) * 260;
      const x = Math.cos(a) * r, z = Math.sin(a) * r;
      if (fbm2(x * 0.02, z * 0.02) < 0.47) continue;
      const h = 6 + R() * 12;
      p.set(x, groundH(x, z) - 0.5, z); s.set(h * 0.28, h, h * 0.28);
      m.compose(p, q, s); this.treeline.setMatrixAt(k++, m);
    }
    this.treeline.frustumCulled = false;

    // Grass: single tapered blades (three segments), instanced around the tree
    // and along the soil line so the cross-section has a living edge.
    const gb = new THREE.BufferGeometry();
    const gp = [], gi = [];
    for (let i = 0; i <= 3; i++) { const t = i / 3; gp.push(-1 + t * 0.9, t, 0, 1 - t * 0.9, t, 0); }
    for (let i = 0; i < 3; i++) { const a = i * 2; gi.push(a, a + 1, a + 2, a + 2, a + 1, a + 3); }
    gb.setAttribute('position', new THREE.Float32BufferAttribute(gp, 3)); gb.setIndex(gi);
    const ng = quality.tier === 'high' ? 16000 : 7000;
    const ig = new THREE.InstancedBufferGeometry(); ig.index = gb.index; ig.attributes.position = gb.attributes.position;
    const ga = new Float32Array(ng * 4);
    for (let i = 0; i < ng; i++) {
      let x, z;
      const edge = i < ng * 0.14;
      if (edge) { x = (R() - 0.5) * 9; z = -R() * R() * 1.5 - 0.004; }
      else { const a = R() * Math.PI * 2, r = 0.4 + Math.sqrt(R()) * 16; x = Math.cos(a) * r; z = Math.sin(a) * r; }
      ga.set([x, z, (edge ? -1 : 1) * (0.05 + R() * 0.12) * (0.6 + fbm2(x * 0.6, z * 0.6)), R()], i * 4);
    }
    ig.setAttribute('aG', new THREE.InstancedBufferAttribute(ga, 4));
    ig.instanceCount = ng;
    this.grass = new THREE.Mesh(ig, new THREE.ShaderMaterial({ uniforms: u(), vertexShader: GRASS_VERT, fragmentShader: GRASS_FRAG, side: THREE.DoubleSide }));
    this.grass.frustumCulled = false;
  }

  addTo(scene) { scene.add(this.terrain, this.face, this.treeline, this.grass); }

  update(s, seedLights) {
    const cut = s.cut;
    this.cutU.value = cut;
    this.seasonU.value = s.season;
    this.windU.value = s.wind;
    const ys = ((s.season % 4) + 4) % 4;
    this.snowU.value = sstep(3.15, 3.45, ys) * (1 - sstep(3.9, 4.0, ys));
    // crown density follows the leaves' life cycle
    this.canopyDenU.value = s.treeVis * sstep(0.1, 0.9, ys) * (1 - sstep(2.4, 3.1, ys));
    const faceOn = cut < 100;
    this.face.visible = faceOn;
    if (faceOn) {
      this.face.position.z = cut;
      if (this.faceCut !== cut) {
        const a = this.face.geometry.attributes.position;
        for (let i = 0; i <= this.faceSeg; i++) a.array[i * 6 + 1] = groundH(a.array[i * 6], cut);
        a.needsUpdate = true; this.faceCut = cut;
      }
    }
    this.seedA.value.w = seedLights[0];
    this.seedB.value.w = seedLights[1];
  }
}
