"""ArchitecturalDSL: pure Pydantic v2 domain models for SketchOS.

This module has no I/O and no dependency on MCP or Blender. It is the
validation boundary: an invalid DSL instance never reaches Blender because
``build_architecture`` validates against these models before generating or
executing any Blender code.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Vec3(BaseModel):
    """A point or vector in 3D space."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float
    z: float


class Wall(BaseModel):
    """A vertical architectural element defined by start/end points and dims."""

    model_config = ConfigDict(extra="forbid")

    id: str
    start: Vec3
    end: Vec3
    height: float = Field(gt=0)
    thickness: float = Field(gt=0)


class Floor(BaseModel):
    """A horizontal slab defined by a closed outline."""

    model_config = ConfigDict(extra="forbid")

    id: str
    outline: list[Vec3]
    thickness: float = Field(gt=0)
    elevation: float = 0


class Opening(BaseModel):
    """An opening (door/window) placed on a wall."""

    model_config = ConfigDict(extra="forbid")

    id: str
    wall_id: str
    position: Vec3
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class Volume(BaseModel):
    """A volumetric element (room/box) defined by origin and size."""

    model_config = ConfigDict(extra="forbid")

    id: str
    origin: Vec3
    size: Vec3


class Relationship(BaseModel):
    """A named relation between two elements."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    target_id: str
    kind: Literal["contains", "adjacent", "opening_in"]


class ArchitectureModel(BaseModel):
    """Top-level architectural model composed of elements and relationships."""

    model_config = ConfigDict(extra="forbid")

    walls: list[Wall]
    floors: list[Floor]
    openings: list[Opening]
    volumes: list[Volume]
    relationships: list[Relationship]
