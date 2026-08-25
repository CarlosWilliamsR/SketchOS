package validate_test

import (
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/sketchos/validator-go/internal/aabb"
	"github.com/sketchos/validator-go/internal/objparse"
	"github.com/sketchos/validator-go/internal/report"
	"github.com/sketchos/validator-go/internal/validate"
)

// benchVisitor wires the parser into global + per-object AABB accumulation,
// mirroring the CLI handoff. It keeps the minimal shape needed to benchmark the
// full parse -> AABB -> validate -> report path on a wall fixture.
type benchVisitor struct {
	global *aabb.AABB
	wall   *aabb.AABB
}

func (v *benchVisitor) VisitVertex(x, y, z float64) {
	v.global.Extend(x, y, z)
	v.wall.Extend(x, y, z)
}

func (v *benchVisitor) VisitObject(name string) {}
func (v *benchVisitor) VisitFace(indices []int) {}

// wallOBJ returns an OBJ source with n vertex lines forming a 3 m tall, 0.25 m
// thick, 10 m long wall (Y-up), so the benchmark exercises the "ten thousand
// vertex lines" scale the Performance requirement targets.
func wallOBJ(n int) string {
	var b strings.Builder
	b.WriteString("o wall_bench\n")
	for i := 0; i < n; i++ {
		x := float64(i%100) * 0.1      // 0.0 .. 9.9 along X
		y := 3.0 * float64(i%2)        // bottom/top: height 3 m on Y
		z := 0.25 * float64((i/100)%2) // thickness 0.25 m on Z
		fmt.Fprintf(&b, "v %.3f %.3f %.3f\n", x, y, z)
	}
	return b.String()
}

// runParseValidate runs the full pipeline (parse -> AABB -> validate -> report)
// over src and returns the resulting exit code.
func runParseValidate(src string) (int, error) {
	v := &benchVisitor{global: aabb.New(), wall: aabb.New()}
	if err := objparse.New(v).Parse(strings.NewReader(src)); err != nil {
		return 0, err
	}
	w := validate.NewWall("wall_bench", v.wall)
	violations := validate.ValidateWall(nil, w, validate.DefaultThresholds())
	objects := []report.ObjectMeasurement{
		{Name: w.Name, Height: w.Height, Thickness: w.Thickness},
	}
	_ = report.NewReport(v.global, objects, violations)
	return report.ExitCode(violations), nil
}

// TestParseAndValidateUnder50ms asserts the end-to-end path completes in under
// 50 ms wall-clock for a 10k-vertex model (spec Performance requirement).
func TestParseAndValidateUnder50ms(t *testing.T) {
	src := wallOBJ(10000)
	start := time.Now()
	code, err := runParseValidate(src)
	if err != nil {
		t.Fatalf("runParseValidate() error = %v, want nil", err)
	}
	if code != 0 {
		t.Errorf("exit code = %d, want 0 (3 m tall / 0.25 m thick wall within defaults)", code)
	}
	if elapsed := time.Since(start); elapsed >= 50*time.Millisecond {
		t.Errorf("parse+validate took %v, want < 50ms", elapsed)
	}
}

// BenchmarkParseAndValidate measures the full parse -> AABB -> validate ->
// report path for a 10k-vertex wall. Run with -benchtime to vary iterations.
func BenchmarkParseAndValidate(b *testing.B) {
	src := wallOBJ(10000)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := runParseValidate(src); err != nil {
			b.Fatal(err)
		}
	}
}
