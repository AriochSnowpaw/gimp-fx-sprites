#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FX Sprites — GIMP 3 Plugin
Animated effect sprite sheet generator for Second Life and beyond.

Part of the Runestone Estate SL Materializer Suite
https://runed4life.com
Copyright (c) 2026 Runestone Estate — MIT License

Install:
  Copy this file and the generators/ folder into your GIMP 3 plug-ins directory.
  The plugin appears under Filters → Animation → FX Sprites...

  Plug-in directories (create a subfolder named 'fx_sprites'):
    Linux:   ~/.config/GIMP/3.0/plug-ins/fx_sprites/
    Windows: %APPDATA%\\GIMP\\3.0\\plug-ins\\fx_sprites\\
    macOS:   ~/Library/Application Support/GIMP/3.0/plug-ins/fx_sprites/

  Final structure:
    fx_sprites/
      fx_sprites.py          (this file — must be executable on Linux/macOS)
      generators/
        __init__.py
        electricity.py
"""

import sys
import os
import math

# Ensure the generators package is importable from the plugin directory
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

# Import the generator registry (triggers self-registration of all generators)
from generators import electricity  # noqa: F401 — side-effect import
from generators import sparkles     # noqa: F401 — side-effect import
from generators import get_generator, list_generators

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLUGIN_PROC = 'plug-in-runestone-fx-sprites'
PLUGIN_BINARY = 'fx_sprites'
VERSION = '0.1.0'
MENU_LABEL = f'_FX Sprites v{VERSION} (Runestone)...'
MENU_PATH = '<Image>/Filters/Animation'


# ---------------------------------------------------------------------------
# Grid math utilities
# ---------------------------------------------------------------------------

def _best_grid(frame_count):
    """Find the best cols x rows grid for a sprite sheet.

    Prefers wider grids (more columns than rows) since that maps
    well to llSetTextureAnim which reads left-to-right, top-to-bottom.
    """
    best_cols, best_rows = frame_count, 1
    best_ratio = float('inf')

    for cols in range(1, frame_count + 1):
        if frame_count % cols == 0:
            rows = frame_count // cols
            ratio = max(cols / rows, rows / cols)
            # Prefer wider grids with a slight bias
            adj_ratio = ratio * (1.0 if cols >= rows else 1.1)
            if adj_ratio < best_ratio:
                best_ratio = adj_ratio
                best_cols, best_rows = cols, rows

    return best_cols, best_rows


def _lsl_snippet(cols, rows, total_frames, fps=10.0):
    """Generate a clipboard-ready LSL texture animation call."""
    return (
        f'// FX Sprites — Runestone Estate (runed4life.com)\n'
        f'// {cols}x{rows} grid, {total_frames} frames at {fps:.1f} fps\n'
        f'default\n'
        f'{{\n'
        f'    state_entry()\n'
        f'    {{\n'
        f'        llSetTextureAnim(ANIM_ON | LOOP, ALL_SIDES, '
        f'{cols}, {rows}, 0.0, {float(total_frames)}, {fps});\n'
        f'    }}\n'
        f'}}\n'
    )


# ---------------------------------------------------------------------------
# Main plugin execution
# ---------------------------------------------------------------------------

def _run_fx_sprites(procedure, run_mode, image, drawables, config, data):
    """Main entry point called by GIMP when the user invokes the plugin."""

    # --- Interactive dialog ---
    if run_mode == Gimp.RunMode.INTERACTIVE:
        gi.require_version('GimpUi', '3.0')
        from gi.repository import GimpUi

        GimpUi.init(PLUGIN_BINARY)

        dialog = GimpUi.ProcedureDialog(procedure=procedure, config=config)
        dialog.fill(None)  # Auto-fill all registered properties

        if not dialog.run():
            dialog.destroy()
            return procedure.new_return_values(
                Gimp.PDBStatusType.CANCEL, None)

        dialog.destroy()

    # --- Read parameters from config ---
    frame_count = config.get_property('frame-count')
    frame_w = config.get_property('frame-width')
    frame_h = config.get_property('frame-height')
    output_mode = config.get_property('output-mode')
    effect = config.get_property('effect')

    # Common params shared by all generators
    common_params = {
        'glow_radius': config.get_property('glow-radius'),
        'color_r': config.get_property('color-r'),
        'color_g': config.get_property('color-g'),
        'color_b': config.get_property('color-b'),
        'intensity_variation': config.get_property('intensity-variation'),
        'seed': config.get_property('random-seed'),
    }

    # Route to the correct generator and build its params
    if effect == 0:
        # Electricity
        gen_name = 'electricity'
        gen_params = dict(common_params)
        gen_params['arc_count'] = config.get_property('arc-count')
        gen_params['branch_density'] = ['Low', 'Medium', 'High'][
            config.get_property('branch-density')]
    elif effect == 1:
        # Sparkles & Twinkle
        gen_name = 'sparkles'
        gen_params = dict(common_params)
        gen_params['style'] = config.get_property('sparkle-style')
        gen_params['density'] = config.get_property('point-density')
        # Size params use glow_radius as a base for now
        gen_params['size_min'] = max(0.5, gen_params['glow_radius'] * 0.3)
        gen_params['size_max'] = gen_params['glow_radius'] * 1.0
    else:
        gen_name = 'electricity'
        gen_params = dict(common_params)

    gen = get_generator(gen_name)
    if gen is None:
        return procedure.new_return_values(
            Gimp.PDBStatusType.EXECUTION_ERROR,
            GLib.Error('Generator not found'))

    generate_func = gen['generate']

    # --- Progress ---
    Gimp.progress_init(f'FX Sprites: generating {frame_count} {gen_name} frames...')

    # --- Generate frames ---
    frames = []
    for i in range(frame_count):
        Gimp.progress_update(i / frame_count)
        pixels = generate_func(
            width=frame_w,
            height=frame_h,
            frame_index=i,
            total_frames=frame_count,
            seed=gen_params['seed'],
            **{k: v for k, v in gen_params.items() if k != 'seed'}
        )
        frames.append(pixels)

    Gimp.progress_update(1.0)

    # --- Output ---
    import tempfile

    if output_mode == 0:
        # Layers mode — add frames as layers to current image
        image.undo_group_start()

        for i, pixel_data in enumerate(frames):
            # Write frame to temp PNG, load as layer (fast path)
            tmp_path = os.path.join(
                tempfile.gettempdir(),
                f'_fx_sprites_frame_{i:03d}.png')
            _write_minimal_png(tmp_path, pixel_data, frame_w, frame_h)
            layer = _load_frame_as_layer(
                image, tmp_path, f'FX Frame {i + 1:03d}')

            # Clean up temp file
            try:
                os.remove(tmp_path)
            except OSError:
                pass

            # Fallback if PNG load failed
            if layer is None:
                layer = Gimp.Layer.new(
                    image, f'FX Frame {i + 1:03d}',
                    frame_w, frame_h,
                    Gimp.ImageType.RGBA_IMAGE, 100.0,
                    Gimp.LayerMode.NORMAL)
                image.insert_layer(layer, None, 0)
                _write_pixels_to_drawable(
                    layer, pixel_data, frame_w, frame_h)

        image.undo_group_end()
        Gimp.displays_flush()

        # Show LSL info
        cols, rows = _best_grid(frame_count)
        lsl = _lsl_snippet(cols, rows, frame_count)
        Gimp.message(
            f'FX Sprites — {frame_count} frames generated as layers.\n\n'
            f'To create a sprite sheet: flatten visible or use '
            f'Filters → Animation → Sprite Sheet.\n\n'
            f'For Second Life, use a {cols}x{rows} grid:\n\n{lsl}'
        )

    else:
        # Sprite sheet mode — create new image with composited grid
        cols, rows = _best_grid(frame_count)
        sheet_w = cols * frame_w
        sheet_h = rows * frame_h

        # Build the full sprite sheet pixel data in Python (fast)
        sheet_pixels = [0] * (sheet_w * sheet_h * 4)

        for i, pixel_data in enumerate(frames):
            col = i % cols
            row = i // cols
            x_off = col * frame_w
            y_off = row * frame_h

            for py in range(frame_h):
                src_start = py * frame_w * 4
                dst_start = ((y_off + py) * sheet_w + x_off) * 4
                for px in range(frame_w):
                    si = src_start + px * 4
                    di = dst_start + px * 4
                    sheet_pixels[di] = pixel_data[si]
                    sheet_pixels[di + 1] = pixel_data[si + 1]
                    sheet_pixels[di + 2] = pixel_data[si + 2]
                    sheet_pixels[di + 3] = pixel_data[si + 3]

        # Write entire sheet as one temp PNG, load into GIMP
        tmp_path = os.path.join(
            tempfile.gettempdir(), '_fx_sprites_sheet.png')
        _write_minimal_png(tmp_path, sheet_pixels, sheet_w, sheet_h)

        # Load as a new image
        pdb = Gimp.get_pdb()
        load_proc = pdb.lookup_procedure('file-png-load')
        config = load_proc.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('file', Gio.File.new_for_path(tmp_path))
        result = load_proc.run(config)

        try:
            os.remove(tmp_path)
        except OSError:
            pass

        status = result.index(0)
        if status == Gimp.PDBStatusType.SUCCESS:
            new_image = result.index(1)
            display = Gimp.Display.new(new_image)
            Gimp.displays_flush()
        else:
            Gimp.message('FX Sprites: Failed to create sprite sheet image.')

        # Show LSL info
        lsl = _lsl_snippet(cols, rows, frame_count)
        Gimp.message(
            f'FX Sprites — Sprite sheet created: '
            f'{sheet_w}x{sheet_h} ({cols}x{rows} grid)\n\n'
            f'Export as PNG for Second Life upload.\n\n'
            f'LSL animation script:\n\n{lsl}'
        )

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)


def _write_pixels_to_drawable(drawable, pixel_data, width, height):
    """Write a flat RGBA pixel list into a GIMP drawable.

    pixel_data: flat list of ints [r,g,b,a, r,g,b,a, ...], length = w*h*4

    Uses Gimp.Drawable.set_pixel() — the direct GIMP 3 API for setting
    individual pixels. Slow but universally compatible.
    Used as fallback only.
    """
    import gi as _gi
    _gi.require_version('Gegl', '0.4')
    from gi.repository import Gegl

    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 4
            r = pixel_data[idx]
            g = pixel_data[idx + 1]
            b = pixel_data[idx + 2]
            a = pixel_data[idx + 3]

            # Skip fully transparent pixels (optimization)
            if a == 0 and r == 0 and g == 0 and b == 0:
                continue

            color = Gegl.Color.new("black")
            color.set_rgba(r / 255.0, g / 255.0, b / 255.0, a / 255.0)
            drawable.set_pixel(x, y, color)

    drawable.update(0, 0, width, height)


def _write_minimal_png(filepath, pixel_data, width, height):
    """Write a minimal RGBA PNG file using only Python stdlib.

    No PIL, no numpy — just struct and zlib. This lets us write
    temp files that GIMP's native PNG loader can read at full speed.
    """
    import struct
    import zlib

    def _chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack('>I', len(data)) + c + crc

    # PNG signature
    sig = b'\x89PNG\r\n\x1a\n'

    # IHDR: width, height, bit depth 8, color type 6 (RGBA)
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = _chunk(b'IHDR', ihdr_data)

    # IDAT: build raw scanlines with filter byte 0 (None) per row
    raw_rows = []
    for y in range(height):
        raw_rows.append(b'\x00')  # filter byte
        row_start = y * width * 4
        row_bytes = bytes(pixel_data[row_start:row_start + width * 4])
        raw_rows.append(row_bytes)

    raw_data = b''.join(raw_rows)
    compressed = zlib.compress(raw_data, 6)
    idat = _chunk(b'IDAT', compressed)

    # IEND
    iend = _chunk(b'IEND', b'')

    with open(filepath, 'wb') as f:
        f.write(sig + ihdr + idat + iend)


def _load_frame_as_layer(image, filepath, layer_name):
    """Load a PNG file as a new layer in the given image.

    Uses GIMP's native file loader via PDB — fast compiled C code
    for pixel I/O instead of per-pixel Python calls.
    """
    # Load the PNG as a new image
    pdb = Gimp.get_pdb()

    # Lookup the procedure, create config, set properties, run
    load_proc = pdb.lookup_procedure('file-png-load')
    config = load_proc.create_config()
    config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
    config.set_property('file', Gio.File.new_for_path(filepath))
    result = load_proc.run(config)

    status = result.index(0)
    if status != Gimp.PDBStatusType.SUCCESS:
        return None

    temp_image = result.index(1)

    # Get the loaded layer and copy it into our target image
    temp_layers = temp_image.get_layers()
    if not temp_layers:
        temp_image.delete()
        return None

    temp_layer = temp_layers[0]

    # Duplicate the layer into our target image
    new_layer = Gimp.Layer.new_from_drawable(temp_layer, image)
    new_layer.set_name(layer_name)
    image.insert_layer(new_layer, None, 0)

    # Clean up temp image
    temp_image.delete()

    return new_layer


# ---------------------------------------------------------------------------
# GIMP 3 Plugin class (GObject Introspection boilerplate)
# ---------------------------------------------------------------------------

class FxSprites(Gimp.PlugIn):

    def do_query_procedures(self):
        return [PLUGIN_PROC]

    def do_set_i18n(self, name):
        return False

    def do_create_procedure(self, name):
        if name != PLUGIN_PROC:
            return None

        procedure = Gimp.ImageProcedure.new(
            self, name,
            Gimp.PDBProcType.PLUGIN,
            _run_fx_sprites, None)

        procedure.set_image_types('*')
        procedure.set_sensitivity_mask(
            Gimp.ProcedureSensitivityMask.ALWAYS)

        procedure.set_menu_label(MENU_LABEL)
        procedure.add_menu_path(MENU_PATH)

        procedure.set_documentation(
            'Generate animated FX sprite sheets for Second Life PBR materials.',
            'Creates multi-frame sprite sheets with procedural effects '
            '(electricity, sparkles, etc.) suitable for SL texture animation '
            'via llSetTextureAnim. Part of the Runestone Estate SL Materializer '
            'Suite. https://runed4life.com',
        )
        procedure.set_attribution(
            'Runestone Estate',
            'Runestone Estate (runed4life.com)',
            '2026')

        # --- Register parameters ---

        # Effect selector: 0 = Crawling Electricity, 1 = Sparkles & Twinkle
        procedure.add_int_argument(
            'effect', 'Effect (0=Electricity, 1=Sparkles)',
            'Which effect generator to use',
            0, 1, 0,
            GObject.ParamFlags.READWRITE)

        # Sparkles-specific: style
        # 0 = Sparkle (sharp bursts), 1 = Twinkle (gentle shimmer)
        procedure.add_int_argument(
            'sparkle-style', 'Sparkle style (0=Spark, 1=Twinkle)',
            'Sparkles only: 0=sharp bursts, 1=gentle twinkle',
            0, 1, 0,
            GObject.ParamFlags.READWRITE)

        procedure.add_int_argument(
            'point-density', 'Point density',
            'Sparkles only: number of points per frame',
            5, 200, 30,
            GObject.ParamFlags.READWRITE)

        # Output configuration
        procedure.add_int_argument(
            'frame-count', '_Frame count',
            'Number of animation frames to generate',
            4, 128, 32,
            GObject.ParamFlags.READWRITE)

        procedure.add_int_argument(
            'frame-width', 'Frame _width',
            'Width of each frame in pixels',
            32, 1024, 128,
            GObject.ParamFlags.READWRITE)

        procedure.add_int_argument(
            'frame-height', 'Frame _height',
            'Height of each frame in pixels',
            32, 1024, 256,
            GObject.ParamFlags.READWRITE)

        # Output mode: 0 = Layers (one frame per layer)
        #              1 = Sprite Sheet (all frames in a grid)
        procedure.add_int_argument(
            'output-mode', '_Output mode (0=Layers, 1=Sheet)',
            'How to output: 0 = separate layers, 1 = sprite sheet grid',
            0, 1, 0,
            GObject.ParamFlags.READWRITE)

        # Generator parameters
        procedure.add_int_argument(
            'arc-count', '_Arc sources',
            'Number of electrical arc origin points',
            2, 16, 6,
            GObject.ParamFlags.READWRITE)

        # Branch density: 0 = Low, 1 = Medium, 2 = High
        procedure.add_int_argument(
            'branch-density', '_Branch density (0=Low 1=Med 2=High)',
            'How much arcs branch: 0=Low, 1=Medium, 2=High',
            0, 2, 1,
            GObject.ParamFlags.READWRITE)

        procedure.add_double_argument(
            'glow-radius', '_Glow radius',
            'Bloom spread around arc cores',
            1.0, 8.0, 3.0,
            GObject.ParamFlags.READWRITE)

        procedure.add_int_argument(
            'color-r', 'Color — _Red',
            'Red component of arc color',
            0, 255, 140,
            GObject.ParamFlags.READWRITE)

        procedure.add_int_argument(
            'color-g', 'Color — _Green',
            'Green component of arc color',
            0, 255, 180,
            GObject.ParamFlags.READWRITE)

        procedure.add_int_argument(
            'color-b', 'Color — _Blue',
            'Blue component of arc color',
            0, 255, 255,
            GObject.ParamFlags.READWRITE)

        procedure.add_int_argument(
            'intensity-variation', '_Variation %',
            'How much frames differ from each other',
            0, 100, 70,
            GObject.ParamFlags.READWRITE)

        procedure.add_int_argument(
            'random-seed', 'Random _seed',
            'Seed for reproducible generation',
            0, 99999, 42,
            GObject.ParamFlags.READWRITE)

        return procedure


Gimp.main(FxSprites.__gtype__, sys.argv)
