"""
FX Sprites — Sparkles & Twinkle Generator
Part of the Runestone Estate SL Materializer Suite
https://runed4life.com

Generates frames of sparkle bursts or gentle twinkle effects.
Pure Python — no external dependencies beyond stdlib.

Two style presets:
  Sparkle: random bursts, sharp attack, fast decay, high energy
  Twinkle: soft fade-in/fade-out, overlapping, gentle drift
"""

import math
import random
from . import register


# ---------------------------------------------------------------------------
# Parameter definitions for the GIMP dialog
# ---------------------------------------------------------------------------

def get_params():
    """Return parameter definitions for the UI."""
    return [
        ('int', 'style', 'Style (0=Sparkle, 1=Twinkle)',
         '0 = sharp bursts, 1 = gentle fade in/out',
         0, 0, 1, None),

        ('int', 'density', 'Density',
         'Number of points per frame',
         30, 5, 200, None),

        ('float', 'size_min', 'Min point size',
         'Minimum radius of each point (pixels)',
         1.0, 0.5, 8.0, None),

        ('float', 'size_max', 'Max point size',
         'Maximum radius of each point (pixels)',
         3.5, 1.0, 16.0, None),

        ('float', 'glow_radius', 'Glow radius',
         'Bloom spread around each point (pixels)',
         4.0, 1.0, 12.0, None),

        ('int', 'color_r', 'Color — Red',
         'Red component of point color (0-255)',
         255, 0, 255, None),

        ('int', 'color_g', 'Color — Green',
         'Green component of point color (0-255)',
         240, 0, 255, None),

        ('int', 'color_b', 'Color — Blue',
         'Blue component of point color (0-255)',
         200, 0, 255, None),

        ('int', 'intensity_variation', 'Frame variation %',
         'How much frames differ (0=static, 100=chaotic)',
         80, 0, 100, None),

        ('int', 'seed', 'Random seed',
         'Seed for reproducibility (same seed = same result)',
         42, 0, 99999, None),
    ]


# ---------------------------------------------------------------------------
# Point lifecycle management
# ---------------------------------------------------------------------------

class SparkPoint:
    """A single sparkle or twinkle point with lifecycle."""

    def __init__(self, x, y, birth_frame, lifespan, peak_brightness,
                 size, drift_x, drift_y, attack_frames, decay_frames):
        self.x = x
        self.y = y
        self.birth_frame = birth_frame
        self.lifespan = lifespan
        self.peak_brightness = peak_brightness
        self.size = size
        self.drift_x = drift_x
        self.drift_y = drift_y
        self.attack_frames = attack_frames
        self.decay_frames = decay_frames

    def brightness_at(self, frame):
        """Get brightness at a given frame (0.0 - 1.0)."""
        age = frame - self.birth_frame
        if age < 0 or age >= self.lifespan:
            return 0.0

        # Attack phase
        if age < self.attack_frames:
            t = age / max(1, self.attack_frames)
            return self.peak_brightness * t

        # Sustain (between attack and decay)
        decay_start = self.lifespan - self.decay_frames
        if age < decay_start:
            return self.peak_brightness

        # Decay phase
        remaining = self.lifespan - age
        t = remaining / max(1, self.decay_frames)
        return self.peak_brightness * t

    def position_at(self, frame):
        """Get position at a given frame (with drift)."""
        age = frame - self.birth_frame
        return (self.x + self.drift_x * age,
                self.y + self.drift_y * age)


def _generate_point_pool(width, height, total_frames, seed,
                         density, size_min, size_max, style,
                         variation):
    """Pre-generate the entire pool of sparkle/twinkle points
    across all frames. This ensures temporal coherence."""

    random.seed(seed)
    points = []

    if style == 0:
        # SPARKLE mode: sharp attack, fast decay, scattered
        # Points are born across all frames, live 2-5 frames
        for frame in range(total_frames):
            # Number of new points born this frame
            count = random.randint(
                max(1, int(density * 0.5)),
                int(density * 1.5))

            for _ in range(count):
                x = random.uniform(0, width)
                y = random.uniform(0, height)
                lifespan = random.randint(2, max(3, min(5, total_frames // 2)))
                peak = random.uniform(0.6, 1.0)
                size = random.uniform(size_min, size_max)

                # Sparkles: instant attack (0-1 frames), fast decay
                attack = random.randint(0, 1)
                decay = lifespan - attack

                # Minimal drift — sparkles pop and fade in place
                drift_x = random.uniform(-0.3, 0.3) * variation
                drift_y = random.uniform(-0.5, -0.1) * variation  # slight upward

                points.append(SparkPoint(
                    x, y, frame, lifespan, peak, size,
                    drift_x, drift_y, attack, decay))
    else:
        # TWINKLE mode: soft fade in/out, longer life, gentle drift
        # Points are born in staggered waves, live 5-12 frames
        # Fewer new points per frame but they overlap more
        for frame in range(total_frames):
            count = random.randint(
                max(1, density // 4),
                max(2, density // 2))

            for _ in range(count):
                x = random.uniform(0, width)
                y = random.uniform(0, height)
                lifespan = random.randint(
                    max(4, total_frames // 4),
                    max(6, total_frames // 2))
                peak = random.uniform(0.4, 1.0)
                size = random.uniform(size_min, size_max)

                # Twinkle: soft attack, soft decay
                attack = max(1, lifespan // 3)
                decay = max(1, lifespan // 3)

                # Gentle drift
                drift_x = random.uniform(-0.2, 0.2) * variation
                drift_y = random.uniform(-0.2, 0.2) * variation

                points.append(SparkPoint(
                    x, y, frame, lifespan, peak, size,
                    drift_x, drift_y, attack, decay))

    return points


# ---------------------------------------------------------------------------
# Rendering primitives
# ---------------------------------------------------------------------------

def _render_point(canvas, width, height, cx, cy, size, glow_radius,
                  brightness):
    """Render a single glowing point onto the canvas.

    Uses a gaussian-like falloff for natural glow appearance.
    Renders in a bounding box around the point for efficiency.
    """
    if brightness <= 0.001:
        return

    # Bounding box with glow margin
    margin = int(glow_radius * 3) + 1
    x_min = max(0, int(cx - margin))
    x_max = min(width - 1, int(cx + margin))
    y_min = max(0, int(cy - margin))
    y_max = min(height - 1, int(cy + margin))

    # Two-layer rendering: bright core + soft glow
    for py in range(y_min, y_max + 1):
        for px in range(x_min, x_max + 1):
            dx = px - cx
            dy = py - cy
            dist_sq = dx * dx + dy * dy

            # Core: tight gaussian based on point size
            core_sigma_sq = size * size
            core = math.exp(-dist_sq / (2.0 * core_sigma_sq)) if core_sigma_sq > 0 else 0

            # Glow: wider gaussian
            glow_sigma_sq = glow_radius * glow_radius
            glow = math.exp(-dist_sq / (2.0 * glow_sigma_sq)) if glow_sigma_sq > 0 else 0

            # Combined intensity
            intensity = (core * 0.8 + glow * 0.3) * brightness

            if intensity > 0.001:
                idx = py * width + px
                # Additive blending
                canvas[idx] = min(1.0, canvas[idx] + intensity)


def _add_star_rays(canvas, width, height, cx, cy, size, brightness):
    """Add subtle 4-point star ray pattern for sparkle style.

    Creates the classic cross/star shape that reads as a light sparkle.
    Only used in sparkle mode, not twinkle.
    """
    if brightness < 0.3:
        return

    ray_length = int(size * 4)
    ray_brightness = brightness * 0.3

    # 4 rays: up, down, left, right
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        for step in range(1, ray_length + 1):
            px = int(cx + dx * step)
            py = int(cy + dy * step)
            if 0 <= px < width and 0 <= py < height:
                falloff = 1.0 - (step / ray_length)
                falloff = falloff * falloff  # quadratic falloff
                intensity = ray_brightness * falloff
                idx = py * width + px
                canvas[idx] = min(1.0, canvas[idx] + intensity)

    # 4 diagonal rays (half length, dimmer)
    diag_length = ray_length // 2
    diag_brightness = ray_brightness * 0.5
    for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        for step in range(1, diag_length + 1):
            px = int(cx + dx * step)
            py = int(cy + dy * step)
            if 0 <= px < width and 0 <= py < height:
                falloff = 1.0 - (step / diag_length)
                falloff = falloff * falloff
                intensity = diag_brightness * falloff
                idx = py * width + px
                canvas[idx] = min(1.0, canvas[idx] + intensity)


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

# Module-level cache for the point pool so it persists across frames
_cached_pool = None
_cached_pool_key = None


def generate(width, height, frame_index, total_frames, seed,
             style=0, density=30, size_min=1.0, size_max=3.5,
             glow_radius=4.0, color_r=255, color_g=240, color_b=200,
             intensity_variation=80, **_kwargs):
    """Generate a single frame of sparkles or twinkle.

    Args:
        width: Frame width in pixels
        height: Frame height in pixels
        frame_index: Which frame (0-based) in the sequence
        total_frames: Total number of frames being generated
        seed: Base random seed
        style: 0 = Sparkle (sharp bursts), 1 = Twinkle (gentle fade)
        density: Number of new points per frame
        size_min/max: Point radius range in pixels
        glow_radius: Bloom spread in pixels
        color_r/g/b: Point color (0-255)
        intensity_variation: 0-100, how much frames differ

    Returns:
        List of pixel values as [r, g, b, a, r, g, b, a, ...] (flat),
        length = width * height * 4. Values are 0-255 integers.
    """
    global _cached_pool, _cached_pool_key

    variation = intensity_variation / 100.0

    # Generate or retrieve the point pool (cached across frames)
    pool_key = (width, height, total_frames, seed, style, density,
                size_min, size_max, variation)

    if _cached_pool_key != pool_key:
        _cached_pool = _generate_point_pool(
            width, height, total_frames, seed,
            density, size_min, size_max, style, variation)
        _cached_pool_key = pool_key

    points = _cached_pool

    # Canvas: flat list of intensity floats (0.0 - 1.0)
    canvas = [0.0] * (width * height)

    # Render all points that are alive during this frame
    for point in points:
        brightness = point.brightness_at(frame_index)
        if brightness <= 0.001:
            continue

        px, py = point.position_at(frame_index)

        # Wrap into frame bounds
        px = px % width
        py = py % height

        # Render the glowing point
        _render_point(canvas, width, height, px, py,
                      point.size, glow_radius, brightness)

        # Add star rays for sparkle mode on bright points
        if style == 0 and brightness > 0.5 and point.size > size_min * 1.2:
            _add_star_rays(canvas, width, height, px, py,
                           point.size, brightness)

    # Colorize to RGBA
    pixels = []
    for i in range(width * height):
        g = canvas[i]
        if g < 0.001:
            pixels.extend([0, 0, 0, 0])  # Transparent
        else:
            # Color temperature ramp: dim = user color, bright = white-hot
            white_blend = min(1.0, g * g)

            r = min(255, int(color_r * g * (1.0 - white_blend * 0.3)
                             + 255 * white_blend * 0.7))
            gn = min(255, int(color_g * g * (1.0 - white_blend * 0.2)
                              + 255 * white_blend * 0.6))
            b = min(255, int(color_b * g * (1.0 - white_blend * 0.1)
                             + 255 * white_blend * 0.5))

            alpha = min(255, int(min(1.0, g) ** 0.5 * 255))
            pixels.extend([r, gn, b, alpha])

    return pixels


# ---------------------------------------------------------------------------
# Self-registration
# ---------------------------------------------------------------------------

register(
    name='sparkles',
    label='Sparkles & Twinkle',
    description='Animated sparkle bursts or gentle twinkle shimmer with star rays and glow.',
    get_params=get_params,
    generate=generate,
)
