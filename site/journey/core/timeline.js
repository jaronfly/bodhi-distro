// Scroll timeline. Reads the [data-scene] sections and turns native scroll into
// u = sceneIndex + progress (DOM order) and c = the canonical journey position.
// Unknown ids hold the nearest known keyframe; missing ids are simply absent.

export const CANON = { soil: 0, roots: 1, cell: 2, 'to-be': 3, tree: 4, sky: 5, ancestors: 6, questions: 7, receipts: 8, workbench: 9, plant: 10, access: 11 };
export const CANON_IDS = Object.keys(CANON);

export class Timeline {
  constructor() {
    this.els = []; this.ids = []; this.base = [];
    this.index = 0; this.scene = null; this.progress = 0; this.u = 0; this.c = 0;
    this.past = false; this.collect();
  }

  collect() {
    const list = [...document.querySelectorAll('[data-scene], section.scene[id]')];
    this.els = list.filter((el) => !list.some((o) => o !== el && o.contains(el)));
    this.ids = this.els.map((el) => el.dataset.scene || el.id);
    this.base = this.ids.map((id) => (id in CANON ? CANON[id] : null));
  }

  // Canonical position for DOM scene i at progress p.
  canonical(i, p) {
    const b = this.base;
    if (b[i] !== null && b[i] !== undefined) return b[i] + p;
    for (let j = i - 1; j >= 0; j--) if (b[j] !== null) return b[j] + 1;
    for (let j = i + 1; j < b.length; j++) if (b[j] !== null) return b[j];
    return 0;
  }

  update() {
    const n = this.els.length;
    if (!n) { this.scene = null; this.past = false; return; }
    const line = window.innerHeight * 0.5;
    let i = 0, top = 0, h = 1, lastBottom = 0;
    for (let k = 0; k < n; k++) {
      const r = this.els[k].getBoundingClientRect();
      if (k === 0 || r.top <= line) { i = k; top = r.top; h = r.height; }
      if (k === n - 1) lastBottom = r.bottom;
    }
    let p = (line - top) / Math.max(1, h);
    if (i === 0) {
      // The hero starts at progress 0 at scroll 0, whatever its height.
      const line0 = line - (top + window.scrollY);
      if (line0 > 0) p = (line - top - line0) / Math.max(1, h - line0);
    }
    p = p < 0 ? 0 : p > 1 ? 1 : p;
    this.index = i; this.scene = this.ids[i]; this.progress = p;
    this.u = i + p; this.c = this.canonical(i, p);
    this.past = lastBottom < 0;
  }
}
