// To be: the pixels of the mark become nodes, and the nodes become the tree
// seen as a graph (every bone tip a node, every bone an edge, the roots too).
// Tree nodes read the live bone texture, so the graph sways with the tree.
import * as THREE from '../vendor/three.module.min.js';
import { COMMON } from '../shaders/common.js';
import { Pixels, Glows, MARK_PIXELS, HEX } from './pixels.js';
import { SEED } from './tree.js';

const EDGE_VERT = /* glsl */`
uniform sampler2D uBones;
attribute vec4 aE; // bone (or -1), end (0 base, 1 tip), order, unused
uniform float uReveal, uAlpha, uTime;
varying float vA; varying float vPulse;
void main(){
  vec3 wp = position;
  int i = int(aE.x);
  if (aE.x >= 0.0) {
    mat4 M = mat4(texelFetch(uBones, ivec2(0, i), 0), texelFetch(uBones, ivec2(1, i), 0), texelFetch(uBones, ivec2(2, i), 0), texelFetch(uBones, ivec2(3, i), 0));
    wp = (M * vec4(0.0, aE.y * texelFetch(uBones, ivec2(4, i), 0).x, 0.0, 1.0)).xyz;
  }
  float o = aE.z;
  vA = uAlpha * smoothstep(o, o + 0.06, uReveal);
  float ph = fract(o * 1.6 - uTime * 0.09);
  vPulse = exp(-pow((ph - 0.5) * 12.0, 2.0));
  gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
}`;
const EDGE_FRAG = /* glsl */`
${COMMON}
varying float vA; varying float vPulse;
void main(){ gl_FragColor = vec4((LICHEN * 0.05 + SPROUT * 0.35 * vPulse) * vA, 1.0); }`;

export class Network {
  constructor(tree, roots) {
    const B = tree.B, n = tree.n;
    // path length from the seed for every bone tip (tree space at full growth)
    const path = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const p = B.parent[i];
      path[i] = (p >= 0 ? path[p] - B.len[p] * (1 - B.at[i]) : 0) + B.len[i];
    }
    const maxP = Math.max(...path);
    const rs = 2.3; // grown root scale
    const rootWorld = (p) => [SEED[0] + (p[0] - SEED[0]) * rs, SEED[1] + (p[1] - SEED[1]) * rs, SEED[2] + (p[2] - SEED[2]) * rs];
    // nodes: [bone or -1, world pos (roots), order]
    const nodes = [];
    for (let i = 0; i < n; i++) if (B.depth[i] < 3 || i % 2 === 0) nodes.push([i, [0, 0, 0], (path[i] / maxP) * 0.92]);
    roots.nodePos.forEach((p, k) => nodes.push([-1, rootWorld(p), roots.nodeOrder[k] * 0.8]));
    this.nodes = nodes;

    // edges
    const ne = n + 0;
    const rootSegs = [];
    // roots as a chain through their nodes in growth order is enough for the graph look
    const byOrder = roots.nodePos.map((p, k) => [p, roots.nodeOrder[k]]).sort((a, b) => a[1] - b[1]);
    for (let k = 1; k < byOrder.length; k++) {
      // connect each node to the nearest earlier node
      let best = 0, bd = 1e9;
      for (let j = 0; j < k; j++) { const d = Math.hypot(byOrder[k][0][0] - byOrder[j][0][0], byOrder[k][0][1] - byOrder[j][0][1], byOrder[k][0][2] - byOrder[j][0][2]); if (d < bd) { bd = d; best = j; } }
      rootSegs.push([rootWorld(byOrder[best][0]), rootWorld(byOrder[k][0]), byOrder[k][1] * 0.8]);
    }
    rootSegs.push([rootWorld(SEED), rootWorld(byOrder[0][0]), 0]);
    const nv = (ne + rootSegs.length) * 2;
    const pos = new Float32Array(nv * 3), aE = new Float32Array(nv * 4);
    let v = 0;
    for (let i = 0; i < n; i++) {
      const o = path[i] / maxP * 0.92;
      aE.set([i, 0, o, 0], v * 4); v++;
      aE.set([i, 1, o, 0], v * 4); v++;
    }
    for (const [a, b, o] of rootSegs) {
      pos.set(a, v * 3); aE.set([-1, 0, o, 0], v * 4); v++;
      pos.set(b, v * 3); aE.set([-1, 1, o, 0], v * 4); v++;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('aE', new THREE.BufferAttribute(aE, 4));
    this.eu = { uBones: { value: tree.tex }, uReveal: { value: 0 }, uAlpha: { value: 0 }, uTime: { value: 0 } };
    this.edges = new THREE.LineSegments(g, new THREE.ShaderMaterial({
      uniforms: this.eu, vertexShader: EDGE_VERT, fragmentShader: EDGE_FRAG,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    this.edges.frustumCulled = false; this.edges.renderOrder = 8;

    // node cores (crisp pixels) and halos
    const N = nodes.length;
    this.px = new Pixels(N, { bones: tree.tex });
    this.glow = new Glows(N, { bones: tree.tex });
    nodes.forEach(([b, p, o], k) => {
      const hex = b >= 0 && B.depth[b] >= 2 ? HEX.sprout : b >= 0 ? HEX.sage : HEX.lichen;
      this.px.set(k, p, hex, b >= 0 && B.depth[b] < 2 ? 3 : 2, 1, o, 0);
      this.px.bone[k] = b;
      this.glow.set(k, p, b >= 0 && B.depth[b] >= 2 ? HEX.sprout : HEX.sage, 0.1, b >= 0 ? 0.09 : 0.06, o, 1);
      this.glow.bone[k] = b;
    });
    this.px.dirty(); this.glow.dirty();

    // the 74 pixels of the mark, each flying to one of the earliest nodes
    const early = nodes.map((nd, k) => [k, nd[2]]).sort((a, b) => a[1] - b[1]).slice(0, MARK_PIXELS.length).map((e) => e[0]);
    const pix = MARK_PIXELS.slice().sort((a, b) => a[1] - b[1] || a[0] - b[0]);
    const targets = early.slice().sort((a, b) => this.nodeY(b, tree) - this.nodeY(a, tree));
    this.mark = new Pixels(pix.length, { bones: tree.tex, mark: true });
    pix.forEach(([c, r], k) => {
      const t = targets[k];
      this.mark.set(k, nodes[t][1], HEX.bone, 3, 1, (k * 0.618) % 1, 0);
      this.mark.bone[k] = nodes[t][0];
      this.mark.scr.set([c, r], k * 2);
    });
    this.mark.dirty();
  }

  nodeY(k, tree) {
    const [b, p] = this.nodes[k];
    return b >= 0 ? tree.B.pos[b][1] : p[1];
  }

  addTo(scene, overlay) { scene.add(this.edges, this.glow.mesh); overlay.add(this.px.mesh, this.mark.mesh); }

  update(s, time, res, rect) {
    const a = s.net;
    this.eu.uAlpha.value = a; this.eu.uReveal.value = s.netReveal; this.eu.uTime.value = time;
    this.glow.u.uAlpha.value = a; this.glow.u.uReveal.value = s.netReveal; this.glow.u.uTime.value = time;
    // node pixels appear as the graph is revealed; the mark's own pixels hand over to them
    this.px.u.uAlpha.value = a * (s.netMorph > 0.98 ? 1 : 0.0) * 0.85;
    this.px.u.uReveal.value = s.netReveal;
    this.px.u.uRes.value.copy(res);
    const mk = this.mark.u;
    mk.uRes.value.copy(res); mk.uMorph.value = s.netMorph; mk.uMark.value.set(rect[0], rect[1], rect[2]);
    mk.uAlpha.value = a * (s.netMorph < 0.999 ? 1 : 0);
    const on = a > 0.002;
    this.edges.visible = this.glow.mesh.visible = this.px.mesh.visible = on;
    this.mark.mesh.visible = on && s.netMorph < 0.999;
  }
}
