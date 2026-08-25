"""Unit tests for arch_macros: pure, deterministic bpy code emission."""

import inspect
import math

from sketchos_backend.arch_dsl import Opening, Vec3, Wall
from sketchos_backend import arch_macros as am


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def make_axis_aligned_wall() -> Wall:
    """A wall along +X (rotation 0)."""
    return Wall(id="w1", start=Vec3(x=0, y=0, z=0), end=Vec3(x=5, y=0, z=0), height=3, thickness=0.25)


def make_angled_wall() -> Wall:
    """A non-axis-aligned wall: dx=4, dy=3 -> rotation atan2(3, 4)."""
    return Wall(id="w1", start=Vec3(x=0, y=0, z=0), end=Vec3(x=4, y=3, z=0), height=3, thickness=0.25)


def make_opening() -> Opening:
    return Opening(id="o1", wall_id="w1", position=Vec3(x=2.5, y=0, z=1), width=1, height=2.1)


# --------------------------------------------------------------------------- #
# R1 — Deterministic emission, no Blender import
# --------------------------------------------------------------------------- #


def test_module_imports_without_blender():
    """Importing arch_macros must not pull in or reference ``bpy``."""
    source = inspect.getsource(am)
    assert "import bpy" not in source
    assert "from bpy" not in source
    assert not hasattr(am, "bpy")


def test_emission_is_deterministic():
    wall = make_angled_wall()
    opening = make_opening()

    assert am.wall_rotation(wall) == am.wall_rotation(wall)
    assert am.cutter_params(wall, opening) == am.cutter_params(wall, opening)
    assert am.emit_boolean_header() == am.emit_boolean_header()
    assert am.emit_opening_cutout(wall, opening) == am.emit_opening_cutout(wall, opening)
    assert am.emit_export_obj("/tmp/out.obj") == am.emit_export_obj("/tmp/out.obj")


# --------------------------------------------------------------------------- #
# R2 — Boolean DIFFERENCE cutter: overextend + shared rotation
# --------------------------------------------------------------------------- #


def test_cutter_overextends_wall_thickness():
    wall = make_axis_aligned_wall()
    opening = make_opening()
    _, size, _ = am.cutter_params(wall, opening)
    # Depth is the second size component (cut axis).
    assert size[1] == wall.thickness + am.OPENING_OVEREXTEND
    assert size[1] > wall.thickness


def test_cutter_params_center_z_on_opening():
    wall = make_axis_aligned_wall()
    opening = make_opening()
    location, _, _ = am.cutter_params(wall, opening)
    assert location[2] == opening.position.z + opening.height / 2.0


def test_wall_rotation_is_atan2():
    wall = make_angled_wall()
    assert am.wall_rotation(wall) == math.atan2(3.0, 4.0)


def test_cutter_shares_wall_rotation():
    wall = make_angled_wall()
    opening = make_opening()
    _, _, rotation_z = am.cutter_params(wall, opening)
    assert rotation_z == am.wall_rotation(wall)
    assert rotation_z == math.atan2(3.0, 4.0)


def test_angled_wall_cutout_emits_rotated_cutter():
    wall = make_angled_wall()
    opening = make_opening()
    code = am.emit_opening_cutout(wall, opening)
    assert '_add_cube("cutter_o1"' in code
    # rotation value == atan2(3, 4) formatted the same way blender_client does
    assert f", {am._fmt(math.atan2(3.0, 4.0))})" in code


def test_cutout_emits_cutter_and_boolean_difference():
    wall = make_axis_aligned_wall()
    opening = make_opening()
    code = am.emit_opening_cutout(wall, opening)
    assert '_add_cube("cutter_o1", (2.5, 0, 2.05), (1, 0.45, 2.1), 0)' in code
    assert '_boolean_difference("wall_w1", "cutter_o1", "opening_o1")' in code


# --------------------------------------------------------------------------- #
# R2 / R3 — self-contained helper definition + apply-then-delete ordering
# --------------------------------------------------------------------------- #


def test_boolean_header_defines_difference_helper():
    header = am.emit_boolean_header()
    assert header.startswith("def _boolean_difference(")
    assert "target.modifiers.new(name=mod_name, type='BOOLEAN')" in header
    assert "mod.operation = 'DIFFERENCE'" in header
    assert "mod.object = cutter" in header
    assert "bpy.ops.object.modifier_apply(modifier=mod_name)" in header
    assert "bpy.data.objects.remove(cutter, do_unlink=True)" in header


def test_boolean_header_applies_before_delete():
    header = am.emit_boolean_header()
    assert header.index("modifier_apply") < header.index("objects.remove")


# --------------------------------------------------------------------------- #
# R3 — single-script execution in a fresh namespace (fake bpy)
# --------------------------------------------------------------------------- #

_ADD_CUBE = """def _add_cube(name, location, size, rotation_z=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    obj.rotation_euler = (0.0, 0.0, rotation_z)"""


class _FakeModifier:
    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.operation = None
        self.object = None


class _FakeModifiers:
    def __init__(self, bpy):
        self._bpy = bpy

    def new(self, name=None, type=None):
        self._bpy.events.append(("modifiers.new", name, type))
        return _FakeModifier(name, type)


class _FakeObject:
    def __init__(self, bpy):
        self._bpy = bpy
        self._name = "Cube"
        self.scale = None
        self.rotation_euler = None
        self.modifiers = _FakeModifiers(bpy)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self._bpy.data.objects._by_name[value] = self


class _FakeObjects:
    def __init__(self, bpy):
        self._bpy = bpy
        self._by_name = {}

    def __getitem__(self, name):
        return self._by_name[name]

    def remove(self, obj, do_unlink=True):
        self._bpy.events.append(("objects.remove", obj.name))


class _FakeData:
    def __init__(self, bpy):
        self.objects = _FakeObjects(bpy)


class _FakeViewLayerObjects:
    def __init__(self, bpy):
        self._bpy = bpy
        self.active = None


class _FakeViewLayer:
    def __init__(self, bpy):
        self.objects = _FakeViewLayerObjects(bpy)


class _FakeContext:
    def __init__(self, bpy):
        self._bpy = bpy
        self.active_object = None
        self.view_layer = _FakeViewLayer(bpy)


class _FakeMeshOps:
    def __init__(self, bpy):
        self._bpy = bpy

    def primitive_cube_add(self, size=1.0, location=None):
        obj = _FakeObject(self._bpy)
        self._bpy.data.objects._by_name[obj.name] = obj
        self._bpy.context.active_object = obj
        self._bpy.events.append(("primitive_cube_add", location))


class _FakeObjectOps:
    def __init__(self, bpy):
        self._bpy = bpy

    def modifier_apply(self, modifier=None):
        self._bpy.events.append(("modifier_apply", modifier))


class _FakeWmOps:
    def __init__(self, bpy):
        self._bpy = bpy

    def obj_export(self, filepath=None):
        self._bpy.events.append(("obj_export", filepath))


class _FakeOps:
    def __init__(self, bpy):
        self.mesh = _FakeMeshOps(bpy)
        self.object = _FakeObjectOps(bpy)
        self.wm = _FakeWmOps(bpy)


class _FakeBpy:
    def __init__(self):
        self.events = []
        self.data = _FakeData(self)
        self.context = _FakeContext(self)
        self.ops = _FakeOps(self)


def _run_script(script: str) -> _FakeBpy:
    """Exec ``script`` in a fresh namespace with a fake ``bpy`` and return it."""
    fake = _FakeBpy()
    exec(script, {"bpy": fake})  # noqa: S102 - mirrors blender-mcp exec contract
    return fake


def _compose_script() -> str:
    """Compose the macros into one self-contained script, as blender_client will."""
    wall = make_axis_aligned_wall()
    opening = make_opening()
    return "\n".join(
        (
            _ADD_CUBE,
            '_add_cube("wall_w1", (2.5, 0, 1.5), (5, 0.25, 3), 0)',
            am.emit_boolean_header(),
            am.emit_opening_cutout(wall, opening),
            am.emit_export_obj("/tmp/out.obj"),
        )
    )


def test_single_script_runs_in_fresh_namespace():
    fake = _run_script(_compose_script())
    names = [event[0] for event in fake.events]
    assert "primitive_cube_add" in names
    assert "modifier_apply" in names
    assert "objects.remove" in names
    assert "obj_export" in names


def test_script_orders_apply_then_delete_then_export():
    fake = _run_script(_compose_script())
    names = [event[0] for event in fake.events]
    apply_idx = names.index("modifier_apply")
    delete_idx = names.index("objects.remove")
    export_idx = names.index("obj_export")
    assert apply_idx < delete_idx < export_idx


def test_script_uses_no_cross_call_state():
    # Two independent executions must not share any state.
    first = _run_script(_compose_script())
    second = _run_script(_compose_script())
    assert first.events == second.events
    assert first is not second


# --------------------------------------------------------------------------- #
# R4 — OBJ export preparation
# --------------------------------------------------------------------------- #


def test_export_emits_wm_obj_export_with_filepath():
    code = am.emit_export_obj("/tmp/model.obj")
    assert "bpy.ops.wm.obj_export" in code
    assert 'filepath="/tmp/model.obj"' in code


def test_export_filepath_is_json_quoted():
    code = am.emit_export_obj('C:\\meshes\\my "model".obj')
    assert 'filepath="C:\\\\meshes\\\\my \\"model\\".obj"' in code
    assert "bpy.ops.wm.obj_export" in code
