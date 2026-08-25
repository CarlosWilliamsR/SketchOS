package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/sketchos/validator-go/internal/report"
)

// writeFixture writes OBJ source to a temp file and returns its path.
func writeFixture(t *testing.T, content string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "fixture.obj")
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	return path
}

// runValidator runs the CLI wiring against args, capturing stdout/stderr.
func runValidator(t *testing.T, args ...string) (code int, stdout, stderr string) {
	t.Helper()
	var out, errBuf bytes.Buffer
	return run(args, &out, &errBuf), out.String(), errBuf.String()
}

func decodeReport(t *testing.T, out string) report.Report {
	t.Helper()
	var doc report.Report
	if err := json.Unmarshal([]byte(out), &doc); err != nil {
		t.Fatalf("json.Unmarshal: %v\nreport:\n%s", err, out)
	}
	return doc
}

// TestRunPassingWall feeds a wall within defaults through the full CLI path and
// asserts exit 0 with a valid JSON report and no violations. Two opposite
// corners fully determine the AABB for the pipeline under test.
func TestRunPassingWall(t *testing.T) {
	code, out, errOut := runValidator(t, "-input", writeFixture(t,
		"o wall_1\nv 0 0 0\nv 4 3 0.25\n"))
	if code != 0 {
		t.Fatalf("exit code = %d, want 0 (stderr: %s)", code, errOut)
	}

	doc := decodeReport(t, out)
	if doc.AABB.Dimensions.DY != 3 {
		t.Errorf("aabb.dy = %v, want 3", doc.AABB.Dimensions.DY)
	}
	if len(doc.Objects) != 1 {
		t.Fatalf("len(objects) = %d, want 1", len(doc.Objects))
	}
	if o := doc.Objects[0]; o.Name != "wall_1" || o.Height != 3 || o.Thickness != 0.25 {
		t.Errorf("objects[0] = %+v, want {wall_1 3 0.25}", o)
	}
	if len(doc.Violations) != 0 {
		t.Errorf("len(violations) = %d, want 0", len(doc.Violations))
	}
}

// TestRunViolatingWall feeds a wall below minimum height and asserts exit 1
// with a wall_height_min violation carrying the measured height.
func TestRunViolatingWall(t *testing.T) {
	code, out, _ := runValidator(t, "-input", writeFixture(t,
		"o wall_short\nv 0 0 0\nv 4 1.5 0.25\n"))
	if code != 1 {
		t.Fatalf("exit code = %d, want 1", code)
	}

	doc := decodeReport(t, out)
	if len(doc.Violations) != 1 {
		t.Fatalf("len(violations) = %d, want 1", len(doc.Violations))
	}
	v := doc.Violations[0]
	if v.Type != "wall_height_min" || v.Object != "wall_short" || v.Measured != 1.5 {
		t.Errorf("violations[0] = %+v, want type=wall_height_min object=wall_short measured=1.5", v)
	}
}

// TestRunAngledWall feeds a wall rotated 45 degrees about Y. Height must still
// read from Y (3 m), while the AABB horizontal extents inflate beyond the
// unrotated 0.25 m thickness. Result: no violations, exit 0.
func TestRunAngledWall(t *testing.T) {
	cos, sin := math.Sqrt2/2, math.Sqrt2/2
	var b strings.Builder
	b.WriteString("o wall_angled\n")
	for _, c := range [][3]float64{
		{0, 0, 0}, {1, 0, 0}, {1, 0, 0.25}, {0, 0, 0.25},
		{0, 3, 0}, {1, 3, 0}, {1, 3, 0.25}, {0, 3, 0.25},
	} {
		fmt.Fprintf(&b, "v %.6f %.6f %.6f\n", c[0]*cos+c[2]*sin, c[1], -c[0]*sin+c[2]*cos)
	}

	code, out, _ := runValidator(t, "-input", writeFixture(t, b.String()))
	if code != 0 {
		t.Fatalf("exit code = %d, want 0", code)
	}

	doc := decodeReport(t, out)
	if dy := doc.AABB.Dimensions.DY; dy != 3 {
		t.Errorf("aabb.dy = %v, want 3 (height from Y, not inflated by rotation)", dy)
	}
	if len(doc.Objects) != 1 {
		t.Fatalf("len(objects) = %d, want 1", len(doc.Objects))
	}
	if th := doc.Objects[0].Thickness; th <= 0.25 {
		t.Errorf("objects[0].Thickness = %v, want > 0.25 (rotated AABB inflation)", th)
	}
	if len(doc.Violations) != 0 {
		t.Errorf("len(violations) = %d, want 0", len(doc.Violations))
	}
}

// TestRunParseError feeds a malformed vertex line and asserts exit 2 with a
// diagnostic on stderr and no report on stdout.
func TestRunParseError(t *testing.T) {
	code, out, errOut := runValidator(t, "-input", writeFixture(t, "v 0 0\n"))
	if code != 2 {
		t.Fatalf("exit code = %d, want 2", code)
	}
	if out != "" {
		t.Errorf("stdout = %q, want empty on parse error", out)
	}
	if errOut == "" {
		t.Error("stderr empty, want a diagnostic on parse error")
	}
}

// TestRunPrintDefaults invokes the CLI with only -print-defaults (no -input)
// and asserts exit 0 with the four threshold keys serialized as JSON. This is
// the geometry-validator "Default thresholds flag" acceptance scenario.
func TestRunPrintDefaults(t *testing.T) {
	code, out, errOut := runValidator(t, "-print-defaults")
	if code != 0 {
		t.Fatalf("exit code = %d, want 0 (stderr: %s)", code, errOut)
	}

	var got map[string]float64
	if err := json.Unmarshal([]byte(out), &got); err != nil {
		t.Fatalf("json.Unmarshal: %v\nstdout:\n%s", err, out)
	}
	for _, key := range []string{"min_height", "max_height", "min_thickness", "max_thickness"} {
		if _, ok := got[key]; !ok {
			t.Errorf("missing threshold key %q in %s", key, out)
		}
	}
	if got["min_height"] != 2.0 {
		t.Errorf("min_height = %v, want 2.0", got["min_height"])
	}
	if got["max_height"] != 0 {
		t.Errorf("max_height = %v, want 0 (unenforced)", got["max_height"])
	}
	if got["min_thickness"] != 0.1 {
		t.Errorf("min_thickness = %v, want 0.1", got["min_thickness"])
	}
	if got["max_thickness"] != 0 {
		t.Errorf("max_thickness = %v, want 0 (unenforced)", got["max_thickness"])
	}
}

// TestRunOutputFile writes the report to -output, leaving stdout empty.
func TestRunOutputFile(t *testing.T) {
	outPath := filepath.Join(t.TempDir(), "report.json")
	code, out, errOut := runValidator(t,
		"-input", writeFixture(t, "o wall_1\nv 0 0 0\nv 1 3 0.25\n"),
		"-output", outPath)
	if code != 0 {
		t.Fatalf("exit code = %d, want 0 (stderr: %s)", code, errOut)
	}
	if out != "" {
		t.Errorf("stdout = %q, want empty when -output is set", out)
	}

	b, err := os.ReadFile(outPath)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if !bytes.Contains(b, []byte(`"aabb"`)) {
		t.Errorf("output file missing aabb key: %s", b)
	}
}
