"""
FX Sprites — Crawling Electricity Generator
Part of the Runestone Estate SL Materializer Suite
https://runed4life.com

Generates frames of crawling surface electrical discharge.
Pure Python — no external dependencies beyond stdlib.
All pixel math uses lists and basic math operations.

This generator is designed to work both inside GIMP (via the
plugin integration layer) and standalone for testing.
"""

import math
import random
from . import register


# ---------------------------------------------------------------------------
# Parameter definitions for the GIMP dialog
# ---------------------------------------------------------------------------

def get_params():
    """Return parameter definitions for the UI.

    Each tuple: (type, key, label, description, default, min_val, max_val, choices)
    - type: 'int', 'float', 'choice', 'color'
    - choices: list of strings for 'choice' type, None otherwise
    """
    return [
        ('int', 'arc_count', 'Arc sources',
         'Number of electrical arc origin points',
         6, 2, 16, None),

        ('choice', 'branch_density', 'Branch density',
         'How much the arcs branch and fork',
         'Medium', None, None, ['Low', 'Medium', 'High']),

        ('float', 'glow_radius', 'Glow radius',
         'Bloom spread around arc cores (pixels)',
         3.0, 1.0, 8.0, None),

        ('int', 'color_r', 'Color — Red',
         'Red component of arc color (0-255)',
         140, 0, 255, None),

        ('int', 'color_g', 'Color — Green',
         'Green component of arc color (0-255)',
         180, 0, 255, None),

        ('int', 'color_b', 'Color — Blue',
         'Blue component of arc color (0-255)',
         255, 0, 255, None),

        ('int', 'intensity_variation', 'Frame variation %',
         'How much frames differ (0=static, 100=chaotic)',
         70, 0, 100, None),

        ('int', 'seed', 'Random seed',
         'Seed for reproducibility (same seed = same result)',
         42, 0, 99999, None),
    ]


# ---------------------------------------------------------------------------
# Arc drawing primitives (pure Python, no numpy)
# ---------------------------------------------------------------------------

def _branch_prob(density):
    """Map density preset to branching probability."""
    return {'Low': 0.04, 'Medium': 0.08, 'High': 0.15}.get(density, 0.08)


def _draw_arc(canvas_intensity, width, height, start_x, start_y,
              angle, steps, intensity, branch_prob, depth=0):
    """Draw a single electrical arc using random walk.

    Writes intensity values into canvas_intensity (a flat list of floats,
    height * width, row-major). No external dependencies.
    """
    if depth > 3:
        return

    x, y = float(start_x), float(start_y)
    current_angle = angle
    step_len = 3.0
    wander = 0.4

    for step in range(steps):
        # Random walk the direction
        current_angle += random.gauss(0, wander)

        # Occasional sharp turns for electrical look
        if random.random() < 0.05:
            current_angle += random.choice([-1, 1]) * random.uniform(0.5, 1.2)

        nx = x + step_len * math.cos(current_angle)
        ny = y + step_len * math.sin(current_angle)

        # Bounds check
        if nx < -5 or nx >= width + 5 or ny < -5 or ny >= height + 5:
            break

        # Draw substeps for smoother lines
        num_sub = max(int(step_len * 2), 4)
        for s in range(num_sub):
            t = s / num_sub
            px = x + t * (nx - x)
            py = y + t * (ny - y)
            ix, iy = int(round(px)), int(round(py))
            if 0 <= ix < width and 0 <= iy < height:
                fade = 1.0 - (step / steps) * 0.5
                brightness = intensity * fade
                idx = iy * width + ix
                if brightness > canvas_intensity[idx]:
                    canvas_intensity[idx] = brightness

        # Branching
        if random.random() < branch_prob and depth < 2:
            b_angle = current_angle + random.choice([-1, 1]) * random.uniform(0.4, 1.0)
            b_steps = random.randint(8, max(10, steps // 3))
            b_intensity = intensity * 0.6
            _draw_arc(canvas_intensity, width, height, nx, ny,
                      b_angle, b_steps, b_intensity, branch_prob, depth + 1)

        x, y = nx, ny


def _gaussian_blur_approx(data, width, height, radius):
    """Approximate gaussian blur using 3-pass box blur (no dependencies).

    Operates on a flat list of floats (height * width, row-major).
    Returns a new flat list. Box blur radius derived from gaussian sigma.
    """
    if radius < 0.5:
        return list(data)

    # Box blur radius for 3-pass approximation of gaussian
    # See: http://blog.ivank.net/fastest-gaussian-blur.html
    box_r = max(1, int(round(radius * 0.8)))

    src = list(data)
    dst = [0.0] * len(src)

    for _pass in range(3):
        # Horizontal pass
        for row in range(height):
            offset = row * width
            for col in range(width):
                total = 0.0
                count = 0
                for k in range(-box_r, box_r + 1):
                    c = col + k
                    if 0 <= c < width:
                        total += src[offset + c]
                        count += 1
                dst[offset + col] = total / count if count > 0 else 0.0

        # Vertical pass
        src, dst = dst, [0.0] * len(src)
        for col in range(width):
            for row in range(height):
                total = 0.0
                count = 0
                for k in range(-box_r, box_r + 1):
                    r = row + k
                    if 0 <= r < height:
                        total += src[r * width + col]
                        count += 1
                dst[row * width + col] = total / count if count > 0 else 0.0

        src = list(dst)
        dst = [0.0] * len(src)

    return src


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

def generate(width, height, frame_index, total_frames, seed,
             arc_count=6, branch_density='Medium', glow_radius=3.0,
             color_r=140, color_g=180, color_b=255,
             intensity_variation=70, **_kwargs):
    """Generate a single frame of crawling electricity.

    Args:
        width: Frame width in pixels
        height: Frame height in pixels
        frame_index: Which frame (0-based) in the sequence
        total_frames: Total number of frames being generated
        seed: Base random seed
        arc_count: Number of arc origin points
        branch_density: 'Low', 'Medium', or 'High'
        glow_radius: Bloom spread in pixels
        color_r/g/b: Arc color (0-255)
        intensity_variation: 0-100, how much frames differ

    Returns:
        List of pixel values as [r, g, b, a, r, g, b, a, ...] (flat),
        length = width * height * 4. Values are 0-255 integers.
    """
    # Seed for this specific frame (deterministic but varied)
    frame_seed = seed + frame_index * 137
    random.seed(frame_seed)

    bp = _branch_prob(branch_density)
    variation = intensity_variation / 100.0

    # Create persistent seed points from base seed
    # These are "anchor" points that drift substantially per frame
    random.seed(seed)
    anchor_points = []
    for _ in range(arc_count):
        sx = random.uniform(10, width - 10)
        sy = random.uniform(10, height - 10)
        angle = random.uniform(0, 2 * math.pi)
        # Each anchor gets its own drift phase so they move independently
        phase_x = random.uniform(0, 2 * math.pi)
        phase_y = random.uniform(0, 2 * math.pi)
        anchor_points.append((sx, sy, angle, phase_x, phase_y))

    # Re-seed for frame-specific variation
    random.seed(frame_seed)

    # Canvas: flat list of intensity floats (0.0 - 1.0)
    canvas = [0.0] * (width * height)

    # Build this frame's actual origin points from anchors + per-frame randomness
    # Drift is proportional to frame dimensions so it scales properly
    drift_range = min(width, height) * 0.3 * variation
    seed_points = []

    for sx, sy, base_angle, px, py in anchor_points:
        # Substantial sinusoidal drift — each point orbits its anchor
        dx = sx + math.sin(frame_index * 0.35 + px) * drift_range
        dy = sy + math.cos(frame_index * 0.28 + py) * drift_range

        # Wrap into frame bounds so arcs don't cluster outside
        dx = dx % width
        dy = dy % height

        # Vary angle significantly per frame
        angle = base_angle + math.sin(frame_index * 0.4 + base_angle) * 1.5 * variation
        angle += random.uniform(-0.3, 0.3) * variation

        seed_points.append((dx, dy, angle))

    # Add some fully random per-frame origin points for variety
    # These appear and disappear between frames = flickering tendrils
    num_transient = max(1, arc_count // 3)
    for _ in range(num_transient):
        tx = random.uniform(0, width)
        ty = random.uniform(0, height)
        ta = random.uniform(0, 2 * math.pi)
        seed_points.append((tx, ty, ta))

    # Add edge-origin arcs (also randomized per frame)
    for _ in range(max(1, arc_count // 4)):
        side = random.randint(0, 3)
        if side == 0:
            seed_points.append((random.uniform(0, width), 0,
                                random.uniform(0.3, 2.8)))
        elif side == 1:
            seed_points.append((width - 1, random.uniform(0, height),
                                random.uniform(1.8, 4.3)))
        elif side == 2:
            seed_points.append((random.uniform(0, width), height - 1,
                                random.uniform(-2.8, -0.3)))
        else:
            seed_points.append((0, random.uniform(0, height),
                                random.uniform(-0.8, 0.8)))

    # Generate arcs
    for dx, dy, angle in seed_points:
        steps = random.randint(25, 70)

        _draw_arc(canvas, width, height, dx, dy, angle, steps, 1.0, bp)

        # Sometimes a secondary arc from same origin
        if random.random() < 0.4:
            angle2 = angle + random.uniform(-1.5, 1.5)
            steps2 = random.randint(15, 40)
            _draw_arc(canvas, width, height, dx, dy, angle2, steps2, 0.7, bp)

    # Apply multi-layer glow
    core = _gaussian_blur_approx(canvas, width, height, glow_radius * 0.4)
    medium = _gaussian_blur_approx(canvas, width, height, glow_radius)
    bloom = _gaussian_blur_approx(canvas, width, height, glow_radius * 2.5)

    # Combine glow layers
    combined = [0.0] * (width * height)
    for i in range(width * height):
        combined[i] = core[i] * 1.0 + medium[i] * 0.5 + bloom[i] * 0.25

    # Normalize
    max_val = max(combined) if combined else 1.0
    if max_val > 0:
        for i in range(len(combined)):
            combined[i] /= max_val

    # Colorize to RGBA
    # Color ramp: low intensity = deep tinted, high = white-hot
    pixels = []
    for i in range(width * height):
        g = combined[i]
        if g < 0.001:
            pixels.extend([0, 0, 0, 0])  # Transparent black
        else:
            # Red: mostly at high intensity
            r = min(255, int(g ** 1.8 * 255))
            # Green: mid-high
            gn = min(255, int(g ** 1.3 * (color_g / 255.0) * 255 + g ** 2.5 * 35))
            # Blue: present across all intensities
            b = min(255, int(g ** 0.7 * (color_b / 255.0) * 255))

            # Blend toward user color at mid intensities,
            # toward white at peak
            white_blend = g ** 2.0
            r = min(255, int(r * (1 - white_blend * 0.3)
                             + color_r * g * (1 - white_blend) * 0.5
                             + 255 * white_blend * 0.7))
            gn = min(255, int(gn * (1 - white_blend * 0.2)
                              + 255 * white_blend * 0.5))
            b = min(255, int(b))

            alpha = min(255, int(g ** 0.5 * 255))
            pixels.extend([r, gn, b, alpha])

    return pixels


# ---------------------------------------------------------------------------
# Self-registration
# ---------------------------------------------------------------------------

register(
    name='electricity',
    label='Crawling Electricity',
    description='Animated electrical surface discharge with branching arcs and glow.',
    get_params=get_params,
    generate=generate,
)
