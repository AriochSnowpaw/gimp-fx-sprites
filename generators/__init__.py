"""
FX Sprites — Generator Registry
Part of the Runestone Estate SL Materializer Suite
https://runed4life.com

This module provides the registry for effect generators.
New generators register themselves here and become available
in the GIMP plugin dialog automatically.
"""

# Registry: name -> {module, label, description, params_func, generate_func}
_generators = {}


def register(name, label, description, get_params, generate):
    """Register a new effect generator.

    Args:
        name: Internal identifier (e.g. 'electricity')
        label: Human-readable label for the UI dropdown
        description: Short description shown in the dialog
        get_params: Function returning list of parameter definitions
                    Each param: (type, key, label, description, default, min, max)
                    Types: 'int', 'float', 'color', 'choice'
        generate: Function(width, height, frame_index, total_frames, seed, **params)
                  Returns a list of [r, g, b, a] pixel rows (height x width x 4)
                  Values are 0-255 integers.
    """
    _generators[name] = {
        'label': label,
        'description': description,
        'get_params': get_params,
        'generate': generate,
    }


def get_generator(name):
    """Retrieve a registered generator by name."""
    return _generators.get(name)


def list_generators():
    """Return list of (name, label) tuples for all registered generators."""
    return [(name, info['label']) for name, info in _generators.items()]


def get_all():
    """Return the full registry dict."""
    return dict(_generators)
