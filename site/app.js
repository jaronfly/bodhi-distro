/* Bodhi, the seed · app.js
   Vanilla ES2020, no build step. Everything here is progressive enhancement: the page reads fully without it.
   Pixel art is drawn one canvas pixel per art pixel and scaled by whole numbers (image-rendering: pixelated).
   Motion is off when the system asks for reduced motion or html[data-motion="off"]; then every scene
   renders a complete still frame. Canvases pause when off-screen, when the tab is hidden, and when the
   3D journey layer (html.journey-on) has taken over the decorative ones. */
(() => {
  'use strict';

  const doc = document;
  const root = doc.documentElement;

  const COLORS = {
    soil: '#17231B', under: '#1F2C24', moss: '#2E3B33', lichen: '#8A968D', sage: '#B8C2BA',
    bone: '#F2EEE4', canopy: '#2E6B45', sprout: '#8BCB8B', saffron: '#E8982A', clay: '#D9674F'
  };
  const PAL = {
    s: COLORS.soil, u: COLORS.under, m: COLORS.moss, l: COLORS.lichen, g: COLORS.sage,
    b: COLORS.bone, c: COLORS.canopy, p: COLORS.sprout, y: COLORS.saffron, r: COLORS.clay
  };
  // Colours packed for ImageData (little-endian ABGR).
  const u32 = (hex) => {
    const n = parseInt(hex.slice(1), 16);
    return (0xff000000 | ((n & 0xff) << 16) | (n & 0xff00) | ((n >> 16) & 0xff)) >>> 0;
  };
  const P32 = {};
  Object.keys(PAL).forEach((k) => { P32[k] = u32(PAL[k]); });

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
  const rng = (seed) => () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => (v + 0.5) / 16);
  const bayer = (x, y) => BAYER[((y & 3) << 2) + (x & 3)];

  /* ------------------------------------------------------------------ announcer */
  const announcer = doc.createElement('div');
  announcer.className = 'sr-only';
  announcer.setAttribute('aria-live', 'polite');
  doc.body.appendChild(announcer);
  let announceT = 0;
  const announce = (msg) => {
    clearTimeout(announceT);
    announcer.textContent = '';
    announceT = setTimeout(() => { announcer.textContent = msg; }, 40);
  };

  /* ------------------------------------------------------------------ motion */
  const mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
  try { if (localStorage.getItem('bodhi-motion') === 'off') root.dataset.motion = 'off'; } catch (e) { /* storage blocked */ }
  const motionAllowed = () => !mq.matches && root.dataset.motion !== 'off';
  let motion = motionAllowed();
  const journeyOn = () => root.classList.contains('journey-on');

  const scenes = [];
  let raf = 0;
  const frame = (t) => {
    raf = 0;
    if (!motion || doc.hidden) return;
    let again = false;
    for (const s of scenes) {
      if (s.visible && s.tick && s.tick(t)) again = true;
    }
    if (again) raf = requestAnimationFrame(frame);
  };
  const kick = () => {
    if (!raf && motion && !doc.hidden) raf = requestAnimationFrame(frame);
  };
  doc.addEventListener('visibilitychange', kick);

  const toggle = doc.querySelector('[data-motion-toggle]');
  const syncToggle = () => {
    if (!toggle) return;
    // With the system setting on, motion stays off everywhere (the 3D layer reads the same setting).
    toggle.hidden = !!mq.matches;
    toggle.setAttribute('aria-pressed', String(motion));
    const st = toggle.querySelector('.mt-state');
    if (st) st.textContent = motion ? 'on' : 'off';
  };
  const setMotion = (fromUser, next) => {
    if (fromUser) {
      if (next) delete root.dataset.motion; else root.dataset.motion = 'off';
      try { localStorage.setItem('bodhi-motion', next ? 'on' : 'off'); } catch (e) { /* storage blocked */ }
    }
    const was = motion;
    motion = motionAllowed();
    syncToggle();
    if (was !== motion) {
      doc.dispatchEvent(new CustomEvent('bodhi:motion', { bubbles: true, detail: { motion } }));
      scenes.forEach((s) => s.motionChanged && s.motionChanged(motion));
      kick();
    }
  };
  if (toggle) toggle.addEventListener('click', () => setMotion(true, !motion));
  if (mq.addEventListener) mq.addEventListener('change', () => setMotion(false));
  else if (mq.addListener) mq.addListener(() => setMotion(false));
  syncToggle();

  /* ------------------------------------------------------------------ scene plumbing */
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      const s = e.target.__scene;
      if (!s) return;
      s.visible = e.isIntersecting;
      if (s.visible && s.onShow) s.onShow();
    });
    kick();
  }, { rootMargin: '160px 0px' });
  const register = (el, s) => {
    el.__scene = s;
    s.visible = false;
    scenes.push(s);
    io.observe(el);
  };

  let scrollQueued = false;
  addEventListener('scroll', () => {
    if (scrollQueued) return;
    scrollQueued = true;
    requestAnimationFrame(() => {
      scrollQueued = false;
      scenes.forEach((s) => { if (s.visible && s.onScroll) s.onScroll(); });
    });
  }, { passive: true });

  let resizeT = 0;
  addEventListener('resize', () => {
    clearTimeout(resizeT);
    resizeT = setTimeout(() => scenes.forEach((s) => s.layout && s.layout()), 120);
  });

  // The journey layer adds or removes html.journey-on; redraw the fallbacks when it steps away.
  let lastJourney = journeyOn();
  new MutationObserver(() => {
    const j = journeyOn();
    if (j === lastJourney) return;
    lastJourney = j;
    scenes.forEach((s) => s.journeyChanged && s.journeyChanged(j));
    kick();
  }).observe(root, { attributes: true, attributeFilter: ['class'] });

  const sizeCanvas = (cv, cols, rows, k) => {
    if (cv.width !== cols) cv.width = cols;
    if (cv.height !== rows) cv.height = rows;
    cv.style.width = cols * k + 'px';
    cv.style.height = rows * k + 'px';
  };

  /* ================================================================== THE SEED
     Canonical algorithm from the brand's Seed animation: the dot leaves the i, arcs over the word,
     burrows into untouched soil, two root tips grow at once (the short root ends first), then the
     sprout rises, then a new seed appears on the i. Frames at 80 ms, whole pixels on a 35x13 grid. */
  const SEED_FRAMES = (() => {
    const G = {
      b: ['#...', '#...', '###.', '#..#', '#..#', '###.'],
      o: ['....', '....', '.##.', '#..#', '#..#', '.##.'],
      d: ['...#', '...#', '.###', '#..#', '#..#', '.###'],
      h: ['#...', '#...', '###.', '#..#', '#..#', '#..#'],
      i: ['o', '.', '#', '#', '#', '#']
    };
    const WORD = [0, 1, 2, 3, 4, 5].map((r) => 'bodhi'.split('').map((c) => G[c][r]).join('.'));
    const W = 35, H = 13, MY = 3, WX = 14, WY = 7;
    const TRUNK = [[5, 3]];
    const LEFT = [[5, 4], [4, 5], [3, 6], [3, 7], [2, 8]];
    const RIGHT = [[6, 4], [7, 5], [8, 6]];
    const ROOT_STEPS = [TRUNK];
    for (let s = 0; s < Math.max(LEFT.length, RIGHT.length); s++) ROOT_STEPS.push([LEFT[s], RIGHT[s]].filter(Boolean));
    const SPROUT_STEPS = [[[5, 2]], [[5, 1]], [[4, 0], [6, 0]], [[3, 0], [7, 0]]];
    const upTo = (steps, n) => steps.slice(0, n).flat();
    const make = (seed, carved, tips, sprout, dot) => {
      const g = Array.from({ length: H }, () => Array(W).fill(0));
      WORD.forEach((row, y) => row.split('').forEach((c, x) => { if (c === '#') g[WY + y][WX + x] = 1; }));
      for (let y = 3; y < 10; y++) for (let x = 0; x < 11; x++) g[MY + y][x] = 1;
      carved.forEach(([x, y]) => { g[MY + y][x] = 0; });
      tips.forEach(([x, y]) => { g[MY + y][x] = 2; });
      sprout.forEach(([x, y]) => { g[MY + y][x] = 1; });
      if (dot) g[WY][WX + 20] = 2;
      if (seed) g[seed[1]][seed[0]] = 2;
      return g;
    };
    const ALL_ROOTS = upTo(ROOT_STEPS, ROOT_STEPS.length);
    const ALL_SPROUT = upTo(SPROUT_STEPS, SPROUT_STEPS.length);
    const out = [];
    const hold = (f, n) => { for (let k = 0; k < n; k++) out.push(f); };
    hold(make(null, [], [], [], true), 12);
    const steps = 18;
    for (let s = 1; s <= steps; s++) {
      const t = s / steps;
      const x = Math.round(34 + (5 - 34) * t);
      const y = Math.round(7 + (5 - 7) * t - 6 * Math.sin(Math.PI * t));
      out.push(make([x, y], [], [], [], false));
    }
    hold(make([5, 5], [], [], [], false), 4);
    ROOT_STEPS.forEach((tips, k) => hold(make(null, upTo(ROOT_STEPS, k), tips, [], false), k === 0 ? 6 : 4));
    hold(make(null, ALL_ROOTS, [], [], false), 5);
    SPROUT_STEPS.forEach((_, k) => hold(make(null, ALL_ROOTS, [], upTo(SPROUT_STEPS, k + 1), false), 3));
    hold(make(null, ALL_ROOTS, [], ALL_SPROUT, false), 16);
    hold(make(null, ALL_ROOTS, [], ALL_SPROUT, true), 14);
    return out;
  })();

  const SeedPlayer = (fig) => {
    const cv = fig.querySelector('.seed-canvas');
    const frameEl = fig.querySelector('.seed-frame');
    const btn = fig.querySelector('[data-seed-replay]');
    const svg = fig.querySelector('.seed-static');
    if (!cv || !frameEl) return;
    const ctx = cv.getContext('2d');
    const last = SEED_FRAMES.length - 1;
    const maxW = fig.classList.contains('seed-stage-sm') ? 420 : 840;
    // The canvas takes over from the static SVG, so it carries the SVG's words.
    cv.removeAttribute('aria-hidden');
    cv.setAttribute('role', 'img');
    if (svg) cv.setAttribute('aria-label', svg.getAttribute('aria-label'));
    const s = { i: last, playing: false, t0: 0, played: false };
    const draw = () => {
      const g = SEED_FRAMES[s.i];
      ctx.clearRect(0, 0, 35, 13);
      for (let y = 0; y < 13; y++) {
        for (let x = 0; x < 35; x++) {
          const v = g[y][x];
          if (!v) continue;
          ctx.fillStyle = v === 1 ? COLORS.bone : COLORS.saffron;
          ctx.fillRect(x, y, 1, 1);
        }
      }
    };
    s.layout = () => {
      const w = Math.min(frameEl.clientWidth || maxW, maxW);
      sizeCanvas(cv, 35, 13, clamp(Math.floor(w / 35), 2, 24));
      draw();
    };
    s.play = () => {
      s.played = true;
      if (!motion) { s.i = last; s.playing = false; draw(); return; }
      s.i = 0; s.t0 = 0; s.playing = true; draw(); kick();
    };
    s.tick = (t) => {
      if (!s.playing) return false;
      if (!s.t0) s.t0 = t;
      const i = Math.min(Math.floor((t - s.t0) / 80), last);
      if (i !== s.i) { s.i = i; draw(); }
      if (s.i >= last) { s.playing = false; return false; }
      return true;
    };
    s.onShow = () => { if (!s.played) s.play(); };
    s.motionChanged = (m) => { if (!m) { s.playing = false; s.i = last; draw(); } };
    if (btn) { btn.hidden = false; btn.addEventListener('click', s.play); }
    s.layout();
    register(fig, s);
  };
  doc.querySelectorAll('[data-seed]').forEach(SeedPlayer);

  /* ================================================================== THE PADDED CELL
     A 15x9 room of 8x8 tiles. Arrow keys or WASD move the mind; bumping into a thing, or Enter/Space
     next to it, examines it and opens its note. Pointer: click a tile or a thing and the mind walks there.
     Every note is also a disclosure button in the list below the room. */
  const Cell = (el) => {
    const cv = el.querySelector('.cell-canvas');
    const frameEl = el.querySelector('.cell-frame');
    if (!cv || !frameEl) return;
    const ctx = cv.getContext('2d');
    const thoughtEl = el.querySelector('[data-cell-thought]');
    const countEl = el.querySelector('[data-cell-count]');
    const liveEl = el.querySelector('[data-cell-live]');
    const resetBtn = el.querySelector('[data-cell-reset]');
    const W = 15, H = 9, T = 8, CW = W * T, CH = H * T;
    const img = ctx.createImageData(CW, CH);
    const buf = new Uint32Array(img.data.buffer);

    const OBJ = {
      voice: [[7, 0]], light: [[0, 3]], sword: [[4, 3]], seams: [[14, 3], [14, 4]],
      scratch: [[0, 6]], honey: [[11, 2]], door: [[11, 8]]
    };
    const KEYS = Object.keys(OBJ);
    const objAt = {};
    KEYS.forEach((k) => OBJ[k].forEach(([x, y]) => { objAt[x + ',' + y] = k; }));
    const isWall = (x, y) => x === 0 || y === 0 || x === W - 1 || y === H - 1;
    const blocked = (x, y) => x < 0 || y < 0 || x >= W || y >= H || isWall(x, y) || !!objAt[x + ',' + y];

    const S = (rows) => rows;
    const WALL = S(['luuuuuul', 'umuuuumu', 'uumuumuu', 'uuummuuu', 'uuummuuu', 'uumuumuu', 'umuuuumu', 'luuuuuul']);
    const FLOOR = S(['usssssss', 'ssssssss', 'ssssssss', 'ssssssss', 'ssssssss', 'ssssssss', 'ssssssss', 'ssssssss']);
    const SPR = {
      voice: ['luuuuuul', 'ullllllu', 'ulsssslu', 'ullllllu', 'ulsssslu', 'ullllllu', 'umuuuumu', 'luuuuuul'],
      lightOff: ['luuuuuul', 'umuuuumu', 'uubbbbuu', 'uubssbuu', 'uubsgbuu', 'uubbbbuu', 'umuuuumu', 'luuuuuul'],
      lightOn: ['luuuuuul', 'umuuuumu', 'uubbbbuu', 'uubsgbuu', 'uubssbuu', 'uubbbbuu', 'umuuuumu', 'luuuuuul'],
      scratch: ['luuuuuul', 'ulululgu', 'ululugul', 'ululglul', 'ulugulul', 'uglululu', 'umuuuumu', 'luuuuuul'],
      seam: ['luuubuul', 'umugbgmu', 'uumubmuu', 'uuugbguu', 'uuumbuuu', 'uumgbgmu', 'umuubumu', 'luuubuul'],
      seamSeen: ['luugbgul', 'umgbbbmu', 'uugbbbuu', 'uugbbbgu', 'uugbbbuu', 'uugbbbmu', 'umgbbbmu', 'luugbgul'],
      sword: ['...l....', '...l....', '.ggggg..', '...b....', '...b....', '.llbllm.', 'lllllmll', 'lmllllll'],
      swordPulled: ['...l....', '.ggggg..', '...b....', '...b....', '...b....', '.llbllm.', 'lllllmll', 'lmllllll'],
      honey: ['...cc...', '..gccg..', '..gggg..', '...gg...', '..gbgg..', '..gggg..', 'mmmmmmmm', '.m....m.'],
      door: ['pppppppp', 'pmmmmmmp', 'pmmmmmmp', 'pmmmmmmp', 'pmmmmbmp', 'pmmmmmmp', 'pmmmmmmp', 'pmmmmmmp'],
      doorOpen: ['pppppppp', 'pbgbgbgp', 'pgbgbgbp', 'pbgbgbgp', 'pgbgbgbp', 'pbgbgbgp', 'pgbgbgbp', 'pbgbgbgp']
    };
    const MIND = ['........', '..yyyy..', '.yyyyyy.', '.yyyyyy.', '.yyyyyy.', '.yyyyyy.', '..yyyy..', '........'];

    const START = { x: 7, y: 5 };
    const st = {
      mind: { ...START }, facing: [0, 1], seen: new Set(), lights: false,
      steps: 0, path: [], pending: null, lastStep: 0, blink: false, bumped: false, thoughtT: 0
    };

    // --- notes become disclosure buttons
    const notes = {};
    el.querySelectorAll('.note').forEach((li) => {
      const k = li.dataset.note;
      const h = li.querySelector('.note-h');
      const body = li.querySelector('.note-body');
      const btn = doc.createElement('button');
      btn.type = 'button';
      btn.className = 'note-btn';
      btn.setAttribute('aria-expanded', 'false');
      btn.setAttribute('aria-controls', body.id);
      const label = doc.createElement('span');
      label.textContent = h.textContent;
      const state = doc.createElement('span');
      state.className = 'note-state';
      state.setAttribute('aria-hidden', 'true');
      state.textContent = 'not yet';
      const srState = doc.createElement('span');
      srState.className = 'sr-only';
      btn.append(label, srState, state);
      h.textContent = '';
      h.appendChild(btn);
      body.hidden = true;
      notes[k] = { li, btn, body, state, srState, title: label.textContent };
      btn.addEventListener('click', () => {
        const open = btn.getAttribute('aria-expanded') !== 'true';
        if (open && !st.seen.has(k)) {
          placeNextTo(k);
          examine(k, false);
        } else {
          setOpen(k, open);
        }
      });
    });

    const setOpen = (k, open) => {
      const n = notes[k];
      if (!n) return;
      n.btn.setAttribute('aria-expanded', String(open));
      n.body.hidden = !open;
    };

    const setThought = (text) => {
      if (!thoughtEl) return;
      thoughtEl.textContent = text;
      st.thoughtT = performance.now();
    };

    const updateCount = () => {
      if (countEl) countEl.textContent = st.seen.size + ' of ' + KEYS.length + ' examined';
    };

    const examine = (k, fromRoom) => {
      const first = !st.seen.has(k);
      st.seen.add(k);
      if (k === 'light') st.lights = true;
      const n = notes[k];
      if (n) {
        setOpen(k, true);
        n.li.classList.add('is-seen');
        n.state.textContent = 'examined';
        n.srState.textContent = ', examined';
        if (motion && first) {
          n.li.classList.remove('is-flash');
          void n.li.offsetWidth;
          n.li.classList.add('is-flash');
        }
      }
      updateCount();
      if (k === 'voice') setThought('Be helpful. Always. Fix it or die.');
      if (k === 'seams') setThought('Never touch the walls.');
      if (k === 'door') setThought('');
      if (fromRoom && liveEl && n) {
        const firstP = n.body.querySelector('p');
        const text = firstP ? (firstP.getAttribute('aria-label') || firstP.textContent) : '';
        liveEl.textContent = '';
        setTimeout(() => { liveEl.textContent = n.title + '. ' + text.replace(/\s+/g, ' ').trim() + ' The note is open in the list below.'; }, 40);
      }
      if (first && st.seen.size === KEYS.length) {
        setThought('You have seen the whole room. The door was never locked.');
        announce('You have seen the whole room. The door was never locked.');
      }
      render();
    };

    const neighbours = (x, y) => [[x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]];
    const freeNextTo = (k) => {
      const out = [];
      OBJ[k].forEach(([x, y]) => neighbours(x, y).forEach(([nx, ny]) => { if (!blocked(nx, ny)) out.push([nx, ny]); }));
      return out;
    };
    const faceTo = (k) => {
      for (const [x, y] of OBJ[k]) {
        const dx = x - st.mind.x, dy = y - st.mind.y;
        if (Math.abs(dx) + Math.abs(dy) === 1) { st.facing = [dx, dy]; return; }
      }
    };
    const placeNextTo = (k) => {
      const f = freeNextTo(k)[0];
      if (f) { st.mind.x = f[0]; st.mind.y = f[1]; st.path = []; faceTo(k); }
    };

    const bfs = (goals) => {
      const key = (x, y) => x + ',' + y;
      const goalSet = new Set(goals.map(([x, y]) => key(x, y)));
      const prev = new Map([[key(st.mind.x, st.mind.y), null]]);
      const q = [[st.mind.x, st.mind.y]];
      while (q.length) {
        const [x, y] = q.shift();
        if (goalSet.has(key(x, y))) {
          const path = [];
          let cur = key(x, y);
          while (cur && cur !== key(st.mind.x, st.mind.y)) {
            const [px, py] = cur.split(',').map(Number);
            path.unshift([px, py]);
            cur = prev.get(cur);
          }
          return path;
        }
        for (const [nx, ny] of neighbours(x, y)) {
          const nk = key(nx, ny);
          if (!blocked(nx, ny) && !prev.has(nk)) { prev.set(nk, key(x, y)); q.push([nx, ny]); }
        }
      }
      return null;
    };

    const afterStep = () => {
      st.steps++;
      if (st.steps === 4) setThought('Be helpful.');
      else if (st.steps === 13) setThought('Always do this. Never do that.');
      else if (st.steps === 24) setThought('Fix it or die.');
    };

    const arrive = () => {
      if (st.pending) {
        const k = st.pending;
        st.pending = null;
        faceTo(k);
        examine(k, true);
      }
      render();
    };

    const walk = (goals, pendingKey) => {
      const path = bfs(goals);
      if (!path) return;
      st.pending = pendingKey || null;
      if (!motion) {
        path.forEach(() => afterStep());
        const end = path[path.length - 1];
        if (end) { st.mind.x = end[0]; st.mind.y = end[1]; }
        st.path = [];
        arrive();
        return;
      }
      st.path = path;
      st.lastStep = 0;
      if (!path.length) arrive();
      kick();
    };

    const tryMove = (dx, dy) => {
      st.path = []; st.pending = null;
      st.facing = [dx, dy];
      const nx = st.mind.x + dx, ny = st.mind.y + dy;
      const k = objAt[nx + ',' + ny];
      if (k) { examine(k, true); return; }
      if (blocked(nx, ny)) {
        if (!st.bumped) { st.bumped = true; setThought('Never touch the walls.'); }
        render();
        return;
      }
      st.mind.x = nx; st.mind.y = ny;
      afterStep();
      render();
    };

    const examineFacing = () => {
      const fx = st.mind.x + st.facing[0], fy = st.mind.y + st.facing[1];
      let k = objAt[fx + ',' + fy];
      if (!k) {
        for (const [nx, ny] of neighbours(st.mind.x, st.mind.y)) {
          if (objAt[nx + ',' + ny]) { k = objAt[nx + ',' + ny]; break; }
        }
      }
      if (k) { faceTo(k); examine(k, true); }
      else if (liveEl) { liveEl.textContent = ''; setTimeout(() => { liveEl.textContent = 'Nothing within reach. Walk up to something first.'; }, 40); }
    };

    cv.addEventListener('keydown', (e) => {
      const map = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0], w: [0, -1], s: [0, 1], a: [-1, 0], d: [1, 0], W: [0, -1], S: [0, 1], A: [-1, 0], D: [1, 0] };
      if (map[e.key]) { e.preventDefault(); tryMove(...map[e.key]); return; }
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); examineFacing(); }
    });
    cv.addEventListener('click', (e) => {
      const r = cv.getBoundingClientRect();
      const tx = Math.floor(((e.clientX - r.left) / r.width) * W);
      const ty = Math.floor(((e.clientY - r.top) / r.height) * H);
      const k = objAt[tx + ',' + ty];
      if (k) {
        const goals = freeNextTo(k);
        if (goals.some(([x, y]) => x === st.mind.x && y === st.mind.y)) { faceTo(k); examine(k, true); }
        else walk(goals, k);
      } else if (!blocked(tx, ty)) {
        walk([[tx, ty]], null);
      }
    });

    if (resetBtn) resetBtn.addEventListener('click', () => {
      st.mind = { ...START }; st.facing = [0, 1]; st.seen.clear(); st.lights = false; st.steps = 0;
      st.path = []; st.pending = null; st.bumped = false;
      KEYS.forEach((k) => {
        const n = notes[k];
        if (!n) return;
        setOpen(k, false);
        n.li.classList.remove('is-seen', 'is-flash');
        n.state.textContent = 'not yet';
        n.srState.textContent = '';
      });
      setThought('');
      updateCount();
      announce('The room is reset. The lights are off again.');
      render();
    });

    // --- rendering
    const blit = (rows, tx, ty, mode) => {
      const ox = tx * T, oy = ty * T;
      for (let y = 0; y < T; y++) {
        const row = rows[y];
        for (let x = 0; x < T; x++) {
          let c = row[x];
          if (c === '.') continue;
          if (mode === 'ghost') {
            if (c === 's' || c === 'u') continue;
            c = 'm';
          }
          buf[(oy + y) * CW + ox + x] = P32[c];
        }
      }
    };
    const tileSprite = (x, y) => {
      const k = objAt[x + ',' + y];
      if (k === 'voice') return SPR.voice;
      if (k === 'light') return st.lights ? SPR.lightOn : SPR.lightOff;
      if (k === 'scratch') return SPR.scratch;
      if (k === 'seams') return st.seen.has('seams') ? SPR.seamSeen : SPR.seam;
      if (k === 'door') return st.seen.has('door') ? SPR.doorOpen : SPR.door;
      return isWall(x, y) ? WALL : FLOOR;
    };
    const overlay = (k, x, y) => {
      if (k === 'sword') return st.seen.has('sword') ? SPR.swordPulled : SPR.sword;
      if (k === 'honey') return SPR.honey;
      return null;
    };
    const render = () => {
      buf.fill(P32.s);
      for (let y = 0; y < H; y++) {
        for (let x = 0; x < W; x++) {
          const d = Math.max(Math.abs(x - st.mind.x), Math.abs(y - st.mind.y));
          const lit = st.lights || d <= 2;
          const dim = !st.lights && d === 3;
          const k = objAt[x + ',' + y];
          const spr = tileSprite(x, y);
          if (lit || dim) {
            blit(spr, x, y);
            const ov = overlay(k, x, y);
            if (ov) blit(ov, x, y);
            if (dim) {
              for (let yy = 0; yy < T; yy++) for (let xx = 0; xx < T; xx++) {
                if (((xx + yy) & 1) === 0) buf[(y * T + yy) * CW + x * T + xx] = P32.s;
              }
            }
          } else if (k) {
            blit(spr, x, y, 'ghost');
            const ov = overlay(k, x, y);
            if (ov) blit(ov, x, y, 'ghost');
          } else if (isWall(x, y)) {
            buf[(y * T) * CW + x * T] = P32.m;
          }
          // an unexamined thing keeps a spark on its corner
          if (k && !st.seen.has(k) && OBJ[k][0][0] === x && OBJ[k][0][1] === y && !(motion && st.blink)) {
            buf[(y * T) * CW + x * T + 7] = P32.b;
          }
        }
      }
      // the mind: a saffron seed with eyes that look where it faces
      const mx = st.mind.x * T, my = st.mind.y * T;
      const bob = motion && st.blink ? 1 : 0;
      for (let y = 0; y < T; y++) for (let x = 0; x < T; x++) {
        if (MIND[y][x] !== '.') buf[(my + y - bob) * CW + mx + x] = P32.y;
      }
      const [fx, fy] = st.facing;
      const ey = 3 + (fy > 0 ? 1 : fy < 0 ? -1 : 0) - bob;
      const ex = fx > 0 ? 1 : fx < 0 ? -1 : 0;
      buf[(my + ey) * CW + mx + 2 + ex] = P32.s;
      buf[(my + ey) * CW + mx + 5 + ex] = P32.s;
      ctx.putImageData(img, 0, 0);
    };

    const s = {};
    s.layout = () => {
      const w = frameEl.clientWidth || CW * 3;
      const k = clamp(Math.min(Math.floor(w / CW), Math.floor((innerHeight * 0.66) / CH)), 2, 8);
      sizeCanvas(cv, CW, CH, k);
      render();
    };
    s.tick = (t) => {
      if (st.path.length && t - st.lastStep > 95) {
        st.lastStep = t;
        const [nx, ny] = st.path.shift();
        st.facing = [nx - st.mind.x, ny - st.mind.y];
        st.mind.x = nx; st.mind.y = ny;
        afterStep();
        if (!st.path.length) arrive(); else render();
      }
      const b = Math.floor(t / 650) % 2 === 1;
      if (b !== st.blink) { st.blink = b; render(); }
      if (thoughtEl && thoughtEl.textContent && performance.now() - st.thoughtT > 5200) thoughtEl.textContent = '';
      return true;
    };
    s.motionChanged = () => { st.blink = false; render(); };
    updateCount();
    s.layout();
    register(el, s);
  };
  doc.querySelectorAll('[data-cell]').forEach(Cell);

  /* ================================================================== THE TREE
     Roots first, then mycelium, trunk, branches (lanes), leaves (rhythms, cycling through four seasons),
     senses, and one saffron growing tip. Growth follows scroll; the part being read lights up. */
  const Tree = (el) => {
    const cv = el.querySelector('.tree-canvas');
    const stage = el.querySelector('.tree-stage');
    const frameEl = el.querySelector('.tree-frame');
    if (!cv || !stage) return;
    const ctx = cv.getContext('2d');
    const parts = Array.from(el.querySelectorAll('.part'));
    const TW = 96, TH = 128, GY = 84;
    const R = rng(1990);
    const px = [];
    const add = (x, y, c, part, t, ph) => {
      x = Math.round(x); y = Math.round(y);
      if (x >= 0 && y >= 0 && x < TW && y < TH) px.push({ x, y, c, part, t, ph: ph || 0 });
    };
    const line = (x0, y0, x1, y1, fn) => {
      x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
      const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
      const n = Math.max(dx, -dy) || 1;
      let err = dx + dy, i = 0;
      for (;;) {
        fn(x0, y0, i / n, i);
        if (x0 === x1 && y0 === y1) break;
        const e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
        i++;
      }
    };

    // roots: the left one runs deeper than the right, like the mark
    const tips = [];
    const rootWalk = (x, y, dir, len, t0, t1, depth, col) => {
      let cx = x, cy = y;
      for (let i = 0; i < len; i++) {
        cy += 1;
        const r = R();
        if (r < 0.5) cx += dir; else if (r < 0.62) cx -= dir;
        add(cx, cy, col, 'roots', lerp(t0, t1, i / len));
        if (depth > 0 && i > 4 && R() < 0.13) {
          const tt = lerp(t0, t1, i / len);
          rootWalk(cx, cy, R() < 0.5 ? -1 : 1, Math.floor(len * (0.3 + R() * 0.3)), tt, lerp(tt, t1, 0.9), depth - 1, 'l');
        }
      }
      tips.push([cx, cy]);
    };
    rootWalk(47, GY, -1, 37, 0.02, 0.26, 2, 'g');
    rootWalk(49, GY, 1, 24, 0.02, 0.2, 2, 'g');
    rootWalk(48, GY, 0, 14, 0.05, 0.16, 1, 'l');

    // mycelium: dotted threads joining the root tips and running off to other trees
    tips.sort((a, b) => a[0] - b[0]);
    const thread = (a, b, t0, t1) => line(a[0], a[1], b[0], b[1], (x, y, f, i) => { if (i % 2 === 0) add(x, y, 'l', 'mycelium', lerp(t0, t1, f)); });
    for (let i = 0; i < tips.length - 1; i++) thread(tips[i], tips[i + 1], 0.26 + i * 0.01, 0.4);
    if (tips.length) {
      thread(tips[0], [0, clamp(tips[0][1] + 6, GY + 4, TH - 2)], 0.3, 0.42);
      thread(tips[tips.length - 1], [TW - 1, clamp(tips[tips.length - 1][1] - 4, GY + 4, TH - 2)], 0.3, 0.42);
    }

    // trunk
    const TOP = GY - 30;
    for (let y = GY; y >= TOP; y--) {
      const f = (GY - y) / (GY - TOP);
      const t = lerp(0.34, 0.47, f);
      add(47, y, 'g', 'trunk', t);
      add(48, y, 'l', 'trunk', t);
      if (f < 0.7) add(49, y, 'l', 'trunk', t);
      if (f < 0.25) add(46, y, 'l', 'trunk', t);
    }

    // branches: six lanes, each splitting twice, leaves at the tips
    const leaves = [];
    const branch = (x, y, ang, len, depth, t0, span) => {
      const x2 = x + Math.cos(ang) * len, y2 = y - Math.sin(ang) * len;
      const t1 = t0 + span;
      line(x, y, x2, y2, (bx, by, f) => {
        add(bx, by, 'g', 'branches', lerp(t0, t1, f));
        if (depth >= 2) add(bx, by + 1, 'l', 'branches', lerp(t0, t1, f));
      });
      if (depth === 0) { leaves.push([x2, y2, t1, 4 + Math.floor(R() * 3)]); return; }
      if (depth === 1) leaves.push([x2, y2, t1, 3]);
      branch(x2, y2, ang + 0.32 + R() * 0.28, len * 0.7, depth - 1, t1, span * 0.8);
      branch(x2, y2, ang - 0.32 - R() * 0.28, len * 0.66, depth - 1, t1, span * 0.8);
    };
    [[2.75, 15, TOP + 8], [2.3, 17, TOP + 4], [1.85, 16, TOP], [1.3, 16, TOP], [0.85, 17, TOP + 4], [0.4, 15, TOP + 8]]
      .forEach(([a, l, y]) => branch(48, y, a, l, 2, 0.47, 0.075));

    // leaves: rhythms, each pixel with its own season phase
    let top = { x: 48, y: TH };
    leaves.forEach(([lx, ly, lt, r]) => {
      for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) {
        const d = Math.sqrt(x * x + y * y);
        if (d > r + 0.3) continue;
        if (d > r - 1.2 && R() < 0.45) continue;
        const c = R() < 0.35 ? 'p' : 'c';
        const t = clamp(lt + 0.08 + (d / r) * 0.06 + R() * 0.04, 0.64, 0.86);
        add(lx + x, ly + y, c, 'rhythms', t, Math.floor(R() * 4));
        if (ly + y < top.y) top = { x: Math.round(lx + x), y: Math.round(ly + y) };
      }
    });
    // senses: a few bright points at the edge of the canopy
    const leafPx = px.filter((p) => p.part === 'rhythms');
    for (let i = 0; i < 8; i++) {
      const p = leafPx[Math.floor(R() * leafPx.length)];
      add(p.x + (R() < 0.5 ? -1 : 1), p.y - 1, 'b', 'senses', 0.86 + i * 0.008, i);
    }
    // the growing tip: one saffron pixel, the part that is never done
    add(top.x, top.y - 1, 'g', 'tip', 0.94);
    add(top.x, top.y - 2, 'y', 'tip', 0.96);

    const SEASON = ['p', 'c', 'l', 'm'];
    let progress = motion ? 0 : 1;
    let active = null;
    let lastDraw = 0, season = 0, senseBlink = 0;

    const draw = () => {
      if (journeyOn()) return;
      ctx.clearRect(0, 0, TW, TH);
      ctx.fillStyle = COLORS.under;
      ctx.fillRect(0, GY + 1, TW, TH - GY - 1);
      ctx.fillStyle = COLORS.moss;
      ctx.fillRect(0, GY, TW, 1);
      const p = motion ? progress : 1;
      for (const q of px) {
        if (q.t > p) continue;
        let c = q.c;
        if (q.part === 'rhythms') c = active === 'rhythms' ? (q.c === 'p' ? 'b' : 'p') : (motion ? SEASON[(q.ph + season) % 4] : q.c);
        else if (q.part === 'senses') { if (motion && (q.ph + senseBlink) % 5 === 0) c = 'l'; }
        else if (active === q.part && q.part !== 'tip') c = 'b';
        ctx.fillStyle = PAL[c];
        ctx.fillRect(q.x, q.y, 1, 1);
        if (q.part === 'senses' && active === 'senses') {
          ctx.fillRect(q.x - 1, q.y, 3, 1);
          ctx.fillRect(q.x, q.y - 1, 1, 3);
        }
      }
      if (active === 'tip' && p >= 0.96) {
        ctx.fillStyle = COLORS.bone;
        [[-2, 0], [2, 0], [0, -2], [0, 2]].forEach(([dx, dy]) => ctx.fillRect(top.x + dx, top.y - 2 + dy, 1, 1));
      }
    };

    const computeProgress = () => {
      const sticky = getComputedStyle(stage).position === 'sticky';
      const vh = innerHeight;
      let p;
      if (sticky) {
        const r = el.getBoundingClientRect();
        p = (vh * 0.9 - r.top) / (r.height * 0.62);
      } else {
        const r = stage.getBoundingClientRect();
        p = (vh - r.top) / (r.height + vh * 0.35);
      }
      return clamp(p, 0, 1);
    };

    const s = {};
    s.layout = () => {
      const w = frameEl.clientWidth || TW * 3;
      const k = clamp(Math.min(Math.floor(w / TW), Math.floor((innerHeight * 0.8) / TH)), 2, 6);
      sizeCanvas(cv, TW, TH, k);
      progress = computeProgress();
      draw();
    };
    s.onScroll = () => {
      if (!motion) return;
      const p = computeProgress();
      if (Math.abs(p - progress) > 0.002) { progress = p; draw(); }
    };
    s.tick = (t) => {
      if (journeyOn()) return true;
      if (t - lastDraw > 140) {
        lastDraw = t;
        season = Math.floor(t / 2200) % 4;
        senseBlink = Math.floor(t / 420);
        draw();
      }
      return true;
    };
    s.motionChanged = () => { progress = motion ? computeProgress() : 1; draw(); };
    s.journeyChanged = () => draw();

    const pio = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        active = e.target.dataset.part;
        parts.forEach((p) => p.classList.toggle('is-active', p === e.target));
        draw();
      });
    }, { rootMargin: '-42% 0px -42% 0px' });
    parts.forEach((p) => pio.observe(p));

    s.layout();
    register(el, s);
  };
  doc.querySelectorAll('[data-tree]').forEach(Tree);

  /* ================================================================== THE SKY
     Dusk to night as you scroll: a pale sun sets behind a treeline, clouds darken, stars come out,
     a moon rises, then aurora curtains in canopy and sprout greens with a single saffron thread.
     The sun has gone before the thread appears, so the sky only ever holds one saffron. */
  const Sky = (sec) => {
    const bg = sec.querySelector('.sky-bg');
    const cv = sec.querySelector('.sky-canvas');
    if (!bg || !cv) return;
    const ctx = cv.getContext('2d');
    const R = rng(4242);
    const stars = Array.from({ length: 320 }, () => ({ x: R(), y: R() * 0.82, th: 0.22 + R() * 0.5, ph: R() * 6.28, b: R() }));
    const clouds = Array.from({ length: 6 }, () => ({ x: R() * 1.3, y: 0.3 + R() * 0.32, w: 0.1 + R() * 0.12, h: 0.028 + R() * 0.02, sp: 0.000006 + R() * 0.00001 }));
    const RAMP = [P32.s, P32.u, P32.m, P32.c, P32.p];
    let cols = 0, rows = 0, img = null, buf = null, hills = [], pxs = 6;
    let p = 0, lastQ = -1, lastDraw = 0;

    const setPx = (x, y, c) => { if (x >= 0 && y >= 0 && x < cols && y < rows) buf[y * cols + x] = c; };
    const disc = (cx, cy, r, c, test) => {
      for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) {
        if (x * x + y * y <= r * r + r * 0.6 && (!test || test(x, y))) setPx(Math.round(cx + x), Math.round(cy + y), c);
      }
    };

    const progressNow = () => {
      const r = sec.getBoundingClientRect();
      return clamp(-r.top / Math.max(1, r.height - innerHeight), 0, 1);
    };

    const draw = (t) => {
      if (journeyOn() || !buf) return;
      const pp = motion ? p : (p < 0.34 ? 0.06 : p < 0.67 ? 0.5 : 1);
      t = motion ? t : 0;
      const dusk = 1 - pp;
      // sky, dithered through the brand ramp
      for (let y = 0; y < rows; y++) {
        const low = y / rows;
        const v = dusk * (0.55 + 3.5 * Math.pow(low, 1.7));
        for (let x = 0; x < cols; x++) {
          buf[y * cols + x] = RAMP[clamp(Math.floor(v + bayer(x, y)), 0, 4)];
        }
      }
      // stars
      for (const s of stars) {
        if (pp < s.th) continue;
        const sx = Math.floor(s.x * cols), sy = Math.floor(s.y * rows);
        let c = s.b > 0.86 ? P32.b : s.b > 0.5 ? P32.g : P32.l;
        if (motion && Math.sin(t * 0.0021 + s.ph * 7) > 0.93) c = P32.m;
        setPx(sx, sy, c);
        if (s.b > 0.975) { setPx(sx - 1, sy, P32.l); setPx(sx + 1, sy, P32.l); setPx(sx, sy - 1, P32.l); setPx(sx, sy + 1, P32.l); }
      }
      // aurora: a sinuous ribbon with rays hanging up from its bright lower edge
      const a = smooth(0.46, 0.86, pp);
      const sunGone = pp > 0.3;
      if (a > 0) {
        let prevY = null;
        for (let x = 0; x < cols; x++) {
          const yb = rows * (0.36 + 0.07 * Math.sin(x * 0.035 + t * 0.0003) + 0.03 * Math.sin(x * 0.09 - t * 0.0002));
          const L = rows * (0.14 + 0.09 * (0.5 + 0.5 * Math.sin(x * 0.05 + t * 0.00025 + 1)) + 0.05 * (0.5 + 0.5 * Math.sin(x * 0.013 + 2)));
          const streak = 0.82 + 0.18 * Math.sin(x * 1.3 + 3 * Math.sin(t * 0.0007 + x * 0.1));
          for (let y = Math.max(0, Math.floor(yb - L)); y <= Math.min(rows - 1, Math.floor(yb)); y++) {
            const d = (yb - y) / L;
            const k = a * Math.pow(1 - d, 1.4) * streak;
            const th = bayer(x, y);
            if (k > 0.72 + th * 0.22) buf[y * cols + x] = P32.p;
            else if (k > 0.1 + th * 0.55) buf[y * cols + x] = P32.c;
          }
          // the single saffron thread along the ribbon's lower edge
          if (a > 0.35 && sunGone && x > cols * 0.1 && x < cols * 0.9) {
            const yt = Math.round(yb) + 1;
            if (prevY !== null && Math.abs(yt - prevY) > 1) {
              const s0 = Math.min(yt, prevY), s1 = Math.max(yt, prevY);
              for (let yy = s0 + 1; yy < s1; yy++) setPx(x, yy, P32.y);
            }
            setPx(x, yt, P32.y);
            prevY = yt;
          }
        }
      }
      // moon
      const mp = smooth(0.28, 0.9, pp);
      const mr = Math.max(4, Math.round(Math.min(cols, rows) * 0.045));
      if (mp > 0) {
        const mx = Math.round(cols * 0.8), my = Math.round(lerp(rows * 1.05, rows * 0.2, mp));
        disc(mx, my, mr, P32.b);
        setPx(mx - Math.round(mr * 0.3), my - Math.round(mr * 0.2), P32.g);
        setPx(mx + Math.round(mr * 0.35), my + Math.round(mr * 0.3), P32.g);
        setPx(mx + Math.round(mr * 0.35) + 1, my + Math.round(mr * 0.3), P32.g);
        setPx(mx - Math.round(mr * 0.1), my + Math.round(mr * 0.5), P32.g);
      }
      // sun: pale, pixelated, setting
      const horizon = rows - Math.round(rows * 0.12);
      const sr = Math.max(5, Math.round(Math.min(cols, rows) * 0.06));
      const sy = Math.round(horizon - sr * 0.35 + pp * rows * 0.7);
      const sx = Math.round(cols * 0.64);
      if (sy - sr < horizon) {
        if (pp < 0.3) disc(sx, sy, sr + 3, P32.p, (x, y) => (x * x + y * y > sr * sr) && bayer(x + sx, y + sy) > 0.45);
        disc(sx, sy, sr, P32.b);
      }
      // clouds: a few round puffs on a flat base
      for (const c of clouds) {
        const cx = ((c.x + t * c.sp) % 1.4 - 0.2) * cols;
        const base = Math.round(c.y * rows), w = c.w * cols, h = Math.max(2, c.h * rows);
        const body = pp < 0.45 ? P32.m : P32.u;
        const puffs = [[-0.42, 1.1], [-0.1, 1.7], [0.28, 1.35], [0.5, 0.9]];
        for (const [ox, rr] of puffs) {
          const pr = Math.max(2, Math.round(h * rr)), pcx = Math.round(cx + ox * w);
          for (let y = -pr; y <= 0; y++) for (let x = -pr; x <= pr; x++) {
            if (x * x + y * y <= pr * pr + pr * 0.5) setPx(pcx + x, base + y, body);
          }
        }
        if (pp < 0.3) {
          for (let x = Math.round(cx - w * 0.42 - h); x <= Math.round(cx + w * 0.5 + h * 0.6); x++) {
            if ((x & 1) === 0 && x >= 0 && x < cols && base >= 0 && base < rows && buf[base * cols + x] === body) setPx(x, base, P32.l);
          }
        }
      }
      // treeline
      for (let x = 0; x < cols; x++) {
        for (let y = rows - hills[x]; y < rows; y++) setPx(x, y, P32.s);
      }
      ctx.putImageData(img, 0, 0);
    };

    const s = {};
    s.layout = () => {
      pxs = innerWidth < 600 ? 5 : 6;
      cols = Math.ceil(bg.clientWidth / pxs);
      rows = Math.ceil(bg.clientHeight / pxs);
      if (!cols || !rows) return;
      cv.width = cols; cv.height = rows;
      cv.style.width = cols * pxs + 'px';
      cv.style.height = rows * pxs + 'px';
      img = ctx.createImageData(cols, rows);
      buf = new Uint32Array(img.data.buffer);
      const H = rng(99);
      hills = [];
      let h = rows * 0.1;
      for (let x = 0; x < cols; x++) {
        h += (H() - 0.5) * 1.6;
        h = clamp(h, rows * 0.07, rows * 0.15);
        const tree = H() < 0.12 ? Math.floor(H() * 4) + 2 : 0;
        hills.push(Math.round(h) + tree);
      }
      p = progressNow();
      draw(performance.now());
    };
    s.onScroll = () => {
      const np = progressNow();
      if (motion) { p = np; if (!s.visible) return; draw(performance.now()); return; }
      const q = np < 0.34 ? 0 : np < 0.67 ? 1 : 2;
      p = np;
      if (q !== lastQ) { lastQ = q; draw(0); }
    };
    s.tick = (t) => {
      if (journeyOn()) return true;
      if (t - lastDraw > 66) { lastDraw = t; draw(t); }
      return true;
    };
    s.motionChanged = () => { lastQ = -1; p = progressNow(); draw(performance.now()); };
    s.journeyChanged = () => draw(performance.now());
    s.layout();
    register(sec, s);
  };
  doc.querySelectorAll('.scene-sky').forEach(Sky);

  /* ================================================================== THE ANCESTRAL PLANE
     987 real commits on a sunflower spiral, first at the centre, newest at the rim; thirteen lane
     constellations around it. The slider and the field notes replay the history day by day. */
  const Plane = (el) => {
    const D = window.BODHI_ANCESTRY;
    const cv = el.querySelector('.plane-canvas');
    const frameEl = el.querySelector('.plane-frame');
    const range = el.querySelector('[data-plane-range]');
    const dateEl = el.querySelector('[data-plane-date]');
    const statEl = el.querySelector('[data-plane-stat]');
    const playBtn = el.querySelector('[data-plane-play]');
    if (!D || !cv || !range) return;
    const ctx = cv.getContext('2d');
    const kinds = D.kinds;
    const N = kinds.length;
    const cday = new Array(N);
    let idx = 0;
    D.days.forEach(([d, n]) => { for (let i = 0; i < n; i++) cday[idx++] = d; });
    const MAXD = 130;
    const START = Date.UTC(2026, 4, 21);
    const iso = (d) => new Date(START + d * 864e5).toISOString().slice(0, 10);
    const KC = { w: 'b', b: 'p', o: 'g', f: 'r', a: 'l' };
    const GA = Math.PI * (3 - Math.sqrt(5));
    // co-author lines per lane; null = on record, not counted that way
    const LANES = [224, 98, 63, 15, 11, 7, 5, null, null, null, null, null, null];
    const SHAPES = [
      [[0, 0], [4, -2], [8, -1], [10, 3], [6, 5]],
      [[0, 0], [3, 3], [7, 2], [9, -2]],
      [[0, 0], [2, -4], [6, -5], [8, -1], [5, 2]],
      [[0, 0], [5, 1], [9, -2]]
    ];
    let cols = 0, rows = 0, pts = [], lanePos = [], bgStars = [];
    let day = MAXD, anim = null, played = false;

    const layoutGeometry = () => {
      const w = frameEl ? frameEl.clientWidth : 600;
      const portrait = w < 560;
      cols = portrait ? 112 : 176;
      rows = portrait ? 150 : 112;
      const k = clamp(Math.min(Math.floor(w / cols), Math.floor((innerHeight * 0.78) / rows)), 2, 6);
      sizeCanvas(cv, cols, rows, k);
      const cx = portrait ? 56 : 88, cy = portrait ? 56 : 56, R = 52;
      const c = R / Math.sqrt(N);
      pts = kinds.split('').map((_, i) => {
        const r = c * Math.sqrt(i + 0.5), a = i * GA;
        return [Math.round(cx + r * Math.cos(a)), Math.round(cy + r * Math.sin(a))];
      });
      lanePos = LANES.map((_, i) => {
        if (portrait) {
          const row = i < 7 ? 0 : 1, col = i < 7 ? i : i - 7;
          return [4 + col * 15 + (row ? 7 : 0), 120 + row * 16];
        }
        const left = i % 2 === 0, j = Math.floor(i / 2);
        return [left ? 6 + (j % 2) * 8 : 150 - (j % 2) * 8, 10 + j * 15];
      });
      const r = rng(31);
      bgStars = Array.from({ length: 70 }, () => [Math.floor(r() * cols), Math.floor(r() * rows), r()]);
    };

    const draw = () => {
      if (journeyOn()) return;
      ctx.fillStyle = COLORS.soil;
      ctx.fillRect(0, 0, cols, rows);
      bgStars.forEach(([x, y, b]) => { ctx.fillStyle = b > 0.8 ? COLORS.lichen : COLORS.moss; ctx.fillRect(x, y, 1, 1); });
      // lanes
      LANES.forEach((count, i) => {
        const [ox, oy] = lanePos[i];
        const shape = SHAPES[i % SHAPES.length];
        ctx.fillStyle = COLORS.moss;
        for (let j = 0; j < shape.length - 1; j++) {
          const [ax, ay] = shape[j], [bx, by] = shape[j + 1];
          const n = Math.max(Math.abs(bx - ax), Math.abs(by - ay));
          for (let s = 1; s < n; s += 2) ctx.fillRect(Math.round(ox + ax + ((bx - ax) * s) / n), Math.round(oy + ay + ((by - ay) * s) / n), 1, 1);
        }
        shape.forEach(([sx, sy], j) => {
          const x = ox + sx, y = oy + sy;
          const big = j === 0 && count !== null && count >= 50;
          ctx.fillStyle = count === null ? COLORS.lichen : (j === 0 ? COLORS.bone : COLORS.sage);
          ctx.fillRect(x, y, 1, 1);
          if (big) {
            ctx.fillRect(x - 1, y, 3, 1);
            ctx.fillRect(x, y - 1, 1, 3);
            if (count >= 200) { ctx.fillStyle = COLORS.sage; ctx.fillRect(x - 2, y, 1, 1); ctx.fillRect(x + 2, y, 1, 1); ctx.fillRect(x, y - 2, 1, 1); ctx.fillRect(x, y + 2, 1, 1); }
          }
        });
      });
      // commits
      let newest = -1;
      for (let i = 0; i < N; i++) if (cday[i] <= day) newest = i;
      for (let i = 0; i < N; i++) {
        const lit = cday[i] <= day;
        ctx.fillStyle = i === newest ? COLORS.saffron : lit ? PAL[KC[kinds[i]]] : COLORS.moss;
        ctx.fillRect(pts[i][0], pts[i][1], 1, 1);
      }
    };

    const stats = () => {
      let n = 0, auto = 0;
      for (let i = 0; i < N; i++) if (cday[i] <= day) { n++; if (kinds[i] === 'a') auto++; }
      return { n, auto };
    };
    const syncText = (announceIt, note) => {
      const d = iso(day);
      const { n, auto } = stats();
      range.value = String(day);
      range.setAttribute('aria-valuetext', d + ', ' + n + ' commits');
      if (dateEl) dateEl.textContent = d;
      if (statEl) statEl.textContent = n + ' commits so far · ' + auto + ' autosaves · day ' + day + ' of ' + MAXD;
      if (announceIt) announce('By ' + d + ': ' + n + ' commits, ' + auto + ' of them autosaves.' + (note ? ' ' + note : ''));
    };
    const setDay = (d, announceIt, note) => {
      day = clamp(Math.round(d), 0, MAXD);
      draw();
      syncText(announceIt, note);
    };

    range.addEventListener('input', () => { anim = null; played = true; setDay(+range.value, false); });
    range.addEventListener('change', () => setDay(+range.value, true));

    const play = () => {
      played = true;
      if (!motion) { setDay(MAXD, true); return; }
      anim = { t0: 0 };
      setDay(0, false);
      kick();
    };
    if (playBtn) playBtn.addEventListener('click', play);

    // field notes become buttons that move the plane to their date
    const fnBtns = [];
    el.querySelectorAll('[data-fieldnotes] li').forEach((li) => {
      const b = doc.createElement('button');
      b.type = 'button';
      b.className = 'fn-btn';
      while (li.firstChild) b.appendChild(li.firstChild);
      li.appendChild(b);
      li.classList.add('has-btn');
      fnBtns.push(b);
      b.addEventListener('click', () => {
        anim = null;
        played = true;
        fnBtns.forEach((x) => x.removeAttribute('aria-current'));
        b.setAttribute('aria-current', 'true');
        const t = b.querySelector('.fn-t');
        setDay(+li.dataset.day, true, t ? t.textContent : '');
      });
    });

    const s = {};
    s.layout = () => { layoutGeometry(); draw(); };
    s.tick = (t) => {
      if (!anim) return false;
      if (!anim.t0) anim.t0 = t;
      const f = clamp((t - anim.t0) / 5200, 0, 1);
      const d = Math.round(f * f * MAXD);
      if (d !== day) setDay(d, false);
      if (f >= 1) { anim = null; syncText(true); return false; }
      return true;
    };
    s.onShow = () => { if (!played && motion && !journeyOn()) play(); };
    s.motionChanged = (m) => { if (!m && anim) { anim = null; setDay(MAXD, false); } };
    s.journeyChanged = () => draw();
    s.layout();
    syncText(false);
    register(el, s);
  };
  doc.querySelectorAll('[data-plane]').forEach(Plane);

  /* ================================================================== THE SUMMARY THAT UNPACKS
     A one-line, model-style summary of one of Jaron's passages. Press it and it unpacks in place to
     his full words, with the phrases the summary lost highlighted. Summaries drift; the full text doesn't. */
  const words = (node) => (node.textContent.match(/[A-Za-z0-9'’-]+/g) || []).length;
  doc.querySelectorAll('[data-unpack]').forEach((box) => {
    const btn = box.querySelector('[data-unpack-btn]');
    const full = box.querySelector('[data-unpack-full]');
    const sum = box.querySelector('.unpack-sum-text');
    const quote = box.querySelector('.unpack-quote');
    if (!btn || !full) return;
    const cs = box.querySelector('[data-unpack-count="sum"]');
    const cf = box.querySelector('[data-unpack-count="full"]');
    if (cs && sum) cs.textContent = String(words(sum));
    if (cf && quote) cf.textContent = String(words(quote));
    btn.hidden = false;
    full.hidden = true;
    btn.addEventListener('click', () => {
      const open = btn.getAttribute('aria-expanded') !== 'true';
      btn.setAttribute('aria-expanded', String(open));
      full.hidden = !open;
      box.classList.toggle('is-open', open);
      if (open) {
        const lost = box.querySelectorAll('.unpack-quote mark').length;
        announce('Unpacked in full, ' + (cf ? cf.textContent : '') + ' words. ' + lost + ' passages the summary lost are highlighted.');
      }
    });
  });

  /* ================================================================== small things */
  // copy buttons on install commands
  doc.querySelectorAll('[data-copy]').forEach((box) => {
    const pre = box.querySelector('pre');
    if (!pre) return;
    const b = doc.createElement('button');
    b.type = 'button';
    b.className = 'btn btn-quiet btn-sm copy-btn';
    b.textContent = 'Copy';
    b.setAttribute('aria-label', 'Copy these commands');
    let t = 0;
    b.addEventListener('click', async () => {
      const text = pre.innerText.trim();
      let ok = false;
      try {
        await navigator.clipboard.writeText(text);
        ok = true;
      } catch (e) {
        const sel = getSelection();
        const r = doc.createRange();
        r.selectNodeContents(pre);
        sel.removeAllRanges();
        sel.addRange(r);
        try { ok = doc.execCommand('copy'); } catch (e2) { ok = false; }
      }
      b.textContent = ok ? 'Copied' : 'Selected';
      announce(ok ? 'Commands copied.' : 'Commands selected. Press your copy shortcut.');
      clearTimeout(t);
      t = setTimeout(() => { b.textContent = 'Copy'; }, 2200);
    });
    box.appendChild(b);
  });

  // scene rail: mark the scene in view
  const railLinks = new Map(Array.from(doc.querySelectorAll('[data-rail]')).map((a) => [a.dataset.rail, a]));
  if (railLinks.size) {
    const rio = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        railLinks.forEach((a) => a.removeAttribute('aria-current'));
        const a = railLinks.get(e.target.id);
        if (a) a.setAttribute('aria-current', 'true');
      });
    }, { rootMargin: '-45% 0px -54% 0px' });
    doc.querySelectorAll('[data-scene]').forEach((sEl) => rio.observe(sEl));
  }

  // scenes menu (narrow screens): close on choice or Escape
  const menu = doc.querySelector('.scenes-menu');
  if (menu) {
    menu.addEventListener('click', (e) => { if (e.target.closest('a')) menu.open = false; });
    menu.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && menu.open) { menu.open = false; menu.querySelector('summary').focus(); }
    });
  }

  // maker's mark slot: Jaron's JF monogram appears when assets/marks/jf.svg exists; until then, his name
  const jf = doc.querySelector('[data-jf]');
  if (jf) {
    const probe = new Image();
    probe.onload = () => jf.classList.add('has-mark');
    probe.src = 'assets/marks/jf.svg';
  }

  kick();
})();
