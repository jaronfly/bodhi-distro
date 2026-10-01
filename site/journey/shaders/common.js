// Shared GLSL: integer hashes, value noise, fbm, Voronoi with border distance,
// the ACES fit, and the sky-view lookup used for aerial perspective.
import { PALETTE_GLSL } from '../core/palette.js';

export const COMMON = /* glsl */`
#define PI 3.14159265
${PALETTE_GLSL}
float sat(float x){ return clamp(x, 0.0, 1.0); }
vec3 sat(vec3 x){ return clamp(x, 0.0, 1.0); }
uint hu(uint x){ x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16; return x; }
float h1(uint x){ return float(hu(x)) * 2.3283064e-10; }
float h21(ivec2 p){ return h1(uint(p.x) * 1597334677U ^ uint(p.y) * 3812015801U); }
vec2 h22(ivec2 p){ uint h = hu(uint(p.x) * 1597334677U ^ uint(p.y) * 3812015801U); return vec2(float(h & 0xffffU), float(h >> 16)) * (1.0 / 65535.0); }
float h31(ivec3 p){ return h1(uint(p.x) * 1597334677U ^ uint(p.y) * 3812015801U ^ uint(p.z) * 2798796415U); }
float vnoise(vec2 x){
  vec2 i = floor(x), f = fract(x); ivec2 n = ivec2(i);
  vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  float a = h21(n), b = h21(n + ivec2(1, 0)), c = h21(n + ivec2(0, 1)), d = h21(n + ivec2(1, 1));
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}
float vnoise3(vec3 x){
  vec3 i = floor(x), f = fract(x); ivec3 n = ivec3(i);
  vec3 u = f * f * (3.0 - 2.0 * f);
  float a = h31(n), b = h31(n + ivec3(1,0,0)), c = h31(n + ivec3(0,1,0)), d = h31(n + ivec3(1,1,0));
  float e = h31(n + ivec3(0,0,1)), g = h31(n + ivec3(1,0,1)), k = h31(n + ivec3(0,1,1)), l = h31(n + ivec3(1,1,1));
  return mix(mix(mix(a,b,u.x), mix(c,d,u.x), u.y), mix(mix(e,g,u.x), mix(k,l,u.x), u.y), u.z);
}
float fbm(vec2 p){ float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++){ s += a * vnoise(p); p = mat2(1.6, 1.2, -1.2, 1.6) * p; a *= 0.5; } return s; }
float fbm3(vec2 p){ float s = 0.0, a = 0.5; for (int i = 0; i < 3; i++){ s += a * vnoise(p); p = mat2(1.6, 1.2, -1.2, 1.6) * p; a *= 0.5; } return s; }
// Voronoi (after Inigo Quilez): x = distance to nearest site, y = distance to the
// cell border, zw = offset from the pixel to its site. id receives the cell index.
vec4 voronoi(vec2 x, out ivec2 id){
  ivec2 n = ivec2(floor(x)); vec2 f = fract(x);
  vec2 mg = vec2(0.0), mr = vec2(0.0); float md = 8.0;
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++){
    vec2 g = vec2(float(i), float(j)); vec2 o = 0.1 + 0.8 * h22(n + ivec2(i, j));
    vec2 r = g + o - f; float d = dot(r, r);
    if (d < md){ md = d; mr = r; mg = g; }
  }
  float bd = 8.0;
  for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++){
    vec2 g = mg + vec2(float(i), float(j)); vec2 o = 0.1 + 0.8 * h22(n + ivec2(g));
    vec2 r = g + o - f;
    if (dot(mr - r, mr - r) > 1e-5) bd = min(bd, dot(0.5 * (mr + r), normalize(r - mr)));
  }
  id = n + ivec2(mg);
  return vec4(sqrt(md), bd, mr);
}
vec3 aces(vec3 x){ return sat((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)); }
vec3 toSrgb(vec3 c){ return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c)); }
`;

// Sky-view LUT lookup (the LUT is made by sky.js with a single-scattering raymarch).
// Returns radiance for a unit sun; callers multiply by the sun's intensity.
export const SKYLUT = /* glsl */`
uniform sampler2D uSkyLut;
uniform vec3 uSunDir;
uniform float uSunI;
uniform vec3 uNightSky;
vec3 skyLut(vec3 d){
  float el = asin(clamp(d.y, -1.0, 1.0));
  float az = atan(d.z, d.x) - atan(uSunDir.z, uSunDir.x);
  az = abs(mod(az + PI, 2.0 * PI) - PI);
  float v = 0.5 + 0.5 * sign(el) * sqrt(abs(el) / (0.5 * PI));
  return texture2D(uSkyLut, vec2(az / PI, v)).rgb * uSunI + uNightSky * (0.35 + 0.65 * sat(1.0 - d.y));
}
// Aerial perspective: blend toward the sky radiance along the view ray (exponential
// fog with the LUT as in-scattered colour; an approximation of the real integral).
vec3 aerial(vec3 col, vec3 wpos, float density){
  vec3 v = wpos - cameraPosition; float d = length(v);
  vec3 dir = v / d; dir.y = max(dir.y, 0.02);
  float f = 1.0 - exp(-d * density);
  return mix(col, skyLut(normalize(dir)), f);
}
`;
