// Package validate applies geometric-regulation rules to AABB-derived wall
// measurements. It consumes the per-object bounding boxes produced by the
// objparse/aabb stages and emits structured Violations.
//
// Axis convention (Blender OBJ export): Y is up, so wall height is the Y
// extent (maxY - minY), never the Z extent. Wall thickness is min(dx, dz).
// Thickness is exact only for axis-aligned walls: a wall rotated about the Y
// axis inflates its AABB and therefore overestimates thickness. That is a
// documented caveat, not a silent mismatch.
package validate

import (
	"fmt"
	"strings"

	"github.com/sketchos/validator-go/internal/aabb"
)

// Rule is a geometric-regulation rule identifier.
type Rule string

// The four wall regulations this package enforces.
const (
	WallHeightMin    Rule = "wall_height_min"
	WallHeightMax    Rule = "wall_height_max"
	WallThicknessMin Rule = "wall_thickness_min"
	WallThicknessMax Rule = "wall_thickness_max"
)

// Thresholds holds the geometric-regulation limits. A value of 0 (or negative)
// means the bound is unenforced, matching the CLI convention where 0 disables a
// flag.
type Thresholds struct {
	MinHeight    float64
	MaxHeight    float64
	MinThickness float64
	MaxThickness float64
}

// DefaultThresholds returns the provisional defaults: min height 2.0 m and min
// thickness 0.1 m. Max bounds are 0 = unenforced. Final normativa values are a
// later product decision and arrive via CLI flags.
func DefaultThresholds() Thresholds {
	return Thresholds{
		MinHeight:    2.0,
		MaxHeight:    0,
		MinThickness: 0.1,
		MaxThickness: 0,
	}
}

// Violation describes a single failed geometric regulation.
type Violation struct {
	Type      string  `json:"type"`
	Object    string  `json:"object"`
	Measured  float64 `json:"measured"`
	Threshold float64 `json:"threshold"`
	Message   string  `json:"message"`
}

// Kind classifies an object by its Blender-export name prefix.
type Kind int

// Object kinds recognized by the name-prefix convention from the Blender
// client (_add_cube uses wall_/floor_/volume_).
const (
	KindOther Kind = iota
	KindWall
	KindFloor
	KindVolume
)

var kindPrefixes = []struct {
	kind   Kind
	prefix string
}{
	{KindWall, "wall_"},
	{KindFloor, "floor_"},
	{KindVolume, "volume_"},
}

// Classify returns the kind of object implied by its name.
func Classify(name string) Kind {
	for _, k := range kindPrefixes {
		if strings.HasPrefix(name, k.prefix) {
			return k.kind
		}
	}
	return KindOther
}

// Measure derives a box's wall height and thickness under the OBJ Y-up
// convention: height = maxY - minY, thickness = min(dx, dz). Thickness is
// exact only for axis-aligned walls; rotated walls inflate the AABB and
// overestimate thickness.
func Measure(a *aabb.AABB) (height, thickness float64) {
	dx, dy, dz := a.Dimensions()
	return dy, min(dx, dz)
}

// Wall is a named object with derived measurements.
type Wall struct {
	Name      string
	Height    float64
	Thickness float64
}

// NewWall derives a Wall from a named bounding box.
func NewWall(name string, a *aabb.AABB) Wall {
	h, th := Measure(a)
	return Wall{Name: name, Height: h, Thickness: th}
}

// ValidateWall appends any violations of t by w to dst and returns the
// extended slice. Callers should gate calls on Classify(w.Name) == Wall; this
// function applies wall regulations regardless.
func ValidateWall(dst []Violation, w Wall, t Thresholds) []Violation {
	if t.MinHeight > 0 && w.Height < t.MinHeight {
		dst = append(dst, newViolation(WallHeightMin, w, w.Height, t.MinHeight))
	}
	if t.MaxHeight > 0 && w.Height > t.MaxHeight {
		dst = append(dst, newViolation(WallHeightMax, w, w.Height, t.MaxHeight))
	}
	if t.MinThickness > 0 && w.Thickness < t.MinThickness {
		dst = append(dst, newViolation(WallThicknessMin, w, w.Thickness, t.MinThickness))
	}
	if t.MaxThickness > 0 && w.Thickness > t.MaxThickness {
		dst = append(dst, newViolation(WallThicknessMax, w, w.Thickness, t.MaxThickness))
	}
	return dst
}

func newViolation(rule Rule, w Wall, measured, threshold float64) Violation {
	return Violation{
		Type:      string(rule),
		Object:    w.Name,
		Measured:  measured,
		Threshold: threshold,
		Message: fmt.Sprintf(
			"%s: object %q measured %.3f m, limit %.3f m",
			rule, w.Name, measured, threshold,
		),
	}
}
