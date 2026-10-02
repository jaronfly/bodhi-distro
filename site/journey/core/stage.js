// The stage: owns the renderer and the loop, and wires the timeline and the
// director to the world. Motion rules, pause, adaptive resolution and context
// loss live here.
import * as THREE from '../vendor/three.module.min.js';
import { Timeline, CANON } from './timeline.js';
import { Director, STILL_P } from './director.js';
import { Quality } from './quality.js';
import { sstep } from './math.js';
import { srgb, HEX } from './palette.js';
import { Sky } from '../world/sky.js';
import { Land } from '../world/land.js';
import { Tree, SEED } from '../world/tree.js';
import { Roots } from '../world/roots.js';
import { Network } from '../world/network.js';
import { Cosmos } from '../world/cosmos.js';
import { Pixels, Glows, markRect } from '../world/pixels.js';
import { Post, inverseTone } from '../world/post.js';

const DEG = Math.PI / 180;
const html = document.documentElement;
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const motionOff = () => reduced.matches || html.dataset.motion === 'off';
const NEW_SEED = [2.2, -0.345, 0.03];

export function start(mount, canvas, gl, opts = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, context: gl, antialias: false, alpha: false, depth: true, stencil: false, powerPreference: 'high-performance' });
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.autoClear = false;
  canvas.setAttribute('aria-hidden', 'true');
  canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none';
  mount.appendChild(canvas);

  const quality = new Quality(opts.dpr);
  const timeline = new Timeline();
  const director = new Director();

  const scene = new THREE.Scene();
  const overlay = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 6000);

  const sky = new Sky(renderer, quality);
  const shared = sky.u;
  const land = new Land(shared, quality);
  const tree = new Tree(shared, quality);
  const roots = new Roots();
  const network = new Network(tree, roots);
  const cosmos = new Cosmos(quality);
  const post = new Post();
  sky.addTo(scene); land.addTo(scene); tree.addTo(scene); roots.addTo(scene);
  network.addTo(scene, overlay); cosmos.addTo(scene, overlay);

  // seeds: one intact pixel, its two halves after it splits, and the new seed
  const seedPx = new Pixels(6);
  seedPx.set(0, SEED, HEX.saffron, 0.022, 1, 0, 1);
  seedPx.set(1, SEED, HEX.saffron, 0.022, 0, 0, 1);
  seedPx.set(2, SEED, HEX.saffron, 0.022, 0, 0, 1);
  seedPx.set(3, NEW_SEED, HEX.saffron, 0.022, 0, 0, 1);
  seedPx.wh.set([0.5, 1, 0.5, 1], 2);
  seedPx.dirty();
  const seedGlow = new Glows(2);
  seedGlow.set(0, SEED, HEX.saffron, 0.5, 0.05);
  seedGlow.set(1, NEW_SEED, HEX.saffron, 0.5, 0.05);
  seedGlow.dirty();
  scene.add(seedGlow.mesh); overlay.add(seedPx.mesh);
  // root graph nodes as pixels
  const rootPx = new Pixels(roots.nodePos.length);
  roots.nodePos.forEach((p, k) => rootPx.set(k, [p[0], p[1], 0], roots.nodeStage[k] === 0 ? HEX.sprout : HEX.sage, roots.nodeStage[k] === 2 ? 2 : 3, 0.9, roots.nodeOrder[k], 0));
  rootPx.dirty();
  overlay.add(rootPx.mesh);

  // render targets
  let rt = null, W = 1, H = 1, cssW = 1, cssH = 1;
  const res = new THREE.Vector2(1, 1);
  let rect = [0, 0, 4];
  function resize(force) {
    const w = mount.clientWidth || innerWidth, h = mount.clientHeight || innerHeight;
    // ignore small height-only changes (mobile URL bar), the canvas stretches instead
    if (!force && w === cssW && Math.abs(h - cssH) < 120 && rt) return false;
    cssW = w; cssH = h;
    const dpr = quality.dpr;
    renderer.setPixelRatio(dpr); renderer.setSize(w, h, false);
    W = Math.max(1, Math.floor(w * dpr)); H = Math.max(1, Math.floor(h * dpr));
    res.set(W, H);
    if (!rt) rt = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, samples: quality.samples, depthBuffer: true });
    else rt.setSize(W, H);
    camera.aspect = w / h;
    rect = markRect(W, H);
    return true;
  }

  // ------------------------------------------------------------------ camera
  const tmpA = new THREE.Vector3(), tmpB = new THREE.Vector3(), tmpC = new THREE.Vector3();
  const upA = new THREE.Vector3(0, 1, 0), upB = new THREE.Vector3(), nY = new THREE.Vector3();
  const clearCol = new THREE.Color(), mA = new THREE.Matrix4(), mB = new THREE.Matrix4();
  const lp = [0, 0, 0], lX = [0, 0, 0], lY = [0, 0, 0];
  function placeCamera(s) {
    const aspect = camera.aspect, tanH = Math.tan((s.fov * DEG) / 2);
    let dist = Math.max(s.dist, s.fitW / (2 * tanH * aspect));
    const cp = Math.cos(s.pitch);
    tmpA.set(s.look[0], s.look[1], s.look[2]);
    tmpB.set(cp * Math.sin(s.yaw), Math.sin(s.pitch), cp * Math.cos(s.yaw));
    let up = upA;
    const w = s.focusLeaf;
    if (w > 0 && tree.focus >= 0) {
      tree.leafWorld(tree.focus, lp, lX, lY);
      const size = tree.leafSize[tree.focus] * tree.u.uLeafSize.value;
      const Z = [lX[1] * lY[2] - lX[2] * lY[1], lX[2] * lY[0] - lX[0] * lY[2], lX[0] * lY[1] - lX[1] * lY[0]];
      tmpC.set(lp[0] + (lX[0] * 0.55 + Z[0] * 0.12) * size, lp[1] + (lX[1] * 0.55 + Z[1] * 0.12) * size, lp[2] + (lX[2] * 0.55 + Z[2] * 0.12) * size);
      const dLeaf = (0.08 * size) / Math.tan(20 * DEG);
      const e = w * w * (3 - 2 * w);
      tmpA.lerp(tmpC, e);
      tmpB.lerp(nY.set(lY[0], lY[1], lY[2]), e).normalize();
      dist = Math.exp(Math.log(dist) * (1 - e) + Math.log(dLeaf) * e);
      upB.set(Z[0], Z[1], Z[2]); up = upB.lerp(upA, 1 - e).normalize();
      camera.fov = s.fov + (40 - s.fov) * e;
    } else camera.fov = s.fov;
    camera.position.copy(tmpA).addScaledVector(tmpB, dist);
    camera.up.copy(up);
    camera.lookAt(tmpA);
    camera.near = Math.max(0.002, dist * 0.02);
    camera.far = 6000;
    camera.updateProjectionMatrix();
    // lens shift keeps the subject off-centre on wide screens only
    const sx = aspect > 1.2 ? s.shiftX : 0;
    camera.projectionMatrix.elements[8] = -sx;
    camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  }

  // ------------------------------------------------------------------ frame
  const voidRGB = [0, 0, 0], soil = srgb(HEX.soil);
  let time = 0;
  const px1 = new Uint8Array(4);
  function renderFrame(c, dt, still) {
    const s = director.eval(c);
    placeCamera(s);
    // tree first: others read its bone texture and leaf poses
    tree.update(s, time, still ? 0 : dt);
    if (s.focusLeaf > 0) placeCamera(s);
    sky.update(s, camera, time);
    const exposure = s.exposure;
    for (let k = 0; k < 3; k++) voidRGB[k] = inverseTone(soil[k], soil[k], exposure);
    shared.uVoid.value.set(voidRGB[0], voidRGB[1], voidRGB[2]);
    shared.uDpr.value = quality.dpr; shared.uStill.value = still ? 1 : 0;
    const seedA = s.seedHero * (1 - 0.35 * s.seedSplit), seedB = s.seedNew;
    land.update(s, [seedA * 1.0, seedB * 1.0]);
    roots.update(s, time);
    network.update(s, time, res, rect);
    cosmos.update(s, time, res, quality.dpr, still);
    // seeds
    const split = s.seedSplit, sp = split * 0.009;
    seedPx.p[1] = s.seedHero * (split < 0.02 ? 1 : 0);
    seedPx.pos.set([SEED[0] - 0.0055 - sp, SEED[1] - sp * 0.3, SEED[2]], 3); seedPx.p[5] = s.seedHero * (split >= 0.02 ? 1 : 0);
    seedPx.pos.set([SEED[0] + 0.0055 + sp, SEED[1] + sp * 0.2, SEED[2]], 6); seedPx.p[9] = s.seedHero * (split >= 0.02 ? 1 : 0);
    seedPx.p[13] = seedB;
    seedPx.dirty('aPos', 'aP');
    seedPx.u.uRes.value.copy(res);
    seedPx.mesh.visible = s.seedHero > 0.001 || seedB > 0.001;
    const breathe = still ? 1 : 0.9 + 0.1 * Math.sin(time * 0.9);
    seedGlow.u.uAlpha.value = breathe * s.env;
    seedGlow.p[1] = s.seedHero * (1 - 0.5 * split); seedGlow.p[5] = seedB;
    seedGlow.dirty();
    seedGlow.mesh.visible = seedPx.mesh.visible;
    rootPx.u.uRes.value.copy(res);
    rootPx.u.uReveal.value = s.rootGrow;
    rootPx.u.uAlpha.value = sstep(1.0, 2.0, s.rootLight) * (s.cut < 100 ? 1 : 0);
    rootPx.u.uModel.value.makeTranslation(-SEED[0], -SEED[1], 0).premultiply(mA.makeScale(s.rootScale, s.rootScale, 1)).premultiply(mB.makeTranslation(SEED[0], SEED[1], s.cut + 0.008));
    rootPx.mesh.visible = s.cut < 100 && s.rootLight > 1;

    // post uniforms
    const pu = post.u;
    pu.uRes.value.copy(res); pu.uExposure.value = exposure; pu.uGrain.value = s.grain; pu.uCalm.value = s.calm;
    pu.uMicro.value = s.micro; pu.uZoom.value = s.zoom; pu.uPad.value = s.pad; pu.uPix.value = s.pix; pu.uMarkT.value = s.markT;
    pu.uMT.value = still ? 0 : time; pu.uNuc.value = sstep(2.78, 2.9, c);
    pu.uMark.value.set(rect[0], rect[1], rect[2]);
    pu.uSeed.value = still ? 1 : (Math.floor(time * 24) % 997);
    pu.uFade.value = fade;

    if (s.micro < 0.999) {
      renderer.setRenderTarget(rt);
      renderer.setClearColor(clearCol.setRGB(voidRGB[0], voidRGB[1], voidRGB[2]), 0);
      renderer.clear(true, true, false);
      renderer.render(scene, camera);
    }
    pu.uScene.value = rt.texture;
    renderer.setRenderTarget(null);
    renderer.render(post.scene, post.cam);
    renderer.render(overlay, camera);
    if (opts.sync) gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px1);
    api.frames++; api.renderedC = c;
  }

  // ------------------------------------------------------------------ loop & state
  let raf = 0, last = 0, running = false, lost = false, on = false, cS = null, fade = 1, jump = 0, lastScene = null, stillKey = null;
  const api = (window.BodhiJourney = { u: 0, scene: null, still: motionOff(), progress: 0, c: 0, frames: 0 });
  // debugging: jump the smoothed camera straight to the scroll position
  api.snap = () => { timeline.update(); publish(); cS = timeline.c; fade = 1; jump = 0; };

  function publish() {
    api.u = timeline.u; api.scene = timeline.scene; api.progress = timeline.progress; api.c = timeline.c; api.still = motionOff();
    api.dpr = quality.dpr; api.frameMs = quality.ema;
    if (timeline.scene !== lastScene) {
      lastScene = timeline.scene;
      document.dispatchEvent(new CustomEvent('journey:scene', { detail: { id: timeline.scene, progress: timeline.progress, u: timeline.u } }));
    }
  }
  function firstFrameDone() { if (!on) { on = true; html.classList.add('journey-on'); } }

  function stillC() {
    const id = timeline.scene, i = timeline.index;
    if (id in CANON) return CANON[id] + (STILL_P[id] ?? 0.5);
    return timeline.canonical(i, 0.5);
  }
  function renderStill(force) {
    if (lost) return;
    const key = timeline.scene + '|' + W + 'x' + H;
    if (!force && key === stillKey) return;
    stillKey = key; fade = 1;
    time = 20;
    renderFrame(stillC(), 0, true);
    firstFrameDone();
  }

  function frame(now) {
    raf = 0;
    if (!running || lost) return;
    const dt = last ? Math.min(0.1, (now - last) / 1000) : 1 / 60;
    last = now;
    if (quality.sample(dt * 1000)) resize(true);
    time += dt;
    const c = timeline.c;
    if (cS === null) cS = c;
    // big jumps (anchor links) fade through the dark instead of flying through every scene
    if (Math.abs(c - cS) > 1.2 && !jump) jump = 1;
    if (jump) {
      fade = Math.max(0, fade - dt * 4);
      if (fade === 0) { cS = c; jump = 0; }
    } else {
      fade = Math.min(1, fade + dt * 3);
      cS += (c - cS) * (1 - Math.exp(-dt * 7));
    }
    renderFrame(cS, dt, false);
    firstFrameDone();
    raf = requestAnimationFrame(frame);
  }

  function shouldRun() { return !lost && !document.hidden && !timeline.past && !motionOff(); }
  function sync() {
    const want = shouldRun();
    if (want && !running) { running = true; last = 0; if (!raf) raf = requestAnimationFrame(frame); }
    else if (!want && running) { running = false; if (raf) cancelAnimationFrame(raf); raf = 0; }
    if (motionOff() && !lost) renderStill(false);
  }

  let pending = 0;
  function onScroll() {
    if (pending) return;
    pending = requestAnimationFrame(() => { pending = 0; timeline.update(); publish(); sync(); });
  }
  function onResize() {
    if (resize(false)) { stillKey = null; }
    timeline.update(); publish(); sync();
    if (motionOff()) renderStill(true);
  }
  function onMotion() { cS = null; stillKey = null; timeline.update(); publish(); sync(); }

  addEventListener('scroll', onScroll, { passive: true });
  addEventListener('resize', onResize, { passive: true });
  document.addEventListener('visibilitychange', sync);
  reduced.addEventListener ? reduced.addEventListener('change', onMotion) : reduced.addListener(onMotion);
  document.addEventListener('bodhi:motion', onMotion);
  window.addEventListener('bodhi:motion', onMotion);
  new MutationObserver(onMotion).observe(html, { attributes: true, attributeFilter: ['data-motion'] });
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => onResize()).observe(mount);
  // page content can change height (images, opened notes): re-measure occasionally
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => onScroll()).observe(document.body);
  cosmos.onChange = () => { if (motionOff()) { stillKey = null; renderStill(true); } };

  let lostTimer = 0;
  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault(); lost = true; running = false; if (raf) cancelAnimationFrame(raf); raf = 0;
    lostTimer = setTimeout(() => { html.classList.remove('journey-on'); on = false; }, 2500);
  });
  canvas.addEventListener('webglcontextrestored', () => {
    clearTimeout(lostTimer); lost = false; sky.dirty = true; tree.tex.needsUpdate = true;
    stillKey = null; cS = null; sync();
  });

  resize(true);
  timeline.update(); publish();
  // compile everything up front so the first scroll does not stutter
  try { renderer.compile(scene, camera); renderer.compile(overlay, camera); } catch (e) { /* compile is an optimisation */ }
  if (motionOff()) renderStill(true);
  sync();
  return api;
}
