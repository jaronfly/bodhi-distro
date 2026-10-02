// Brand palette (see the journey contract). Hex is sRGB; shaders work in linear light.
export const HEX = {
  soil: 0x17231b, under: 0x1f2c24, moss: 0x2e3b33, lichen: 0x8a968d, sage: 0xb8c2ba,
  bone: 0xf2eee4, canopy: 0x2e6b45, sprout: 0x8bcb8b, saffron: 0xe8982a, clay: 0xd9674f,
};

const toLin = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
export const srgb = (hex) => [((hex >> 16) & 255) / 255, ((hex >> 8) & 255) / 255, (hex & 255) / 255];
export const lin = (hex) => srgb(hex).map(toLin);

const f = (v) => v.toFixed(5);
const v3 = (a) => `vec3(${f(a[0])},${f(a[1])},${f(a[2])})`;

// GLSL constants: linear (SOIL) and exact sRGB (SOIL_S) for post-tonemap brand pixels.
export const PALETTE_GLSL = Object.keys(HEX).map((k) => {
  const n = k.toUpperCase();
  return `const vec3 ${n} = ${v3(lin(HEX[k]))};\nconst vec3 ${n}_S = ${v3(srgb(HEX[k]))};`;
}).join('\n');
