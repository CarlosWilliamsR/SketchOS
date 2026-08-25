package report

import (
	"bytes"
	"encoding/json"
	"flag"
	"os"
	"path/filepath"
	"testing"

	"github.com/sketchos/validator-go/internal/aabb"
	"github.com/sketchos/validator-go/internal/validate"
)

var update = flag.Bool("update", false, "update golden files")

// sampleReport builds a deterministic report with a global AABB, one object,
// and one violation, used by both the shape and golden tests.
func sampleReport() Report {
	box := aabb.New()
	box.Extend(0, 0, 0)
	box.Extend(10.25, 3, 5)
	objects := []ObjectMeasurement{
		{Name: "wall_1", Height: 3, Thickness: 0.25},
	}
	violations := []validate.Violation{
		{Type: "wall_height_min", Object: "wall_1", Measured: 1.5, Threshold: 2, Message: "wall \"wall_1\" height below minimum"},
	}
	return NewReport(box, objects, violations)
}

func TestReportJSONShape(t *testing.T) {
	b, err := Marshal(sampleReport())
	if err != nil {
		t.Fatalf("Marshal() error = %v, want nil", err)
	}

	var got map[string]json.RawMessage
	if err := json.Unmarshal(b, &got); err != nil {
		t.Fatalf("Unmarshal() error = %v", err)
	}
	for _, key := range []string{"aabb", "objects", "violations"} {
		if _, ok := got[key]; !ok {
			t.Errorf("missing top-level key %q", key)
		}
	}

	var doc struct {
		AABB struct {
			Min struct {
				X, Y, Z float64
			} `json:"min"`
			Max struct {
				X, Y, Z float64
			} `json:"max"`
			Dimensions struct {
				DX, DY, DZ float64
			} `json:"dimensions"`
		} `json:"aabb"`
		Objects []struct {
			Name      string  `json:"name"`
			Height    float64 `json:"height"`
			Thickness float64 `json:"thickness"`
		} `json:"objects"`
		Violations []struct {
			Type      string  `json:"type"`
			Object    string  `json:"object"`
			Measured  float64 `json:"measured"`
			Threshold float64 `json:"threshold"`
			Message   string  `json:"message"`
		} `json:"violations"`
	}
	if err := json.Unmarshal(b, &doc); err != nil {
		t.Fatalf("Unmarshal() error = %v", err)
	}

	// Global AABB: 6 scalars + dimensions.
	if doc.AABB.Min.X != 0 || doc.AABB.Min.Y != 0 || doc.AABB.Min.Z != 0 {
		t.Errorf("aabb.min = %+v, want {0 0 0}", doc.AABB.Min)
	}
	if doc.AABB.Max.X != 10.25 || doc.AABB.Max.Y != 3 || doc.AABB.Max.Z != 5 {
		t.Errorf("aabb.max = %+v, want {10.25 3 5}", doc.AABB.Max)
	}
	if doc.AABB.Dimensions.DX != 10.25 || doc.AABB.Dimensions.DY != 3 || doc.AABB.Dimensions.DZ != 5 {
		t.Errorf("aabb.dimensions = %+v, want {10.25 3 5}", doc.AABB.Dimensions)
	}

	// Objects.
	if len(doc.Objects) != 1 {
		t.Fatalf("len(objects) = %d, want 1", len(doc.Objects))
	}
	if o := doc.Objects[0]; o.Name != "wall_1" || o.Height != 3 || o.Thickness != 0.25 {
		t.Errorf("objects[0] = %+v, want {wall_1 3 0.25}", o)
	}

	// Violations.
	if len(doc.Violations) != 1 {
		t.Fatalf("len(violations) = %d, want 1", len(doc.Violations))
	}
	if v := doc.Violations[0]; v.Type != "wall_height_min" || v.Object != "wall_1" || v.Measured != 1.5 || v.Threshold != 2 {
		t.Errorf("violations[0] = %+v, want type=wall_height_min object=wall_1 measured=1.5 threshold=2", v)
	}
}

func TestReportEmptyListsSerializeAsArrays(t *testing.T) {
	box := aabb.New()
	box.Extend(0, 0, 0)
	box.Extend(1, 1, 1)

	b, err := Marshal(NewReport(box, nil, nil))
	if err != nil {
		t.Fatalf("Marshal() error = %v", err)
	}

	var got struct {
		Objects    []json.RawMessage `json:"objects"`
		Violations []json.RawMessage `json:"violations"`
	}
	if err := json.Unmarshal(b, &got); err != nil {
		t.Fatalf("Unmarshal() error = %v", err)
	}
	if got.Objects == nil {
		t.Error("objects serialized as null, want []")
	}
	if got.Violations == nil {
		t.Error("violations serialized as null, want []")
	}
}

// TestWriteDefaultsShape serializes validate.DefaultThresholds() and asserts
// the four threshold keys with their expected numeric values, plus the
// unenforced bounds encoding as 0.
func TestWriteDefaultsShape(t *testing.T) {
	var buf bytes.Buffer
	if err := WriteDefaults(&buf, validate.DefaultThresholds()); err != nil {
		t.Fatalf("WriteDefaults() error = %v, want nil", err)
	}

	var got map[string]json.RawMessage
	if err := json.Unmarshal(buf.Bytes(), &got); err != nil {
		t.Fatalf("Unmarshal() error = %v", err)
	}
	for _, key := range []string{"min_height", "max_height", "min_thickness", "max_thickness"} {
		if _, ok := got[key]; !ok {
			t.Errorf("missing threshold key %q", key)
		}
	}

	var doc struct {
		MinHeight    float64 `json:"min_height"`
		MaxHeight    float64 `json:"max_height"`
		MinThickness float64 `json:"min_thickness"`
		MaxThickness float64 `json:"max_thickness"`
	}
	if err := json.Unmarshal(buf.Bytes(), &doc); err != nil {
		t.Fatalf("Unmarshal() error = %v", err)
	}
	if doc.MinHeight != 2.0 || doc.MaxHeight != 0 || doc.MinThickness != 0.1 || doc.MaxThickness != 0 {
		t.Errorf("thresholds = %+v, want {2 0 0.1 0}", doc)
	}
}

func TestExitCode(t *testing.T) {
	if got := ExitCode(nil); got != 0 {
		t.Errorf("ExitCode(nil) = %d, want 0", got)
	}
	if got := ExitCode([]validate.Violation{{Type: "wall_height_min"}}); got != 1 {
		t.Errorf("ExitCode(1 violation) = %d, want 1", got)
	}
}

func TestReportGolden(t *testing.T) {
	b, err := Marshal(sampleReport())
	if err != nil {
		t.Fatalf("Marshal() error = %v", err)
	}
	path := filepath.Join("testdata", "report.golden")
	assertGolden(t, path, string(b))
}

func assertGolden(t *testing.T, path, got string) {
	t.Helper()
	if *update {
		if err := os.WriteFile(path, []byte(got), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	want, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if got != string(want) {
		t.Fatalf("golden mismatch for %s\n--- got ---\n%s\n--- want ---\n%s", path, got, string(want))
	}
}
