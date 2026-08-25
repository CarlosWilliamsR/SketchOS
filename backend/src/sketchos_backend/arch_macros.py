"""Pure bpy code-emitting macros for CSG boolean cutouts and OBJ export.

This module imports **no Blender** and performs **no runtime I/O**: every
function returns a deterministic string of Blender Python (bpy) source that
``blender_client.generate_blender_code`` composes into one self-contained
script. Because blender-mcp runs each generated script under a fresh
``exec(code, {"bpy": bpy})`` namespace, the macros below emit their helpers
inline (see :func:`emit_boolean_header`) so nothing depends on cross-call
state.

The float formatting mirrors ``blender_client``'s ``_fmt``/``_vec`` helpers so
cutter strings are byte-consistent with the wall/floor/volume boxes emitted
elsewhere.

Mesh extrusion is intentionally deferred (floors remain bounding-box slabs);
the module leaves room for a future ``emit_mesh_extrude`` helper without
shipping a dead stub.
"""

from __future__ import annotations

import json
import math

from sketchos_backend.arch_dsl import Opening, Wall

#: Extra depth added past the wall thickness so a cutter clears both wall
#: faces and avoids coplanar/degenerate boolean faces. Cutter depth is
#: ``wall.thickness + OPENING_OVEREXTEND``.
OPENING_OVEREXTEND: float = 0.2


def _fmt(value: float) -> str:
    """Format a float deterministically with trailing zeros stripped."""
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _vec(values: tuple[float, float, float]) -> str:
    """Format a 3-tuple as a bpy-style ``(x, y, z)`` literal."""
    return "(" + ", ".join(_fmt(v) for v in values) + ")"


def _cube_line(
    name: str,
    location: tuple[float, float, float],
    size: tuple[float, float, float],
    rotation_z: float = 0.0,
) -> str:
    """Emit an ``_add_cube(...)`` call matching the generated-script header."""
    return f"_add_cube({json.dumps(name)}, {_vec(location)}, {_vec(size)}, {_fmt(rotation_z)})"


def wall_rotation(wall: Wall) -> float:
    """Return the wall's in-plane rotation angle ``atan2(dy, dx)`` in radians."""
    dx = wall.end.x - wall.start.x
    dy = wall.end.y - wall.start.y
    return math.atan2(dy, dx)


def cutter_params(
    wall: Wall, opening: Opening
) -> tuple[tuple[float, float, float], tuple[float, float, float], float]:
    """Return ``(location, size, rotation_z)`` for an opening's cutter box.

    The cutter is centered on the opening: horizontally at ``opening.position``
    and vertically at ``position.z + height / 2``. Its depth overextends the
    wall thickness by :data:`OPENING_OVEREXTEND` and it shares the wall's
    ``atan2(dy, dx)`` rotation so the boolean DIFFERENCE aligns with the wall.
    """
    location = (opening.position.x, opening.position.y, opening.position.z + opening.height / 2.0)
    depth = wall.thickness + OPENING_OVEREXTEND
    size = (opening.width, depth, opening.height)
    return location, size, wall_rotation(wall)


def emit_boolean_header() -> str:
    """Emit the inline ``_boolean_difference`` helper definition.

    The helper sets the target wall active, adds a ``BOOLEAN`` modifier with
    ``operation='DIFFERENCE'`` targeting the cutter, applies the modifier, then
    deletes the cutter. Apply-then-delete order is fixed and deterministic.
    """
    return '''def _boolean_difference(target_name, cutter_name, mod_name):
    target = bpy.data.objects[target_name]
    cutter = bpy.data.objects[cutter_name]
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new(name=mod_name, type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod_name)
    bpy.data.objects.remove(cutter, do_unlink=True)'''


def emit_opening_cutout(wall: Wall, opening: Opening) -> str:
    """Emit a cutter box plus a ``_boolean_difference`` call for ``opening``.

    The emitted script creates ``cutter_<opening.id>`` (rotated to the wall
    angle, overextended past the wall thickness) and then cuts it out of
    ``wall_<wall.id>`` with a ``BOOLEAN`` ``DIFFERENCE`` modifier named
    ``opening_<opening.id>``.
    """
    location, size, rotation_z = cutter_params(wall, opening)
    cutter_name = f"cutter_{opening.id}"
    wall_name = f"wall_{wall.id}"
    mod_name = f"opening_{opening.id}"
    return "\n".join(
        (
            _cube_line(cutter_name, location, size, rotation_z),
            f"_boolean_difference({json.dumps(wall_name)}, {json.dumps(cutter_name)}, {json.dumps(mod_name)})",
        )
    )


def emit_export_obj(filepath: str) -> str:
    """Emit a Blender 4.x ``bpy.ops.wm.obj_export`` call for ``filepath``.

    The filepath is embedded via :func:`json.dumps` so it is safely quoted and
    forwarded verbatim (never executed).
    """
    return f"bpy.ops.wm.obj_export(filepath={json.dumps(filepath)})"
