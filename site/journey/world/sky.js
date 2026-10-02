// Sky: a physically based atmosphere (Rayleigh + Mie + ozone single scattering,
// raymarched into a small sky-view LUT, after Hillaire 2020) plus a dome shader
// for the sun, a phase-lit moon, a cloud layer and the aurora curtain, and stars.
import * as THREE from '../vendor/three.module.min.js';
import { COMMON, SKYLUT } from '../shaders/common.js';
import { rng } from '../core/math.js';

const LUT_W = 128, LUT_H = 96;

// ---------------------------------------------------------------- CPU atmosphere
// The same model as the LUT shader, evaluated on the CPU for the light that
// reaches the ground (sun colour) and a rough sky ambient term.
const RG = 6360, RT = 6460;
const BR = [5.802e-3, 13.558e-3, 33.1e-3], BMS = 3.996e-3, BME = 4.4e-3, BO = [0.65e-3, 1.881e-3, 0.085e-3];
function extAt(h, o) {
  const r = Math.exp(-h / 8), m = Math.exp(-h / 1.2), oz = Math.max(0, 1 - Math.abs(h - 25) / 15);
  for (let k = 0; k < 3; k++) o[k] = BR[k] * r + BME * m + BO[k] * oz;
}
const _e = [0, 0, 0];
function transmittance(h0, el, out) {
  const ro = [0, RG + h0, 0], rd = [Math.cos(el), Math.sin(el), 0];
  const b = ro[1] * rd[1], cG = ro[1] * ro[1] - RG * RG, dG = b * b - cG;
  if (dG > 0 && b < 0) { out[0] = out[1] = out[2] = 0; return out; }
  const cT = ro[1] * ro[1] - RT * RT, tMax = -b + Math.sqrt(b * b - cT);
  const N = 40, dt = tMax / N, od = [0, 0, 0];
  for (let i = 0; i < N; i++) {
    const t = (i + 0.5) * dt, x = rd[0] * t, y = ro[1] + rd[1] * t;
    extAt(Math.hypot(x, y) - RG, _e);
    od[0] += _e[0] * dt; od[1] += _e[1] * dt; od[2] += _e[2] * dt;
  }
  out[0] = Math.exp(-od[0]); out[1] = Math.exp(-od[1]); out[2] = Math.exp(-od[2]);
  return out;
}

const LUT_FRAG = /* glsl */`
${COMMON}
uniform vec3 uSun;
varying vec2 vUv;
const float RG = 6360.0, RT = 6460.0;
const vec3 BR = vec3(5.802e-3, 13.558e-3, 33.1e-3);
const float BMS = 3.996e-3, BME = 4.40e-3;
const vec3 BO = vec3(0.650e-3, 1.881e-3, 0.085e-3);
vec3 ext(float h){ return BR * exp(-h / 8.0) + BME * exp(-h / 1.2) + BO * max(0.0, 1.0 - abs(h - 25.0) / 15.0); }
float exitT(vec3 ro, vec3 rd, float R){ float b = dot(ro, rd), c = dot(ro, ro) - R * R; return -b + sqrt(max(b * b - c, 0.0)); }
float groundT(vec3 ro, vec3 rd){ float b = dot(ro, rd), c = dot(ro, ro) - RG * RG, d = b * b - c; return (d < 0.0 || b > 0.0) ? -1.0 : -b - sqrt(d); }
vec3 sunT(vec3 p, vec3 s){
  if (groundT(p, s) > 0.0) return vec3(0.0);
  float T = exitT(p, s, RT), dt = T / 6.0; vec3 od = vec3(0.0);
  for (int i = 0; i < 6; i++) od += ext(length(p + s * (float(i) + 0.5) * dt) - RG) * dt;
  return exp(-od);
}
void main(){
  float phi = vUv.x * PI, v = vUv.y * 2.0 - 1.0, el = sign(v) * v * v * 0.5 * PI;
  float sEl = asin(clamp(uSun.y, -1.0, 1.0));
  vec3 rd = vec3(cos(el) * cos(phi), sin(el), cos(el) * sin(phi));
  vec3 sd = vec3(cos(sEl), sin(sEl), 0.0);
  vec3 ro = vec3(0.0, RG + 0.3, 0.0);
  float tMax = exitT(ro, rd, RT), tg = groundT(ro, rd);
  bool hitG = tg > 0.0; if (hitG) tMax = tg;
  float mu = dot(rd, sd);
  float pR = 3.0 / (16.0 * PI) * (1.0 + mu * mu);
  const float g = 0.8;
  float pM = 3.0 / (8.0 * PI) * ((1.0 - g * g) * (1.0 + mu * mu)) / ((2.0 + g * g) * pow(1.0 + g * g - 2.0 * g * mu, 1.5));
  vec3 L = vec3(0.0), T = vec3(1.0); float t0 = 0.0;
  for (int i = 0; i < 20; i++){
    float t1 = tMax * pow((float(i) + 1.0) / 20.0, 2.0), dt = t1 - t0, tm = t0 + 0.5 * dt; t0 = t1;
    vec3 p = ro + rd * tm; float h = length(p) - RG;
    vec3 sR = BR * exp(-h / 8.0); float sM = BMS * exp(-h / 1.2);
    vec3 e = ext(h), ts = sunT(p, sd);
    // single scattering + a crude isotropic multiple-scattering term (approximation)
    vec3 S = (sR * pR + sM * pM) * ts + (sR + sM) * ts * 0.06;
    vec3 Ts = exp(-e * dt);
    L += T * S * (1.0 - Ts) / max(e, vec3(1e-7));
    T *= Ts;
  }
  if (hitG){ vec3 pg = ro + rd * tMax; L += T * sunT(pg, sd) * max(dot(normalize(pg), sd), 0.0) * 0.08 / PI; }
  gl_FragColor = vec4(L, 1.0);
}`;

const DOME_VERT = /* glsl */`
varying vec3 vDir;
void main(){ vDir = position; vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0); gl_Position = p.xyww; }`;

const DOME_FRAG = /* glsl */`
${COMMON}
${SKYLUT}
#ifndef AUR_STEPS
#define AUR_STEPS 20
#endif
varying vec3 vDir;
uniform float uTime, uEnv, uCloud, uAurora, uNight, uMoonI;
uniform vec3 uSunCol, uCloudSun, uAmb, uMoonDir, uMoonCol, uSunTrue, uVoid;
float cloudDen(vec2 p){
  float n = fbm(p * 0.2 + vec2(uTime * 0.006, uTime * 0.002));
  return sat((n - (1.02 - uCloud)) * 3.2);
}
vec4 clouds(vec3 d){
  if (d.y < 0.012) return vec4(0.0);
  float t = 2.0 / d.y; vec2 p = d.xz * t;
  float den = cloudDen(p);
  if (den < 0.002) return vec4(0.0);
  // 2.5D self-shadowing: three taps toward the sun in the layer (approximation, not a volume march)
  vec2 ls = normalize(uSunTrue.xz + vec2(1e-4));
  float od = cloudDen(p + ls * 0.5) + cloudDen(p + ls * 1.1) + cloudDen(p + ls * 1.9);
  float light = exp(-od * 1.25), mu = dot(d, uSunTrue);
  float hg = (1.0 - 0.36) / pow(1.0 + 0.36 - 1.2 * mu, 1.5) / (4.0 * PI);
  vec3 col = uCloudSun * light * (0.25 + 5.0 * hg) + uAmb * (0.55 + 0.25 * light) + uMoonCol * exp(-od * 0.7) * 0.5;
  col *= 1.0 - 0.35 * den;
  float a = den * sat((d.y - 0.012) * 9.0);
  col = mix(col, skyLut(d), sat(t / 70.0));
  return vec4(col, a);
}
vec3 aurora(vec3 d){
  if (d.y < 0.02) return vec3(0.0);
  vec3 acc = vec3(0.0);
  for (int i = 0; i < AUR_STEPS; i++){
    float fi = (float(i) + 0.5) / float(AUR_STEPS);
    float h = 1.0 + fi * 3.6, t = h / d.y;
    if (t > 40.0) break;
    vec2 p = d.xz * t;
    // the curtain: a folded sheet whose footprint wanders along x
    float w = (fbm3(vec2(p.x * 0.07 + 3.0, uTime * 0.006)) - 0.5) * 9.0 + sin(p.x * 0.21 + uTime * 0.02) * 1.6;
    float dz = p.y - (-7.0 + w);
    float band = exp(-dz * dz * 0.5);
    float rays = pow(0.35 + 0.65 * vnoise(vec2(p.x * 2.2 + w * 1.4, uTime * 0.03)), 2.0);
    float prof = exp(-fi * 2.6) * sat(fi * 16.0);
    vec3 c = mix(SPROUT * 1.2, CANOPY * 1.6 + vec3(0.0, 0.02, 0.04), sat(fi * 1.6));
    c = mix(SAFFRON * 1.3, c, smoothstep(0.02, 0.1, fi));
    acc += c * band * rays * prof * exp(-t * 0.02);
  }
  return acc * (9.0 / float(AUR_STEPS));
}
void main(){
  vec3 d = normalize(vDir);
  vec3 col = skyLut(d);
  // sun disc with limb darkening
  float cs = dot(d, uSunDir);
  float r = sqrt(max(0.0, 1.0 - cs * cs)) / 0.0085;
  if (r < 1.0 && cs > 0.0) col += uSunCol * 2600.0 * (0.4 + 0.6 * sqrt(1.0 - r * r)) * smoothstep(1.0, 0.9, r);
  // moon: a lit sphere, phase from the true sun direction
  float cm = dot(d, uMoonDir);
  if (cm > 0.999) {
    vec3 up = abs(uMoonDir.y) < 0.99 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0);
    vec3 tx = normalize(cross(up, uMoonDir)), ty = cross(uMoonDir, tx);
    vec2 q = vec2(dot(d, tx), dot(d, ty)) / 0.02;
    float r2 = dot(q, q);
    if (r2 < 1.0) {
      vec3 n = q.x * tx + q.y * ty - sqrt(1.0 - r2) * uMoonDir;
      float lam = max(dot(n, uSunTrue), 0.0);
      float maria = 0.72 + 0.28 * fbm3(q * 2.6 + 7.0);
      vec3 moon = vec3(0.95, 0.93, 0.86) * maria * (lam + 0.012);
      col = mix(col, moon * uMoonI, smoothstep(1.0, 0.93, r2));
    }
  }
  col += uMoonCol * 0.6 * exp(-(1.0 - cm) * 900.0) + uMoonCol * 0.05 * exp(-(1.0 - cm) * 40.0);
  float cloudA = 0.0;
  if (uAurora > 0.001) col += aurora(d) * uAurora * uNight;
  if (uCloud > 0.001) { vec4 c = clouds(d); col = mix(col, c.rgb, c.a); cloudA = c.a; }
  col = mix(uVoid, col, uEnv);
  gl_FragColor = vec4(col, cloudA);
}`;

const STAR_VERT = /* glsl */`
attribute vec4 aStar; // brightness, size, twinkle rate, phase
varying vec3 vCol; varying float vB;
uniform float uTime, uNight, uDpr, uStill;
void main(){
  vec3 d = normalize(position);
  vec4 p = projectionMatrix * viewMatrix * vec4(cameraPosition + d * 1500.0, 1.0);
  gl_Position = p;
  float tw = uStill > 0.5 ? 1.0 : 0.85 + 0.15 * sin(uTime * aStar.z + aStar.w);
  vB = aStar.x * tw * uNight * smoothstep(0.0, 0.18, d.y);
  vCol = color;
  gl_PointSize = aStar.y * uDpr;
}`;
const STAR_FRAG = /* glsl */`
varying vec3 vCol; varying float vB;
void main(){ if (vB < 0.002) discard; gl_FragColor = vec4(vCol * vB, 1.0); }`;

export class Sky {
  constructor(renderer, quality) {
    this.renderer = renderer;
    this.lut = new THREE.WebGLRenderTarget(LUT_W, LUT_H, { type: THREE.HalfFloatType, depthBuffer: false, magFilter: THREE.LinearFilter, minFilter: THREE.LinearFilter, wrapS: THREE.ClampToEdgeWrapping, wrapT: THREE.ClampToEdgeWrapping });
    this.lutMat = new THREE.ShaderMaterial({
      uniforms: { uSun: { value: new THREE.Vector3(0, 1, 0) } },
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
      fragmentShader: LUT_FRAG, depthTest: false, depthWrite: false,
    });
    this.lutScene = new THREE.Scene();
    const q = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.lutMat); q.frustumCulled = false;
    this.lutScene.add(q);
    this.orthoCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.lastEl = 99;

    // Shared uniforms: every lit material reads these (fog, light, sky colour).
    this.u = {
      uSkyLut: { value: this.lut.texture },
      uSunDir: { value: new THREE.Vector3(0, 1, 0) },
      uSunTrue: { value: new THREE.Vector3(0, 1, 0) },
      uSunI: { value: 9 },
      uSunCol: { value: new THREE.Vector3() },
      uCloudSun: { value: new THREE.Vector3() },
      uAmb: { value: new THREE.Vector3() },
      uNightSky: { value: new THREE.Vector3() },
      uMoonDir: { value: new THREE.Vector3(0, 1, 0) },
      uMoonCol: { value: new THREE.Vector3() },
      uMoonI: { value: 0 },
      uTime: { value: 0 },
      uEnv: { value: 1 },
      uVoid: { value: new THREE.Vector3() },
      uCloud: { value: 0.3 },
      uAurora: { value: 0 },
      uNight: { value: 0 },
      uDpr: { value: 1 },
      uStill: { value: 0 },
    };
    const domeMat = new THREE.ShaderMaterial({
      uniforms: this.u, vertexShader: DOME_VERT, fragmentShader: DOME_FRAG,
      defines: { AUR_STEPS: quality.tier === 'high' ? 22 : 12 },
      side: THREE.BackSide, depthTest: false, depthWrite: false,
    });
    this.dome = new THREE.Mesh(new THREE.SphereGeometry(2000, 48, 24), domeMat);
    this.dome.renderOrder = -100; this.dome.frustumCulled = false;

    // Stars: crisp square points. Blending uses (1 - destination alpha) so the
    // cloud layer (which writes its coverage into alpha) hides them.
    const n = quality.tier === 'high' ? 5200 : 2600, R = rng(77);
    const pos = new Float32Array(n * 3), col = new Float32Array(n * 3), st = new Float32Array(n * 4);
    const tints = [[0.85, 0.9, 1.0], [0.95, 0.93, 0.88], [0.72, 0.76, 0.73], [0.8, 0.95, 0.85]];
    for (let i = 0; i < n; i++) {
      const z = R() * 2 - 1, a = R() * Math.PI * 2, s = Math.sqrt(1 - z * z);
      pos.set([s * Math.cos(a), z, s * Math.sin(a)], i * 3);
      const m = Math.pow(R(), 5);
      const t = tints[(R() * tints.length) | 0];
      col.set(t, i * 3);
      st.set([0.04 + m * 1.6, m > 0.35 ? 2 : 1, 0.6 + R() * 1.4, R() * 6.28], i * 4);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    g.setAttribute('aStar', new THREE.BufferAttribute(st, 4));
    const starMat = new THREE.ShaderMaterial({
      uniforms: this.u, vertexShader: STAR_VERT, fragmentShader: STAR_FRAG, vertexColors: true,
      transparent: true, depthWrite: false, blending: THREE.CustomBlending,
      blendSrc: THREE.OneMinusDstAlphaFactor, blendDst: THREE.OneFactor,
    });
    this.stars = new THREE.Points(g, starMat);
    this.stars.frustumCulled = false; this.stars.renderOrder = -90;
    this._t = [0, 0, 0];
  }

  addTo(scene) { scene.add(this.dome); scene.add(this.stars); }

  update(s, camera, time) {
    const u = this.u, el = s.sunEl, az = s.sunAz;
    const dir = (e, a, v) => v.set(Math.cos(e) * Math.sin(a), Math.sin(e), -Math.cos(e) * Math.cos(a));
    dir(el, az, u.uSunTrue.value);
    // The LUT sun: clamp just under the horizon so twilight keeps its colour.
    dir(Math.max(el, -0.3), az, u.uSunDir.value);
    dir(s.moonEl, s.moonAz, u.uMoonDir.value);
    const t = this._t;
    transmittance(0.3, el, t);
    const sunI = 1.6 * Math.max(0, Math.sin(el + 0.02)) ** 0.35;
    u.uSunCol.value.set(t[0] * sunI, t[1] * sunI, t[2] * sunI);
    transmittance(3.0, el, t);
    const ci = 1.3 * (el > -0.07 ? 1 : 0);
    u.uCloudSun.value.set(t[0] * ci, t[1] * ci, t[2] * ci);
    // Ambient: a fitted stand-in for integrated sky irradiance (approximation).
    const day = Math.max(0, Math.sin(el + 0.1));
    const night = s.night, moonUp = Math.max(0, Math.sin(s.moonEl));
    u.uAmb.value.set(0.030 * day + 0.003, 0.046 * day + 0.005, 0.052 * day + 0.007);
    u.uNightSky.value.set(0.0011, 0.0024, 0.0034).multiplyScalar(0.4 + 0.6 * night);
    u.uMoonCol.value.set(0.020, 0.026, 0.034).multiplyScalar(night * moonUp);
    u.uMoonI.value = 0.35 * (0.4 + 0.6 * night);
    u.uNight.value = night;
    u.uAurora.value = s.aurora;
    u.uCloud.value = s.clouds;
    u.uEnv.value = s.env;
    u.uTime.value = time;
    this.dome.position.copy(camera.position);
    if (Math.abs(el - this.lastEl) > 0.0004 || this.dirty) {
      this.lutMat.uniforms.uSun.value.copy(u.uSunDir.value);
      const r = this.renderer, prev = r.getRenderTarget();
      r.setRenderTarget(this.lut); r.render(this.lutScene, this.orthoCam); r.setRenderTarget(prev);
      this.lastEl = el; this.dirty = false;
    }
  }
}
