package validate

import (
	"testing"

	"github.com/sketchos/validator-go/internal/aabb"
)

// boxFrom returns a non-empty AABB spanning the given min/max corners.
func boxFrom(minx, miny, minz, maxx, maxy, maxz float64) *aabb.AABB {
	a := aabb.New()
	a.Extend(minx, miny, minz)
	a.Extend(maxx, maxy, maxz)
	return a
}

func TestMeasureYAxisHeight(t *testing.T) {
	// A tall, thin wall: vertical extent on Y (3 m), long on Z (10 m), thin on
	// X. Height must come from Y, not Z; thickness is min(dx, dz).
	a := boxFrom(0, 0, 0, 0.25, 3, 10)
	height, thickness := Measure(a)
	if height != 3 {
		t.Errorf("height = %v, want 3 (Y extent, not Z extent of 10)", height)
	}
	if thickness != 0.25 {
		t.Errorf("thickness = %v, want 0.25 (min(dx,dz))", thickness)
	}
}

func TestNewWall(t *testing.T) {
	a := boxFrom(0, 0, 0, 0.25, 3, 10)
	w := NewWall("wall_1", a)
	if w.Name != "wall_1" {
		t.Errorf("Name = %q, want %q", w.Name, "wall_1")
	}
	if w.Height != 3 {
		t.Errorf("Height = %v, want 3", w.Height)
	}
	if w.Thickness != 0.25 {
		t.Errorf("Thickness = %v, want 0.25", w.Thickness)
	}
}

func TestDefaultThresholds(t *testing.T) {
	d := DefaultThresholds()
	if d.MinHeight != 2.0 {
		t.Errorf("MinHeight = %v, want 2.0", d.MinHeight)
	}
	if d.MinThickness != 0.1 {
		t.Errorf("MinThickness = %v, want 0.1", d.MinThickness)
	}
	if d.MaxHeight != 0 || d.MaxThickness != 0 {
		t.Errorf("max bounds = (%v, %v), want (0, 0) unenforced", d.MaxHeight, d.MaxThickness)
	}
}

func TestValidateWall(t *testing.T) {
	// Wall 3 m tall, 0.25 m thick — within defaults.
	ok := NewWall("wall_ok", boxFrom(0, 0, 0, 0.25, 3, 10))
	short := NewWall("wall_short", boxFrom(0, 0, 0, 0.25, 1.5, 10))
	tall := NewWall("wall_tall", boxFrom(0, 0, 0, 0.25, 100, 10))
	thin := NewWall("wall_thin", boxFrom(0, 0, 0, 0.05, 3, 10))
	thick := NewWall("wall_thick", boxFrom(0, 0, 0, 5, 3, 5))

	cases := []struct {
		name string
		w    Wall
		t    Thresholds
		want []Rule
	}{
		{"pass within defaults", ok, DefaultThresholds(), nil},
		{"height below min", short, DefaultThresholds(), []Rule{WallHeightMin}},
		{"height above max", tall, Thresholds{MinHeight: 2, MaxHeight: 50}, []Rule{WallHeightMax}},
		{"thickness below min", thin, DefaultThresholds(), []Rule{WallThicknessMin}},
		{"thickness above max", thick, Thresholds{MinThickness: 0.1, MaxThickness: 1}, []Rule{WallThicknessMax}},
		{"max unenforced when 0", tall, DefaultThresholds(), nil},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := ValidateWall(nil, tc.w, tc.t)
			if len(got) != len(tc.want) {
				t.Fatalf("got %d violations, want %d: %+v", len(got), len(tc.want), got)
			}
			for i, r := range tc.want {
				if got[i].Type != string(r) {
					t.Errorf("violation[%d].Type = %q, want %q", i, got[i].Type, r)
				}
			}
		})
	}
}

func TestValidateWallViolationFields(t *testing.T) {
	short := NewWall("wall_short", boxFrom(0, 0, 0, 0.25, 1.5, 10))
	got := ValidateWall(nil, short, DefaultThresholds())
	if len(got) != 1 {
		t.Fatalf("got %d violations, want 1", len(got))
	}
	v := got[0]
	if v.Type != string(WallHeightMin) {
		t.Errorf("Type = %q, want %q", v.Type, WallHeightMin)
	}
	if v.Object != "wall_short" {
		t.Errorf("Object = %q, want %q", v.Object, "wall_short")
	}
	if v.Measured != 1.5 {
		t.Errorf("Measured = %v, want 1.5", v.Measured)
	}
	if v.Threshold != 2.0 {
		t.Errorf("Threshold = %v, want 2.0", v.Threshold)
	}
	if v.Message == "" {
		t.Error("Message = empty, want non-empty")
	}
}

func TestClassify(t *testing.T) {
	cases := []struct {
		name string
		want Kind
	}{
		{"wall_1", KindWall},
		{"wall_north_exterior", KindWall},
		{"floor_1", KindFloor},
		{"volume_living_room", KindVolume},
		{"ceiling_1", KindOther},
		{"", KindOther},
		{"wall", KindOther}, // no underscore suffix: not wall-prefixed
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := Classify(tc.name); got != tc.want {
				t.Errorf("Classify(%q) = %v, want %v", tc.name, got, tc.want)
			}
		})
	}
}
