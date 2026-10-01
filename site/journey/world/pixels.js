// Pixels and glows.
// Pixels: crisp squares snapped to the device-pixel grid and drawn after tone
// mapping, so brand colours land exactly (the seed is exactly Saffron, the mark
// exactly Bone). Glows: additive soft sprites in the HDR scene (light, not ink).
import * as THREE from '../vendor/three.module.min.js';
import { srgb, lin, HEX } from '../core/palette.js';

export const MARK_PATH = 'M3 0h2v1h-2zM6 0h2v1h-2zM5 1h1v1h-1zM5 2h1v1h-1zM0 3h5v1h-5zM6 3h5v1h-5zM0 4h5v1h-5zM7 4h4v1h-4zM0 5h4v1h-4zM5 5h2v1h-2zM8 5h3v1h-3zM0 6h3v1h-3zM4 6h4v1h-4zM9 6h2v1h-2zM0 7h3v1h-3zM4 7h7v1h-7zM0 8h2v1h-2zM3 8h8v1h-8zM0 9h11v1h-11z';
// The mark as whole pixels: [col, row] with row 0 at the top.
export const MARK_PIXELS = (() => {
  const out = [];
  for (const m of MARK_PATH.matchAll(/M(\d+) (\d+)h(\d+)/g)) {
    const x = +m[1], y = +m[2], w = +m[3];
    for (let i = 0; i < w; i++) out.push([x + i, y]);
  }
  return out;
})();
export const MARK_ROWS = (() => {
  const rows = new Array(10).fill(0);
  for (const [c, r] of MARK_PIXELS) rows[r] |= 1 << c;
  return rows;
})();

// Mark rectangle in device pixels: whole-pixel size, centred.
export function markRect(W, H) {
  const ps = Math.max(2, Math.round(Math.min(W, H) * 0.3 / 11));
  return [Math.round(W / 2 - 5.5 * ps), Math.round(H / 2 - 5 * ps), ps];
}

const PIX_VERT = /* glsl */`
uniform vec2 uRes; uniform float uAlpha, uReveal, uMorph, uGlobalScale;
uniform vec3 uMark; // left, bottom, pixel size (device px)
uniform mat4 uModel;
attribute vec3 aPos; attribute vec3 aCol; attribute vec4 aP; // size, alpha, order, mode
attribute vec2 aScr; attribute vec2 aWH;
#ifdef BONES
uniform sampler2D uBones; attribute float aBone;
#endif
varying vec3 vCol; varying float vA;
void main(){
  vec3 wp = (uModel * vec4(aPos, 1.0)).xyz;
#ifdef BONES
  if (aBone >= 0.0) {
    int i = int(aBone);
    mat4 M = mat4(texelFetch(uBones, ivec2(0, i), 0), texelFetch(uBones, ivec2(1, i), 0), texelFetch(uBones, ivec2(2, i), 0), texelFetch(uBones, ivec2(3, i), 0));
    wp = (M * vec4(0.0, texelFetch(uBones, ivec2(4, i), 0).x, 0.0, 1.0)).xyz;
  }
#endif
  vec4 clip = projectionMatrix * viewMatrix * vec4(wp, 1.0);
  vec2 px = (clip.xy / max(clip.w, 1e-5) * 0.5 + 0.5) * uRes;
  float size = aP.x * uGlobalScale;
  if (aP.w > 0.5 && aP.w < 1.5) size = aP.x * projectionMatrix[1][1] * 0.5 * uRes.y / max(clip.w, 1e-5);
  float vis = clip.w > 0.0 ? 1.0 : 0.0;
#ifdef MARK
  float m = smoothstep(aP.z * 0.55, aP.z * 0.55 + 0.45, uMorph);
  vec2 mp = uMark.xy + vec2(aScr.x, 9.0 - aScr.y) * uMark.z + 0.5 * uMark.z;
  px = mix(mp, px, m); size = mix(uMark.z, size, m);
  vis = m < 0.5 ? 1.0 : vis;
  float reveal = 1.0;
#else
  float reveal = step(aP.z, uReveal);
#endif
  vec2 s = max(vec2(1.0), floor(size * aWH + 0.5));
  vec2 bl = floor(px - s * 0.5 + 0.5);
  gl_Position = vec4((bl + position.xy * s) / uRes * 2.0 - 1.0, 0.0, 1.0);
  vA = uAlpha * aP.y * reveal * vis;
  vCol = aCol;
}`;
const PIX_FRAG = /* glsl */`
varying vec3 vCol; varying float vA;
void main(){ if (vA < 0.004) discard; gl_FragColor = vec4(vCol, vA); }`;

const quad = () => {
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0], 3));
  g.setIndex([0, 1, 2, 2, 1, 3]);
  return g;
};

// A group of crisp pixels. Attributes are typed arrays the owner may rewrite.
export class Pixels {
  constructor(n, { bones = null, mark = false } = {}) {
    this.n = n;
    const g = quad();
    this.pos = new Float32Array(n * 3); this.col = new Float32Array(n * 3);
    this.p = new Float32Array(n * 4); this.scr = new Float32Array(n * 2); this.wh = new Float32Array(n * 2).fill(1);
    this.attr = {
      aPos: new THREE.InstancedBufferAttribute(this.pos, 3), aCol: new THREE.InstancedBufferAttribute(this.col, 3),
      aP: new THREE.InstancedBufferAttribute(this.p, 4), aScr: new THREE.InstancedBufferAttribute(this.scr, 2),
      aWH: new THREE.InstancedBufferAttribute(this.wh, 2),
    };
    for (const k in this.attr) g.setAttribute(k, this.attr[k]);
    if (bones) { this.bone = new Float32Array(n).fill(-1); this.attr.aBone = new THREE.InstancedBufferAttribute(this.bone, 1); g.setAttribute('aBone', this.attr.aBone); }
    g.instanceCount = n;
    this.u = {
      uRes: { value: new THREE.Vector2(1, 1) }, uAlpha: { value: 1 }, uReveal: { value: 1 }, uMorph: { value: 0 },
      uGlobalScale: { value: 1 }, uMark: { value: new THREE.Vector3(0, 0, 4) }, uModel: { value: new THREE.Matrix4() },
    };
    if (bones) this.u.uBones = { value: bones };
    const defines = {}; if (bones) defines.BONES = 1; if (mark) defines.MARK = 1;
    this.mesh = new THREE.Mesh(g, new THREE.ShaderMaterial({
      uniforms: this.u, defines, vertexShader: PIX_VERT, fragmentShader: PIX_FRAG,
      transparent: true, depthTest: false, depthWrite: false,
    }));
    this.mesh.frustumCulled = false;
  }
  set(i, pos, hex, size, alpha = 1, order = 0, mode = 0) {
    this.pos.set(pos, i * 3); this.col.set(srgb(hex), i * 3); this.p.set([size, alpha, order, mode], i * 4);
  }
  dirty(...names) { for (const k of names.length ? names : Object.keys(this.attr)) this.attr[k].needsUpdate = true; }
}

const GLOW_VERT = /* glsl */`
uniform float uAlpha, uReveal, uTime;
uniform mat4 uModel;
attribute vec3 aPos; attribute vec3 aCol; attribute vec4 aP; // size (world), alpha, order, twinkle
#ifdef BONES
uniform sampler2D uBones; attribute float aBone;
#endif
varying vec3 vCol; varying vec2 vUv;
void main(){
  vec3 wp = (uModel * vec4(aPos, 1.0)).xyz;
#ifdef BONES
  if (aBone >= 0.0) {
    int i = int(aBone);
    mat4 M = mat4(texelFetch(uBones, ivec2(0, i), 0), texelFetch(uBones, ivec2(1, i), 0), texelFetch(uBones, ivec2(2, i), 0), texelFetch(uBones, ivec2(3, i), 0));
    wp = (M * vec4(0.0, texelFetch(uBones, ivec2(4, i), 0).x, 0.0, 1.0)).xyz;
  }
#endif
  vec4 v = viewMatrix * vec4(wp, 1.0);
  v.xy += (position.xy * 2.0 - 1.0) * aP.x;
  gl_Position = projectionMatrix * v;
  float tw = 1.0 + aP.w * 0.25 * sin(uTime * (0.7 + aP.z * 3.0) + aP.z * 40.0);
  vCol = aCol * uAlpha * aP.y * step(aP.z, uReveal) * tw;
  vUv = position.xy * 2.0 - 1.0;
}`;
const GLOW_FRAG = /* glsl */`
varying vec3 vCol; varying vec2 vUv;
void main(){
  float r2 = dot(vUv, vUv);
  if (r2 > 1.0) discard;
  float g = exp(-r2 * 7.0) * 0.8 + 0.2 * (1.0 - r2) * (1.0 - r2);
  gl_FragColor = vec4(vCol * g, 1.0);
}`;

export class Glows {
  constructor(n, { bones = null } = {}) {
    this.n = n;
    const g = quad();
    this.pos = new Float32Array(n * 3); this.col = new Float32Array(n * 3); this.p = new Float32Array(n * 4);
    this.attr = { aPos: new THREE.InstancedBufferAttribute(this.pos, 3), aCol: new THREE.InstancedBufferAttribute(this.col, 3), aP: new THREE.InstancedBufferAttribute(this.p, 4) };
    for (const k in this.attr) g.setAttribute(k, this.attr[k]);
    if (bones) { this.bone = new Float32Array(n).fill(-1); this.attr.aBone = new THREE.InstancedBufferAttribute(this.bone, 1); g.setAttribute('aBone', this.attr.aBone); }
    g.instanceCount = n;
    this.u = { uAlpha: { value: 1 }, uReveal: { value: 1 }, uTime: { value: 0 }, uModel: { value: new THREE.Matrix4() } };
    if (bones) this.u.uBones = { value: bones };
    this.mesh = new THREE.Mesh(g, new THREE.ShaderMaterial({
      uniforms: this.u, defines: bones ? { BONES: 1 } : {}, vertexShader: GLOW_VERT, fragmentShader: GLOW_FRAG,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    this.mesh.frustumCulled = false; this.mesh.renderOrder = 10;
  }
  set(i, pos, hex, intensity, size, order = 0, twinkle = 0) {
    this.pos.set(pos, i * 3);
    const c = lin(hex); this.col.set([c[0] * intensity, c[1] * intensity, c[2] * intensity], i * 3);
    this.p.set([size, 1, order, twinkle], i * 4);
  }
  dirty() { for (const k in this.attr) this.attr[k].needsUpdate = true; }
}

export { HEX };
