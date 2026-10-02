// Quality: a device tier chosen once, and an adaptive device-pixel ratio that
// drops when frames run over budget and creeps back when there is headroom.
export class Quality {
  constructor(lockDpr) {
    const coarse = matchMedia('(pointer: coarse)').matches;
    const small = Math.min(screen.width, screen.height) < 700;
    const cores = navigator.hardwareConcurrency || 4;
    this.tier = coarse || small || cores < 4 ? 'low' : 'high';
    this.samples = this.tier === 'high' ? 4 : 0;
    this.max = Math.min(window.devicePixelRatio || 1, 1.5);
    this.min = 0.6;
    this.locked = typeof lockDpr === 'number' && lockDpr > 0;
    this.dpr = this.locked ? lockDpr : this.max;
    this.ema = 16.7; this.over = 0; this.under = 0;
  }
  // Feed one frame time (ms). Returns true when the resolution changed.
  sample(ms) {
    if (ms > 250 || ms <= 0) return false; // tab switches and first frames
    this.ema += (ms - this.ema) * 0.06;
    if (this.locked) return false;
    if (this.ema > 21) { this.over += ms; this.under = 0; } else if (this.ema < 17.5) { this.under += ms; this.over = 0; } else { this.over = 0; this.under = 0; }
    if (this.over > 800 && this.dpr > this.min) {
      this.dpr = Math.max(this.min, +(this.dpr * 0.8).toFixed(3)); this.over = 0; this.ema = 16.7; return true;
    }
    if (this.under > 5000 && this.dpr < this.max) {
      this.dpr = Math.min(this.max, +(this.dpr * 1.12).toFixed(3)); this.under = 0; return true;
    }
    return false;
  }
}
