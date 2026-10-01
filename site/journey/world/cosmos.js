// The ancestral plane. A golden-angle (phyllotaxis) spiral with one pixel per
// real commit to the Brain when window.BODHI_ANCESTRY is present (first commit at
// the centre, newest at the rim, coloured by kind, the newest in Saffron); behind
// it a faint 123,278-point disc echoing the size of the memory graph; around it
// thirteen small constellations. The page's replay slider, if present, drives it.
import * as THREE from '../vendor/three.module.min.js';
import { Pixels, Glows, HEX } from './pixels.js';
import { rng, v3 } from '../core/math.js';

const GOLDEN = Math.PI * (3 - Math.sqrt(5));
export const CENTER = [0, 112, -82];
const MEMORY_NODES = 123278;

const FIELD_VERT = /* glsl */`
attribute vec4 aF; // brightness, hue, phase, unused
uniform float uAlpha, uDpr, uTime, uStill;
uniform mat4 uModel;
varying vec3 vC;
const vec3 A = vec3(0.30, 0.36, 0.32), Bc = vec3(0.26, 0.60, 0.26), Cc = vec3(0.9, 0.86, 0.78);
void main(){
  vec4 w = uModel * vec4(position, 1.0);
  gl_Position = projectionMatrix * viewMatrix * w;
  vec3 c = aF.y < 0.6 ? A : aF.y < 0.9 ? Bc : Cc;
  float tw = uStill > 0.5 ? 1.0 : 0.8 + 0.2 * sin(uTime * 0.6 + aF.z);
  vC = c * aF.x * uAlpha * tw;
  gl_PointSize = uDpr;
}`;
const FIELD_FRAG = /* glsl */`varying vec3 vC; void main(){ gl_FragColor = vec4(vC, 1.0); }`;

const LINE_VERT = /* glsl */`
uniform mat4 uModel; uniform float uAlpha;
varying float vA;
void main(){ vA = uAlpha; gl_Position = projectionMatrix * viewMatrix * uModel * vec4(position, 1.0); }`;
const LINE_FRAG = /* glsl */`varying float vA; void main(){ gl_FragColor = vec4(vec3(0.05, 0.07, 0.065) * vA, 1.0); }`;

export class Cosmos {
  constructor(quality) {
    const data = window.BODHI_ANCESTRY;
    const kinds = data && typeof data.kinds === 'string' && data.kinds.length ? data.kinds : null;
    const n = kinds ? kinds.length : 987;
    this.n = n;
    this.days = data && Array.isArray(data.days) ? data.days : null;
    const C = CENTER;
    // plane faces the camera path that rises from the tree
    const N = v3.norm([0, -0.55, 0.84]);
    const U = v3.norm(v3.cross([0, 1, 0], N)), V = v3.cross(N, U);
    this.basis = { N, U, V };
    const R = 24, R0 = rng(5);
    const colors = { b: HEX.sprout, f: HEX.clay, w: HEX.bone, o: HEX.lichen, a: HEX.moss };
    this.px = new Pixels(n + 13 * 7);
    this.glow = new Glows(n);
    const local = (x, y, z = 0) => [x, y, z];
    for (let i = 0; i < n; i++) {
      const r = R * Math.sqrt((i + 0.5) / n), a = i * GOLDEN;
      const p = local(Math.cos(a) * r, Math.sin(a) * r, (R0() - 0.5) * 0.4);
      const k = kinds ? kinds[i] : 'o';
      const last = i === n - 1, first = i === 0;
      const hex = last ? HEX.saffron : colors[k] || HEX.lichen;
      const size = first ? 5 : last ? 4 : k === 'a' || k === 'o' ? 2 : 3;
      this.px.set(i, p, hex, size, k === 'a' ? 0.8 : 1, i / n, 0);
      this.glow.set(i, p, last ? HEX.saffron : first ? HEX.bone : hex, first || last ? 0.5 : k === 'a' ? 0.02 : 0.07, first || last ? 1.4 : 0.55, i / n, 1);
    }
    // thirteen small constellations around the spiral
    const lines = [];
    for (let c = 0; c < 13; c++) {
      const a = c * (2 * Math.PI / 13) + 0.2, rr = R * (1.35 + 0.25 * R0());
      let px = Math.cos(a) * rr, py = Math.sin(a) * rr;
      let prev = null;
      for (let s = 0; s < 7; s++) {
        const p = local(px, py, (R0() - 0.5) * 2);
        this.px.set(n + c * 7 + s, p, s === 0 ? HEX.sage : HEX.lichen, s === 0 ? 3 : 2, 0.9, 0, 0);
        if (prev) lines.push(...prev, ...p);
        prev = p;
        const t = a + (R0() - 0.5) * 2.2;
        px += Math.cos(t) * 2.2; py += Math.sin(t) * 2.2;
      }
    }
    this.px.dirty(); this.glow.dirty();
    const lg = new THREE.BufferGeometry(); lg.setAttribute('position', new THREE.Float32BufferAttribute(lines, 3));
    this.lu = { uModel: { value: new THREE.Matrix4() }, uAlpha: { value: 0 } };
    this.lines = new THREE.LineSegments(lg, new THREE.ShaderMaterial({ uniforms: this.lu, vertexShader: LINE_VERT, fragmentShader: LINE_FRAG, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    this.lines.frustumCulled = false;

    // the memory field: 123,278 points on a golden-angle disc, far behind, twisted into arms
    const M = quality.tier === 'high' ? MEMORY_NODES : Math.round(MEMORY_NODES / 2);
    const fp = new Float32Array(M * 3), fa = new Float32Array(M * 4), R2 = rng(123278);
    const FR = 210;
    for (let i = 0; i < M; i++) {
      const t = (i + 0.5) / M, r = FR * Math.sqrt(t), a = i * GOLDEN + r * 0.018;
      const th = (R2() - 0.5) * (1 - t) * 18;
      fp.set([Math.cos(a) * r, Math.sin(a) * r, th - 150], i * 3);
      fa.set([(0.012 + Math.pow(R2(), 6) * 0.35) * (1.15 - t), R2(), R2() * 6.28, 0], i * 4);
    }
    const fg = new THREE.BufferGeometry();
    fg.setAttribute('position', new THREE.BufferAttribute(fp, 3));
    fg.setAttribute('aF', new THREE.BufferAttribute(fa, 4));
    this.fu = { uAlpha: { value: 0 }, uDpr: { value: 1 }, uTime: { value: 0 }, uStill: { value: 0 }, uModel: { value: new THREE.Matrix4() } };
    this.field = new THREE.Points(fg, new THREE.ShaderMaterial({ uniforms: this.fu, vertexShader: FIELD_VERT, fragmentShader: FIELD_FRAG, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    this.field.frustumCulled = false; this.field.renderOrder = -80;

    this.model = new THREE.Matrix4(); this.fieldModel = new THREE.Matrix4();
    this.base = new THREE.Matrix4().makeBasis(new THREE.Vector3(...U), new THREE.Vector3(...V), new THREE.Vector3(...N)).setPosition(...C);
    this.rot = new THREE.Matrix4();
    this.slider = null; this.sliderReveal = -1;
    this.hookSlider();
  }

  hookSlider() {
    const el = document.querySelector('[data-plane-range]');
    if (!el || !this.days) return;
    const cum = [];
    let acc = 0;
    const sorted = this.days.slice().sort((a, b) => a[0] - b[0]);
    for (const [d, c] of sorted) { acc += c; cum.push([d, acc]); }
    el.addEventListener('input', () => {
      const day = +el.value; let count = 0;
      for (const [d, c] of cum) if (d <= day) count = c;
      this.sliderReveal = count / this.n;
      if (this.onChange) this.onChange();
    });
  }

  addTo(scene, overlay) { scene.add(this.field, this.lines, this.glow.mesh); overlay.add(this.px.mesh); }

  update(s, time, res, dpr, still) {
    const a = s.cosmos;
    const on = a > 0.002;
    this.field.visible = this.lines.visible = this.glow.mesh.visible = this.px.mesh.visible = on;
    if (!on) return;
    const spin = still ? 0.6 : 0.6 + time * 0.012;
    this.rot.makeRotationZ(spin);
    this.model.multiplyMatrices(this.base, this.rot);
    this.fieldModel.multiplyMatrices(this.base, this.rot.makeRotationZ(spin * 0.4 + 1.0));
    const reveal = this.sliderReveal >= 0 ? this.sliderReveal : s.spiral;
    this.px.u.uModel.value.copy(this.model); this.px.u.uAlpha.value = a; this.px.u.uRes.value.copy(res);
    this.px.u.uReveal.value = reveal * 1.0001;
    this.glow.u.uModel.value.copy(this.model); this.glow.u.uAlpha.value = a; this.glow.u.uReveal.value = reveal * 1.0001; this.glow.u.uTime.value = still ? 0 : time;
    this.lu.uModel.value.copy(this.model); this.lu.uAlpha.value = a * Math.min(1, reveal * 1.5);
    this.fu.uModel.value.copy(this.fieldModel); this.fu.uAlpha.value = a; this.fu.uDpr.value = dpr; this.fu.uTime.value = time; this.fu.uStill.value = still ? 1 : 0;
  }
}
