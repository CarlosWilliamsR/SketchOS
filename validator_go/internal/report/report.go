// Package report serializes a validation result as deterministic JSON.
//
// Field ordering is fixed by struct declaration order (aabb, objects,
// violations), which encoding/json preserves, so the emitted bytes are stable
// and diff-friendly. Nil slices are normalized to empty slices so they encode
// as [] rather than null.
package report

import (
	"encoding/json"
	"io"

	"github.com/sketchos/validator-go/internal/aabb"
	"github.com/sketchos/validator-go/internal/validate"
)

// Vec3 is a JSON-serializable 3D point.
type Vec3 struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
	Z float64 `json:"z"`
}

// Dims is a JSON-serializable extent (dx, dy, dz).
type Dims struct {
	DX float64 `json:"dx"`
	DY float64 `json:"dy"`
	DZ float64 `json:"dz"`
}

// AABB is the JSON representation of a bounding box: six scalars plus
// dimensions.
type AABB struct {
	Min        Vec3 `json:"min"`
	Max        Vec3 `json:"max"`
	Dimensions Dims `json:"dimensions"`
}

// ObjectMeasurement is a per-object entry in the report.
type ObjectMeasurement struct {
	Name      string  `json:"name"`
	Height    float64 `json:"height"`
	Thickness float64 `json:"thickness"`
}

// Report is the top-level JSON document. Field order is fixed (aabb, objects,
// violations) so encoding is deterministic.
type Report struct {
	AABB       AABB                 `json:"aabb"`
	Objects    []ObjectMeasurement  `json:"objects"`
	Violations []validate.Violation `json:"violations"`
}

// NewReport builds a Report from a global AABB, per-object measurements, and
// violations. Nil slices are normalized to empty so they serialize as [] rather
// than null.
func NewReport(a *aabb.AABB, objects []ObjectMeasurement, violations []validate.Violation) Report {
	dx, dy, dz := a.Dimensions()
	r := Report{
		AABB: AABB{
			Min:        Vec3{X: a.MinX, Y: a.MinY, Z: a.MinZ},
			Max:        Vec3{X: a.MaxX, Y: a.MaxY, Z: a.MaxZ},
			Dimensions: Dims{DX: dx, DY: dy, DZ: dz},
		},
		Objects:    objects,
		Violations: violations,
	}
	if r.Objects == nil {
		r.Objects = []ObjectMeasurement{}
	}
	if r.Violations == nil {
		r.Violations = []validate.Violation{}
	}
	return r
}

// ThresholdsJSON is the JSON representation of the normativa thresholds,
// emitted by -print-defaults. Field order is fixed (min_height, max_height,
// min_thickness, max_thickness) so encoding is deterministic.
type ThresholdsJSON struct {
	MinHeight    float64 `json:"min_height"`
	MaxHeight    float64 `json:"max_height"`
	MinThickness float64 `json:"min_thickness"`
	MaxThickness float64 `json:"max_thickness"`
}

// WriteDefaults encodes the normativa thresholds t as JSON and writes it to w,
// followed by a newline. A value of 0 encodes as 0, signalling an unenforced
// bound.
func WriteDefaults(w io.Writer, t validate.Thresholds) error {
	enc := json.NewEncoder(w)
	return enc.Encode(ThresholdsJSON{
		MinHeight:    t.MinHeight,
		MaxHeight:    t.MaxHeight,
		MinThickness: t.MinThickness,
		MaxThickness: t.MaxThickness,
	})
}

// Marshal encodes r as JSON. Field ordering is deterministic (struct
// declaration order) and empty slices encode as [].
func Marshal(r Report) ([]byte, error) {
	return json.Marshal(r)
}

// Write encodes r and writes it to w, followed by a newline.
func Write(w io.Writer, r Report) error {
	enc := json.NewEncoder(w)
	return enc.Encode(r)
}

// ExitCode returns the process exit code for a validation result: 0 when there
// are no violations, 1 otherwise. Parse errors (exit 2) are handled by main.
func ExitCode(violations []validate.Violation) int {
	if len(violations) == 0 {
		return 0
	}
	return 1
}
