package aabb

import (
	"math"
	"testing"
)

func TestAABBAxisAlignedBox(t *testing.T) {
	box := New()
	// A 2 x 3 x 4 box anchored at (1, 2, 3).
	for _, v := range [][3]float64{
		{1, 2, 3}, {3, 2, 3}, {3, 5, 3}, {1, 5, 3}, // bottom face
		{1, 2, 7}, {3, 2, 7}, {3, 5, 7}, {1, 5, 7}, // top face
	} {
		box.Extend(v[0], v[1], v[2])
	}

	assertScalar(t, "MinX", box.MinX, 1)
	assertScalar(t, "MinY", box.MinY, 2)
	assertScalar(t, "MinZ", box.MinZ, 3)
	assertScalar(t, "MaxX", box.MaxX, 3)
	assertScalar(t, "MaxY", box.MaxY, 5)
	assertScalar(t, "MaxZ", box.MaxZ, 7)

	dx, dy, dz := box.Dimensions()
	assertScalar(t, "dx", dx, 2)
	assertScalar(t, "dy", dy, 3)
	assertScalar(t, "dz", dz, 4)
}

func TestAABBNonAxisAlignedWall(t *testing.T) {
	// A unit square wall in the XZ plane, rotated 45° about Y (the up axis).
	// Its true AABB grows beyond the unrotated unit extents.
	cos := math.Sqrt2 / 2
	sin := math.Sqrt2 / 2
	box := New()
	for _, v := range [][3]float64{
		{0, 0, 0}, {1, 0, 0}, {1, 0, 1}, {0, 0, 1}, // base
		{0, 3, 0}, {1, 3, 0}, {1, 3, 1}, {0, 3, 1}, // top
	} {
		// Rotate about Y: x' = x*cos + z*sin, z' = -x*sin + z*cos.
		xr := v[0]*cos + v[2]*sin
		zr := -v[0]*sin + v[2]*cos
		box.Extend(xr, v[1], zr)
	}

	// Y is the wall height axis and is unaffected by the rotation.
	assertScalar(t, "MinY", box.MinY, 0)
	assertScalar(t, "MaxY", box.MaxY, 3)

	// X extent: the rotated unit square spans [min(x'), max(x')].
	// x' takes values {0, cos, cos+sin, sin} = {0, .707, 1.414, .707}.
	assertScalar(t, "MinX", box.MinX, 0)
	if math.Abs(box.MaxX-(cos+sin)) > 1e-9 {
		t.Errorf("MaxX = %v, want %v", box.MaxX, cos+sin)
	}
	// Z extent: z' takes values {0, -sin, cos-sin, cos} = {0, -.707, 0, .707}.
	if math.Abs(box.MinZ-(-sin)) > 1e-9 {
		t.Errorf("MinZ = %v, want %v", box.MinZ, -sin)
	}
	if math.Abs(box.MaxZ-cos) > 1e-9 {
		t.Errorf("MaxZ = %v, want %v", box.MaxZ, cos)
	}

	dx, dy, dz := box.Dimensions()
	assertScalar(t, "dy (wall height)", dy, 3)
	if math.Abs(dx-(cos+sin)) > 1e-9 {
		t.Errorf("dx = %v, want %v", dx, cos+sin)
	}
	if math.Abs(dz-(cos+sin)) > 1e-9 {
		t.Errorf("dz = %v, want %v", dz, cos+sin)
	}
}

func TestAABBEmptyDimensions(t *testing.T) {
	box := New()
	dx, dy, dz := box.Dimensions()
	// Empty box: max - min with +Inf/-Inf yields -Inf.
	if !math.IsInf(dx, -1) || !math.IsInf(dy, -1) || !math.IsInf(dz, -1) {
		t.Errorf("empty Dimensions() = (%v, %v, %v), want all -Inf", dx, dy, dz)
	}
}

func assertScalar(t *testing.T, name string, got, want float64) {
	t.Helper()
	if math.Abs(got-want) > 1e-12 {
		t.Errorf("%s = %v, want %v", name, got, want)
	}
}
