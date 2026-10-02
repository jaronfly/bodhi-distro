# The journey layer

A fixed WebGL2 canvas behind the Bodhi landing page. One continuous camera, keyed to the page's scenes, goes from a seed in the soil into a single leaf cell, back out to the tree, up into the sky and the ancestral plane, and back down to a new seed. The canvas is `aria-hidden`. All of the meaning lives in the page's text, so the layer is decoration and the page reads the same without it.

Built by Claude, subagent, cloud session.

## How it mounts

It follows the integration contract:

- `index.html` has `<div id="journey" aria-hidden="true"></div>` as the first child of `<body>` and `<script type="module" src="journey/journey.js"></script>` before `</body>`. The page's CSS makes `#journey` fixed, full-viewport and `pointer-events:none`.
- `journey.js` is a small entry. It checks for `#journey`, Save-Data, `deviceMemory < 2`, and a WebGL2 context that isn't software-only (`failIfMajorPerformanceCaveat`). Only if all of those pass does it load the rest, including three.js. Otherwise it does nothing, and the page keeps its own 2D scene art.
- After the first rendered frame it adds `html.journey-on`. If the context is lost and not restored within 2.5 s, it removes the class again, so the 2D art comes back.
- Scroll stays native. Each scroll or resize, throttled to one per animation frame, measures the `[data-scene]` sections and computes `u = sceneIndex + progress`, with progress measured where the viewport's middle line crosses the section. The hero is rescaled so it starts at 0 at the top of the page. A `journey:scene` event fires when the scene changes. `window.BodhiJourney` exposes `{ u, scene, still, progress }`, plus `frames`, `dpr`, `frameMs` and `snap()` for debugging and tests.
- Scene ids map to a canonical timeline: `soil roots cell to-be tree sky ancestors questions receipts workbench plant access`. An unknown id holds the nearest known keyframe (the end of the previous known scene). Missing ids are skipped.
- The page's replay slider, `[data-plane-range]`, drives the commit spiral in the ancestral plane if it is present.

## Scene by scene

| Scene | What the layer does |
|---|---|
| soil | Pre-dawn and near-dark. The camera looks at a cut face of layered soil, with grass silhouetted on the soil line. One Saffron pixel, the seed, lights the grains around it. As you scroll, it splits, a pale root goes down first, and a hooked shoot pushes up through the soil. |
| roots | The shoot opens its cotyledons and becomes a sapling. Below the soil line, a root system grows against the glass and lights up as a graph in three stages. First the taproot (persistence). Then the laterals, with pixel nodes and pulses running along them (continuity). Then dotted mycorrhizal links between root tips that were never connected (rapport). |
| cell | The camera flies to one leaf of the sapling and falls in. The zoom is continuous on a log scale. It passes the midrib and secondary veins, then two finer vein networks, then a lattice of cells (Voronoi membranes, drifting cytoplasm, chloroplasts circling the cell). It stops in one cell, whose wall band turns into quilted padding: the padded cell. While the page's game is on screen, the centre of the frame stays dark and calm. At the end, the nucleus is sampled into an 11×10 grid of pixels, and the pixels resolve into the Bodhi mark: whole pixels, exactly Bone on Soil. |
| to-be | The mark's 74 pixels fly out to become nodes. The camera pulls back while the graph grows outward from the seed, until the nodes are the whole tree and its roots seen as a network. The tree nodes read the live branch simulation, so the graph sways. |
| tree | The tree is the anchor, on a small landscape with a treeline and hills. The leaves grow in with scroll, and the seasons cycle across the scene. Spring brings light-green buds, summer a full canopy, and autumn leaves turning Clay and ochre (a few Saffron) that let go and fall with physics. Winter is bare, with snow on the ground and branches. Golden-hour light comes through the leaves. |
| sky | Late afternoon becomes sunset, dusk and night, under a physically based sky. The clouds are lit from below after the sun sets. The moon rises and is phase-lit by the real sun direction. Stars come out, and an aurora curtain in Sprout and Canopy, with a thin Saffron hem, rises over the bare winter tree. |
| ancestors | The camera rises off the ground into the ancestral plane. It is a golden-angle spiral with one pixel per real commit from `window.BODHI_ANCESTRY`. The first commit sits at the centre and the newest, in Saffron, at the rim. Each pixel is coloured by kind: build is Sprout, fix Clay, write Bone, other Lichen, autosave Moss. Thirteen faint constellations sit around the spiral, and behind it a disc of 123,278 dim points echoes the size of the memory graph. |
| questions, receipts, workbench | These scenes are calm and low-contrast. The camera comes down far from the tree, so the tree is small on the horizon. Each scene has its own keyframe, while the blue hour turns slowly toward dawn and the clouds drift. The middle band of the viewport is compressed toward Soil, so dense text reads cleanly. |
| plant | Back to earth at dawn. The camera flies to the tree. The ground in front of it peels back to the cut face, showing the grown tree's root graph, and the camera drops below the soil line to one new Saffron seed: the same framing as the hero. The loop closes. |
| access | Holds the plant frame, dimmed. |

## Real simulation and approximations

| Part | What it is |
|---|---|
| Sky | **Real.** Rayleigh, Mie and ozone single scattering, raymarched (20 view steps × 6 light steps) into a 128×96 sky-view LUT whenever the sun moves. The same model runs on the CPU for the colour of sunlight reaching the ground and the clouds. The multiple-scattering term is a crude isotropic boost, which is an approximation. |
| Soil cut face | **Real raymarch** against a height field (relief mapping, 12 steps and a bisection), with a 4-tap soft shadow toward the seed's light. |
| Branch sway | **Real dynamics.** Each branch is a 2-DOF damped spring on its parent, with natural frequency, damping and gain by branch order. A gusty wind field travels through the crown and drives it. The hierarchy propagates the motion. |
| Falling leaves | **Real dynamics.** Each leaf is a rigid thin plate under gravity, with quadratic drag split into normal and tangential parts, and a pitching torque that turns it broadside to the relative wind. Under-damped, it flutters and glides. Leaves land, lie flat and stay until winter. The pool is fixed and recycles the oldest leaves. |
| Root and branch growth | **Procedural growth.** Stochastic branching with gravitropism and phototropism, golden-angle azimuths, and reveal by arc length. It is not a resource-competition simulation. |
| Leaf flutter on the tree | Approximation: a per-leaf oscillator about the petiole, scaled by the wind. |
| Grass | Approximation: kinematic sway from a travelling gust. |
| Clouds | Approximation: one 2D fbm layer, with three taps toward the sun for self-shadowing and a Henyey-Greenstein silver lining. It is not a volume march. |
| Aurora | Raymarched through height layers (22 steps on desktop, 12 on mobile), with a noise-folded curtain. It is a stylised emission model, not physics. |
| Canopy shadow on the ground | Approximation: the crown projected along the sun as a dappled disc. There are no shadow maps. |
| Aerial perspective | Approximation: exponential fog toward the LUT's sky colour. |
| Leaf translucency | Approximation: a thin-slab back-lighting term. |

## The mark and brand pixels

Everything that is a brand pixel is drawn after tone mapping, as crisp quads snapped to the device-pixel grid, in exact sRGB brand colours. That covers the seed, the mark, the graph nodes and the commit stars. The mark is generated from the canonical SVG path, at a whole number of device pixels per mark pixel. It is never rotated or smoothed, and nothing is added to it. Light from those pixels (halos, the seed lighting the soil) is drawn separately, in the HDR scene.

## Motion

Motion is off when `prefers-reduced-motion: reduce` matches or `<html data-motion="off">` is set. The layer listens for the media query, `bodhi:motion`, and changes to that attribute. With motion off, there is no animation loop and no camera flight. The layer renders one complete still frame per scene, at a representative keyframe (`STILL_P` in `core/director.js`), and renders again only when the scene changes or the window resizes. Physics is replaced by deterministic still poses. For example, autumn leaves are frozen mid-fall and on the ground.

With motion on, the camera eases toward the scroll position over about a quarter of a second. A jump of more than one scene, for example from an anchor link, fades through dark instead of flying through every scene. Nothing flashes. The aurora and the star twinkle stay well under 1 Hz, and the film grain is low-amplitude per-pixel noise.

The loop also pauses when the tab is hidden, when the page has scrolled past the last scene, and while the context is lost.

## Performance budget

- **Resolution.** The device-pixel ratio starts at `min(devicePixelRatio, 1.5)`. An exponential moving average of frame time drops it by 20% after 0.8 s over 21 ms, down to 0.6. It raises it by 12% after 5 s under 17.5 ms. Small height-only resizes, such as a mobile URL bar showing or hiding, stretch the canvas instead of reallocating.
- **Tiers.** A coarse pointer, a small screen or fewer than 4 cores selects the low tier. It has no MSAA, about 1,800 leaves instead of about 2,950, 7,000 grass blades instead of 16,000, 2,600 stars instead of 5,200, 12 aurora steps instead of 22, half the memory-field points, and half the falling-leaf pool.
- **Work per frame.** One HDR pass (half-float, 4× MSAA on the high tier) and one post pass. While the cell dive covers the screen, the 3D pass is skipped. The sky LUT is re-rendered only when the sun moves. Leaves, bark, grass, roots, nodes, stars and pixels are all instanced. Branch transforms go to a float texture once per frame, and leaves and graph nodes read it in their vertex shaders. Hot paths allocate nothing per frame.
- **Payload.** About 134 KB of JS outside `vendor/` (about 42 KB gzipped), plus three.js (742 KB minified, 189 KB gzipped). three.js is loaded only after the capability checks pass.

## Run the demo and the tests

`demo.html` is a standalone page with placeholder sections for every scene id, at heights similar to the real page. It has a Motion switch and a small readout showing the scene, `u`, frame time and DPR. Serve `site/` so that `../assets/data/ancestry.js` resolves, then open `/journey/demo.html`:

```sh
python3 -m http.server --directory site 8000
# then visit http://localhost:8000/journey/demo.html
```

To screenshot and check everything (Chromium from `/opt/pw-browsers`, WebGL via SwiftShader):

```sh
NODE_PATH=$(npm root -g) node site/journey/test/shots.cjs          # 3 points per scene
NODE_PATH=$(npm root -g) node site/journey/test/shots.cjs --quick  # 1 point per scene
NODE_PATH=$(npm root -g) node site/journey/test/shots.cjs --only=tree,sky
```

The script saves screenshots at 1440×900 and 390×844 to `test/shots/`, which git ignores, and writes `results.txt` there. It checks that:

- there are no console errors;
- `html.journey-on` gets set;
- `BodhiJourney.scene` matches the scene scrolled to;
- under reduced motion, two screenshots 1 s apart are identical and no frames are rendered in between;
- the Motion switch stops the loop.

It also reports frame times from a requestAnimationFrame sample. If the page's assets aren't next to `journey/`, set `ANCESTRY=/path/to/ancestry.js` to give the spiral real data.

The tests use two query switches. `?journey=force` allows software GL (SwiftShader), and `?jdpr=1` locks the DPR. SwiftShader frame times are orders of magnitude slower than any real GPU. Use them to compare changes against each other, not as real numbers.

## Files

```
journey.js          entry: capability checks, then loads core/stage.js
core/stage.js       renderer, loop, camera, motion, pause, context loss, events
core/timeline.js    scroll -> u and canonical position
core/director.js    camera knots and every scene parameter as a function of position
core/quality.js     device tier and adaptive DPR
core/palette.js     brand colours (sRGB and linear)
core/math.js        PRNG, noise, quaternion helpers
shaders/common.js   hashes, noise, Voronoi, ACES, sky-LUT lookup
world/sky.js        atmosphere LUT, dome (sun, moon, clouds, aurora), stars
world/land.js       terrain, soil cut face, treeline, grass
world/tree.js       tree generation, branch springs, leaves, falling-leaf physics
world/roots.js      root system and its graph lighting
world/network.js    mark -> nodes -> the tree as a graph
world/cosmos.js     commit spiral, memory field, constellations
world/pixels.js     crisp brand pixels and HDR glows; the mark's pixels
world/post.js       cell dive, tone map, grade, grain, calm band
vendor/             three.js r186 (MIT)
```

`vendor/three.module.min.js` is three@0.186.1's `build/three.module.js`, bundled with its `three.core.js` import and minified once with `esbuild --bundle --minify --format=esm`, because the npm package no longer ships a minified build. `vendor/LICENSE` is three.js's MIT license.
