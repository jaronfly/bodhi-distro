// Bodhi journey layer: entry point.
// Decides whether the 3D layer can run here, and only then loads it. When it
// cannot (no #journey, no WebGL2, a software-only GPU, Save-Data, very little
// memory) it does nothing and the page keeps its own 2D scene art.
//
// Test and review switches (query string): ?journey=force allows software GL,
// ?jdpr=1 locks the device-pixel ratio.

function boot() {
  const mount = document.getElementById('journey');
  if (!mount) return;
  const nav = navigator;
  if (nav.connection && nav.connection.saveData) return;
  if (typeof nav.deviceMemory === 'number' && nav.deviceMemory < 2) return;
  const q = new URLSearchParams(location.search);
  const canvas = document.createElement('canvas');
  let gl = null;
  try {
    gl = canvas.getContext('webgl2', {
      alpha: false, antialias: false, depth: true, stencil: false, premultipliedAlpha: true,
      powerPreference: 'high-performance', failIfMajorPerformanceCaveat: q.get('journey') !== 'force',
    });
  } catch (e) { gl = null; }
  if (!gl) return;
  const dpr = parseFloat(q.get('jdpr'));
  import('./core/stage.js')
    .then((m) => m.start(mount, canvas, gl, { dpr: dpr > 0 ? dpr : undefined }))
    .catch((err) => {
      document.documentElement.classList.remove('journey-on');
      if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
      console.warn('[journey] off:', err && err.message);
    });
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
else boot();
