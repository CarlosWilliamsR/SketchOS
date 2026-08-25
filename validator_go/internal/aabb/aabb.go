// Package aabb provides an Axis-Aligned Bounding Box with online single-pass
// accumulation. It is a pure leaf: no dependencies on other internal packages.
package aabb

import "math"

// AABB is an axis-aligned bounding box over 3D vertices. The box is empty until
// the first vertex is accumulated. It uses the OBJ file's native axis
// convention (Blender export: Y is up).
type AABB struct {
	MinX, MinY, MinZ float64
	MaxX, MaxY, MaxZ float64
}

// New returns an empty AABB. Accumulate vertices with Extend; Dimensions is
// only meaningful once at least one vertex has been added.
func New() *AABB {
	return &AABB{
		MinX: math.Inf(1), MinY: math.Inf(1), MinZ: math.Inf(1),
		MaxX: math.Inf(-1), MaxY: math.Inf(-1), MaxZ: math.Inf(-1),
	}
}

// Extend grows the box to include the vertex (x, y, z) in a single pass.
func (a *AABB) Extend(x, y, z float64) {
	if x < a.MinX {
		a.MinX = x
	}
	if x > a.MaxX {
		a.MaxX = x
	}
	if y < a.MinY {
		a.MinY = y
	}
	if y > a.MaxY {
		a.MaxY = y
	}
	if z < a.MinZ {
		a.MinZ = z
	}
	if z > a.MaxZ {
		a.MaxZ = z
	}
}

// Dimensions returns the extent of the box along each axis (dx, dy, dz).
func (a *AABB) Dimensions() (dx, dy, dz float64) {
	return a.MaxX - a.MinX, a.MaxY - a.MinY, a.MaxZ - a.MinZ
}
