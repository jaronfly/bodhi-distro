// Post: composites the HDR scene with the micro layer (the cell dive), then
// tone maps, grades toward the palette, adds grain, and applies the calm band.
//
// The micro layer is a continuous log-scale zoom into one leaf. Each scale is its
// own layer anchored at the focus point (so float precision holds at 1000x), and
// layers crossfade by their on-screen feature size:
//   venation (midrib, secondary, then two Voronoi vein networks)
//   -> cells (Voronoi membranes, cytoplasm drift, chloroplasts circling = cyclosis)
//   -> one cell whose wall band becomes quilted padding (the padded cell)
//   -> its nucleus, sampled into an 11x10 pixel grid, resolving into the mark.
import * as THREE from '../vendor/three.module.min.js';
import { COMMON } from '../shaders/common.js';
import { MARK_ROWS } from './pixels.js';

const FRAG = /* glsl */`
${COMMON}
uniform sampler2D uScene;
uniform vec2 uRes;
uniform float uExposure, uGrain, uCalm, uFade, uSeed, uMicro, uZoom, uPad, uPix, uMarkT, uMT, uNuc;
uniform vec3 uMark;
uniform vec2 uFocus;
const int MARK[10] = int[10](${MARK_ROWS.join(', ')});
float sdBox(vec2 p, vec2 b, float r){ vec2 q = abs(p) - b + r; return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r; }

vec3 micro(vec2 fc){
  vec2 sp = (fc - 0.5 * uRes) / (0.5 * uRes.y);
  float H = 0.08 * pow(10.0, -uZoom);
  vec2 d = sp * H;
  float px = H / (0.5 * uRes.y);
  float z = uZoom;
  // ---------------- leaf: midrib and secondary veins (absolute leaf coordinates)
  vec2 P = uFocus + d;
  float ay = abs(P.y);
  float mid = 1.0 - smoothstep(0.006, 0.006 + px * 1.5, ay);
  float phi = P.x - ay * 0.95 - ay * ay * 1.6;
  float k = phi / 0.075, dv = abs(k - floor(k + 0.5)) * 0.075 / (1.0 + 3.0 * ay);
  float sw = 0.0022;
  float sec = (1.0 - smoothstep(sw, sw + px * 1.5, dv)) * smoothstep(0.02, 0.05, ay);
  // ---------------- tertiary / quaternary veins, anchored at the focus
  vec2 s0 = 0.1 + 0.8 * h22(ivec2(0));
  ivec2 i3; vec4 v3 = voronoi(d / 0.02 + s0, i3);
  float ter = 1.0 - smoothstep(0.04, 0.04 + px / 0.02 * 1.5, v3.y);
  ivec2 i4; vec4 v4 = voronoi(d / 0.005 + s0.yx, i4);
  float qua = 1.0 - smoothstep(0.035, 0.035 + px / 0.005 * 1.5, v4.y);
  float veins = max(max(mid, sec * 0.9), max(ter * 0.7 * (1.0 - smoothstep(1.4, 1.9, z)), qua * 0.5 * (1.0 - smoothstep(1.8, 2.2, z))));
  // ---------------- cells
  const float C = 0.0011;
  ivec2 ic; vec4 vc = voronoi(d / C + s0, ic);
  float cpx = px / C;
  vec2 rel = -vc.zw;
  float rr = vc.x / max(vc.x + vc.y, 1e-4);
  float wall = 1.0 - smoothstep(0.006, 0.006 + cpx * 1.5, vc.y);
  float wglow = exp(-vc.y * 26.0);
  float memb = 1.0 - smoothstep(0.004, 0.004 + cpx * 1.5, abs(vc.y - 0.035));
  float t = uMT;
  float cyto = fbm3(rel * 6.0 + vec2(h21(ic) * 17.0) + vec2(t * 0.03, -t * 0.02));
  bool focusCell = ic == ivec2(0);
  // chloroplasts circulating around the cell (cyclosis), two staggered rings
  float dir = h21(ic + ivec2(9, 1)) > 0.5 ? 1.0 : -1.0;
  float cr = vc.x + vc.y;
  float chl = 0.0; vec2 lcs = vec2(0.0);
  for (int ring = 0; ring < 2; ring++){
    float fr = float(ring);
    float ang = atan(rel.y, rel.x) - dir * t * (0.05 + 0.04 * h21(ic + ivec2(2, 7))) * (1.0 - 0.3 * fr) + fr * 0.4;
    float nch = 15.0 + floor(h21(ic + ivec2(3, 3 + ring)) * 6.0) - fr * 5.0, sector = 6.2831853 / nch;
    float da = ang - floor(ang / sector + 0.5) * sector;
    float r0 = mix(0.74, 0.54, fr);
    vec2 lc = vec2(da * r0 * cr, vc.x - r0 * cr);
    float c1 = 1.0 - smoothstep(0.03, 0.03 + cpx * 1.5, length(lc * vec2(0.8, 1.45)));
    if (c1 > chl) { chl = c1; lcs = lc; }
  }
  if (focusCell) chl *= 1.0 - uPad;
  float nucR = 0.09;
  float nuc = 1.0 - smoothstep(nucR, nucR + cpx * 1.5, vc.x);
  // lit leaf (reflected light) vs dark-field (the microscope)
  float cushion = 1.0 - rr * rr;
  vec3 leaf = mix(CANOPY * 0.22, CANOPY * 0.42, cushion) * (0.85 + 0.3 * vnoise(d / C * 3.0));
  leaf = mix(leaf, mix(CANOPY, SPROUT, 0.55) * 0.55, veins * 0.85);
  vec3 dark = UNDER * 0.07 + CANOPY * 0.04 * cyto;
  dark += SPROUT * (0.3 * wall + 0.05 * wglow) + SAGE * 0.05 * memb;
  float grana = vnoise(lcs * 900.0);
  dark = mix(dark, mix(CANOPY * 0.55, SPROUT * 0.42, grana * 0.7), chl * 0.9);
  dark = mix(dark, SAGE * 0.07 + SPROUT * 0.03 * cyto, nuc * (focusCell ? 0.0 : 1.0));
  dark += SPROUT * 0.16 * veins * (1.0 - smoothstep(1.6, 2.1, z));
  float df = smoothstep(0.9, 1.7, z);
  vec3 col = mix(leaf, dark, df);
  // ---------------- the padded cell
  if (focusCell && uPad > 0.001) {
    float room = sdBox(rel, vec2(mix(0.05, 0.25, uPad)), 0.05);
    float inRoom = 1.0 - smoothstep(-cpx, cpx, room);
    float band = (1.0 - inRoom) * smoothstep(0.012, 0.03, vc.y);
    vec2 w = rel / 0.07, r45 = vec2(w.x + w.y, w.x - w.y) * 0.7071, f = fract(r45) - 0.5;
    float cush = (1.0 - 4.0 * f.x * f.x) * (1.0 - 4.0 * f.y * f.y);
    vec2 g = vec2(-8.0 * f.x * (1.0 - 4.0 * f.y * f.y), -8.0 * f.y * (1.0 - 4.0 * f.x * f.x));
    g = vec2(g.x + g.y, g.x - g.y) * 0.7071;
    vec3 nn = normalize(vec3(-g * 0.35, 1.0));
    float light = 0.35 + 0.65 * max(dot(nn, normalize(vec3(-0.4, 0.55, 0.75))), 0.0);
    float btn = 1.0 - smoothstep(0.06, 0.1, length(0.5 - abs(f)));
    vec3 pad = mix(LICHEN * 0.05, SAGE * 0.14, cush) * light * (1.0 - 0.7 * btn);
    // a soft shadow where the padding meets the floor
    float lip = exp(-max(room, 0.0) * 60.0) * (1.0 - inRoom);
    col = mix(col, pad * (1.0 - 0.5 * lip), band * uPad);
    col = mix(col, UNDER * 0.045 + CANOPY * 0.015 * cyto, inRoom * uPad * (1.0 - nuc));
    // nucleus: dim while the cell is a room, then it draws the eye
    float chrom = fbm(rel * 38.0 + 2.0);
    vec3 nc = mix(SAGE * 0.06, SAGE * 0.5 + SPROUT * 0.1, smoothstep(0.35, 0.75, chrom));
    col = mix(col, nc * mix(0.14, 1.3, uNuc), nuc * max(uPad, uNuc));
    col += SPROUT * 0.06 * uNuc * exp(-vc.x * vc.x / (nucR * nucR) * 0.6);
  }
  return col;
}

void main(){
  vec2 fc = gl_FragCoord.xy, uv = fc / uRes;
  vec3 hdr = texture2D(uScene, uv).rgb;
  // pixel grid of the mark
  vec2 mq = (fc - uMark.xy) / uMark.z;
  ivec2 cell = ivec2(floor(mq));
  bool inRect = mq.x >= 0.0 && mq.y >= 0.0 && cell.x < 11 && cell.y < 10;
  if (uMicro > 0.001) {
    vec2 fe = fc;
    if (inRect && uPix > 0.0) fe = mix(fc, uMark.xy + (vec2(cell) + 0.5) * uMark.z, uPix);
    hdr = mix(hdr, micro(fe), uMicro);
  }
  vec3 c = aces(hdr * uExposure);
  c = toSrgb(c);
  // grade: sit everything on a Soil-tinted floor instead of black
  c = SOIL_S * 0.5 + c * (1.0 - SOIL_S * 0.5);
  float band = smoothstep(0.06, 0.3, uv.y) * smoothstep(0.94, 0.7, uv.y);
  c = mix(c, SOIL_S + (c - SOIL_S) * 0.35, uCalm * band);
  vec2 q = (uv - 0.5) * vec2(uRes.x / uRes.y, 1.0);
  c *= 1.0 - 0.28 * dot(q, q);
  float gr = h21(ivec2(fc) + ivec2(int(uSeed) * 7919, int(uSeed) * 104729)) - 0.5;
  c += gr * uGrain * 0.045 * (1.0 - 0.7 * c);
  // exact brand pixels at the end of the dive
  if (uMicro > 0.001 && uPix > 0.0) {
    if (inRect) {
      float lum = dot(c, vec3(0.3, 0.55, 0.15));
      float on = step(0.2, lum);
      float bit = float((MARK[9 - cell.y] >> cell.x) & 1);
      float res = step(h21(cell + ivec2(5, 11)), uMarkT * 1.05 - 0.02);
      vec3 bin = mix(SOIL_S, BONE_S, mix(on, bit, res));
      c = mix(c, bin, smoothstep(0.6, 1.0, uPix) * uMicro);
    } else c = mix(c, SOIL_S, uMarkT * uMicro);
  }
  gl_FragColor = vec4(c * uFade, 1.0);
}`;

export class Post {
  constructor() {
    this.u = {
      uScene: { value: null }, uRes: { value: new THREE.Vector2(1, 1) }, uExposure: { value: 1 }, uGrain: { value: 0.6 },
      uCalm: { value: 0 }, uFade: { value: 1 }, uSeed: { value: 0 }, uMicro: { value: 0 }, uZoom: { value: 0 },
      uPad: { value: 0 }, uPix: { value: 0 }, uMarkT: { value: 0 }, uMT: { value: 0 }, uNuc: { value: 0 },
      uMark: { value: new THREE.Vector3(0, 0, 4) }, uFocus: { value: new THREE.Vector2(0.55, 0.12) },
    };
    this.mat = new THREE.ShaderMaterial({
      uniforms: this.u, fragmentShader: FRAG,
      vertexShader: 'void main(){ gl_Position = vec4(position.xy, 0.0, 1.0); }',
      depthTest: false, depthWrite: false,
    });
    this.scene = new THREE.Scene();
    const m = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.mat); m.frustumCulled = false;
    this.scene.add(m);
    this.cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  }
}

// The same tone curve on the CPU, to find the HDR value that lands on a brand colour.
const acesF = (x) => Math.min(1, Math.max(0, (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)));
const srgbF = (c) => (c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 1 / 2.4) - 0.055);
export function inverseTone(target, floor, exposure) {
  // solve floor*0.5 + s*(1 - floor*0.5) = target for s, then invert the curve
  const s = (target - floor * 0.5) / (1 - floor * 0.5);
  if (s <= 0) return 0;
  let lo = 0, hi = 16;
  for (let i = 0; i < 40; i++) { const m = (lo + hi) / 2; if (srgbF(acesF(m)) < s) lo = m; else hi = m; }
  return lo / exposure;
}
