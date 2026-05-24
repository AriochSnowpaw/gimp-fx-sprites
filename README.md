# ⚡ FX Sprites — Animated Effect Sprite Sheet Generator for GIMP 3

**Part of the Runestone Estate SL Materializer Suite**
[runed4life.com](https://runed4life.com)

Generate procedural animated effects as sprite sheets — purpose-built for Second Life PBR materials, game development, and creative projects.

## What it does

FX Sprites generates multi-frame animated effects directly inside GIMP 3. Version 0.1 ships with a **Crawling Electricity** generator that produces surface electrical discharge with branching arcs and customizable glow — the kind of effect you'd use on sci-fi panels, magical objects, or steampunk machinery.

Output options:
- **Layers** — one frame per layer, ready for GIMP's animation preview
- **Sprite Sheet** — all frames composited into a grid, ready to export as PNG and upload to Second Life (or any game engine)

Every sprite sheet generation includes a clipboard-ready **LSL script** for `llSetTextureAnim`, so you can drop it straight into your SL build.

## Installation

### Requirements

- **GIMP 3.0+** (tested on 3.2.4)
- No external dependencies — uses only Python stdlib and GIMP's built-in libraries

### Steps

1. Download or clone this repository
2. Find your GIMP 3 plug-ins folder:
   - **Linux**: `~/.config/GIMP/3.0/plug-ins/`
   - **Windows**: `%APPDATA%\GIMP\3.0\plug-ins\`
   - **macOS**: `~/Library/Application Support/GIMP/3.0/plug-ins/`
3. Create a folder named `fx_sprites` inside the plug-ins directory
4. Copy these files into it:
   ```
   fx_sprites/
     fx_sprites.py
     generators/
       __init__.py
       electricity.py
   ```
5. **Linux/macOS only**: make the main script executable:
   ```bash
   chmod +x ~/.config/GIMP/3.0/plug-ins/fx_sprites/fx_sprites.py
   ```
6. Restart GIMP

The plugin appears under **Filters → Animation → FX Sprites v0.1 (Runestone)...**

## Usage

1. Open or create any image in GIMP (the plugin creates its own layers/images)
2. Go to **Filters → Animation → FX Sprites v0.1 (Runestone)...**
3. Configure your effect:
   - **Frame count**: how many animation frames (16, 32, 64, etc.)
   - **Frame width/height**: dimensions of each frame (e.g. 128×256)
   - **Arc sources**: number of electrical origin points
   - **Branch density**: Low / Medium / High forking
   - **Glow radius**: bloom spread around the arc cores
   - **Color**: RGB values for the arc color (default: blue-white)
   - **Variation %**: how much frames differ (0 = static, 100 = chaotic)
   - **Random seed**: same seed = same result (great for iteration)
   - **Output mode**: Layers or Sprite Sheet
4. Click OK and wait for generation
5. A dialog shows the LSL script for Second Life use

## Second Life Integration

### Using with PBR Materials

The generated sprite sheet works as an **emissive texture** in SL's PBR/GLTF material system:

1. **Upload** the sprite sheet PNG to Second Life
2. **Apply** a PBR material to your object
3. **Set the emissive override**: apply the sprite sheet texture to the emissive channel, set emissive tint to white `<1,1,1>`
4. **Add the LSL script** (shown after generation) to the object:

```lsl
// FX Sprites — Runestone Estate (runed4life.com)
// 8x4 grid, 32 frames at 10.0 fps
default
{
    state_entry()
    {
        llSetTextureAnim(ANIM_ON | LOOP, ALL_SIDES, 8, 4, 0.0, 32.0, 10.0);
    }
}
```

### Tips

- **Glow**: Add SL's postprocessing glow at 0.1–0.2 for extra bloom. The emissive map controls where glow appears.
- **Speed**: Adjust the last parameter in `llSetTextureAnim` — lower = slower crawl, higher = frenetic.
- **Alpha mode**: Use Opaque or Mask mode. Blend mode has known quirks with PBR texture animation.
- **Color in-world**: The emissive tint color multiplies with the texture, so you can shift colors without re-uploading.
- **Blinn-Phong**: The sprite sheet also works with legacy Blinn-Phong materials. Set the face to **Full Bright** and apply the texture to the diffuse slot. Both material systems have been tested and verified in-world.

### Troubleshooting

**Emissive texture not showing in PBR material:**
The most common cause is the **emissive tint being set to black** `<0,0,0>`. When the tint is black, the emissive texture is multiplied to zero and nothing renders. Set the emissive tint to **white** `<1,1,1>` in the Build floater's PBR material tab.

**PBR materials not rendering at all:**
Your viewer needs **Advanced Lighting Model (ALM)** enabled. In Firestorm: Preferences → Graphics → make sure ALM and Atmospheric Shaders are both ON. Lower graphics quality settings can disable PBR rendering entirely.

**Animation not playing on PBR material:**
Make sure the `llSetTextureAnim` script is in the same prim as the PBR material. If the material is only on one face, try changing `ALL_SIDES` to the specific face number (0–5).

**Sprite sheet looks correct but animation stutters:**
Reduce the frame count or frame size. SL texture animation performance depends on texture memory — a 1024×1024 sprite sheet with 32 frames is the practical upper limit for smooth playback.

### Using with SL Materialize

This plugin is designed to complement [SL Materialize](https://runed4life.com) for complete PBR material workflows. Generated sprite sheets can serve as height map inputs for normal map generation, or directly as emissive channel textures.

## Parameters Reference

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| Frame count | 4–128 | 32 | Total animation frames |
| Frame width | 32–1024 | 128 | Pixel width per frame |
| Frame height | 32–1024 | 256 | Pixel height per frame |
| Output mode | 0=Layers / 1=Sheet | 0 | How to output results |
| Arc sources | 2–16 | 6 | Number of origin points |
| Branch density | 0=Low / 1=Med / 2=High | 1 | Forking intensity |
| Glow radius | 1.0–8.0 | 3.0 | Bloom spread (px) |
| Color R/G/B | 0–255 | 140/180/255 | Arc color |
| Variation % | 0–100 | 70 | Inter-frame difference |
| Random seed | 0–99999 | 42 | Reproducibility seed |

## Roadmap

FX Sprites is designed with a pluggable generator architecture. Future effects on the roadmap:

- ✨ **Sparkles** — random point bursts with falloff
- 💡 **Neon Tubes** — path-following glow with flicker
- 🔥 **Fire / Embers** — particle rise with thermal color ramp
- 🌀 **Plasma Field** — noise-driven color cycling energy

Future output enhancements:
- APNG direct export
- Animated GIF preview
- Tiled preview window
- SL Materialize pipeline integration

## Contributing

Contributions welcome! The generator architecture is designed for easy extension:

1. Create a new file in `generators/` (e.g. `sparkles.py`)
2. Implement a `generate()` function matching the signature in `electricity.py`
3. Call `register()` to add it to the registry

See `generators/electricity.py` for the complete reference implementation.

## License

MIT License — Copyright (c) 2026 Runestone Estate ([runed4life.com](https://runed4life.com))

See [LICENSE](LICENSE) for full text.

---

**Runestone Estate** — Forging digital worlds.
[runed4life.com](https://runed4life.com) · [Games Hall](https://games.runed4life.com)
