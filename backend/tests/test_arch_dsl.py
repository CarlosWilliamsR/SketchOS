"""Unit tests for the ArchitecturalDSL Pydantic models (arch_dsl.py)."""

import pytest
from pydantic import ValidationError

from sketchos_backend.arch_dsl import (
    ArchitectureModel,
    Floor,
    Opening,
    Relationship,
    Vec3,
    Volume,
    Wall,
)


def make_valid_model() -> ArchitectureModel:
    """Return a minimal, fully valid architectural model."""
    return ArchitectureModel(
        walls=[
            Wall(
                id="w1",
                start=Vec3(x=0, y=0, z=0),
                end=Vec3(x=5, y=0, z=0),
                height=3,
                thickness=0.25,
            )
        ],
        floors=[
            Floor(
                id="f1",
                outline=[
                    Vec3(x=0, y=0, z=0),
                    Vec3(x=5, y=0, z=0),
                    Vec3(x=5, y=5, z=0),
                    Vec3(x=0, y=5, z=0),
                ],
                thickness=0.2,
                elevation=0,
            )
        ],
        openings=[
            Opening(
                id="o1",
                wall_id="w1",
                position=Vec3(x=2.5, y=0, z=1),
                width=1,
                height=2.1,
            )
        ],
        volumes=[
            Volume(id="v1", origin=Vec3(x=0, y=0, z=0), size=Vec3(x=5, y=5, z=3))
        ],
        relationships=[
            Relationship(source_id="w1", target_id="f1", kind="adjacent"),
            Relationship(source_id="o1", target_id="w1", kind="opening_in"),
        ],
    )


def test_valid_model_parses():
    model = make_valid_model()
    assert len(model.walls) == 1
    assert model.walls[0].id == "w1"
    assert model.floors[0].id == "f1"
    assert model.openings[0].id == "o1"


def test_wall_negative_height_rejected():
    with pytest.raises(ValidationError):
        Wall(
            id="w1",
            start=Vec3(x=0, y=0, z=0),
            end=Vec3(x=5, y=0, z=0),
            height=-3,
            thickness=0.25,
        )


def test_wall_negative_thickness_rejected():
    with pytest.raises(ValidationError):
        Wall(
            id="w1",
            start=Vec3(x=0, y=0, z=0),
            end=Vec3(x=5, y=0, z=0),
            height=3,
            thickness=-0.25,
        )


def test_floor_negative_thickness_rejected():
    with pytest.raises(ValidationError):
        Floor(
            id="f1",
            outline=[Vec3(x=0, y=0, z=0), Vec3(x=1, y=0, z=0)],
            thickness=-0.2,
        )


def test_opening_negative_dimension_rejected():
    with pytest.raises(ValidationError):
        Opening(
            id="o1",
            wall_id="w1",
            position=Vec3(x=1, y=0, z=1),
            width=-1,
            height=2.1,
        )


def test_missing_required_field_rejected():
    # Floor requires `thickness`; omitting it must fail validation.
    with pytest.raises(ValidationError):
        Floor(id="f1", outline=[Vec3(x=0, y=0, z=0), Vec3(x=1, y=0, z=0)])


def test_extra_field_forbidden():
    with pytest.raises(ValidationError):
        Wall(
            id="w1",
            start=Vec3(x=0, y=0, z=0),
            end=Vec3(x=5, y=0, z=0),
            height=3,
            thickness=0.25,
            material="brick",
        )


def test_json_round_trip_equality():
    original = make_valid_model()
    restored = ArchitectureModel.model_validate_json(original.model_dump_json())
    assert restored == original


def test_json_round_trip_field_values():
    original = make_valid_model()
    restored = ArchitectureModel.model_validate_json(original.model_dump_json())
    assert restored.walls[0].height == 3
    assert restored.floors[0].thickness == 0.2
    assert restored.relationships[0].kind == "adjacent"
