package objparse_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/sketchos/validator-go/internal/aabb"
	"github.com/sketchos/validator-go/internal/objparse"
)

// accum wires the parser's Visitor into an AABB accumulator, mirroring the
// exact handoff that main.go performs in the CLI slice. It is declared here so
// slice 1 can prove the runtime boundary (file -> parser -> AABB) without
// shipping main.go ahead of its slice.
type accum struct {
	aabb *aabb.AABB
}

func (a *accum) VisitVertex(x, y, z float64) { a.aabb.Extend(x, y, z) }
func (a *accum) VisitObject(name string)     {}
func (a *accum) VisitFace(indices []int)     {}

// TestParseFileAccumulatesAABB feeds a real .obj file (os.File, not a string
// reader) through the visitor and asserts the accumulated AABB. This is the
// runtime harness for work unit 1: parser -> aabb accumulation.
func TestParseFileAccumulatesAABB(t *testing.T) {
	fixture := `# Blender 4.x export, Y-up
o wall_1
v 0 0 0
v 4 0 0
v 4 0 0.25
v 0 0 0.25
v 0 3 0
v 4 3 0
v 4 3 0.25
v 0 3 0.25
o wall_2
v 10 0 0
v 10.25 0 0
v 10.25 0 5
v 10 0 5
v 10 2.5 0
v 10.25 2.5 0
v 10.25 2.5 5
v 10 2.5 5
f -8 -7 -6 -5
f -4 -3 -2 -1
`

	path := filepath.Join(t.TempDir(), "walls.obj")
	if err := os.WriteFile(path, []byte(fixture), 0o644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	f, err := os.Open(path)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer f.Close()

	acc := &accum{aabb: aabb.New()}
	if err := objparse.New(acc).Parse(f); err != nil {
		t.Fatalf("Parse() error = %v, want nil", err)
	}

	// wall_1: x in [0,4], y in [0,3], z in [0,0.25]
	// wall_2: x in [10,10.25], y in [0,2.5], z in [0,5]
	// Combined box spans both walls.
	assertCoord := func(name string, got, want float64) {
		t.Helper()
		if got != want {
			t.Errorf("%s = %v, want %v", name, got, want)
		}
	}
	assertCoord("MinX", acc.aabb.MinX, 0)
	assertCoord("MinY", acc.aabb.MinY, 0)
	assertCoord("MinZ", acc.aabb.MinZ, 0)
	assertCoord("MaxX", acc.aabb.MaxX, 10.25)
	assertCoord("MaxY", acc.aabb.MaxY, 3) // wall height on Y
	assertCoord("MaxZ", acc.aabb.MaxZ, 5)

	dx, dy, dz := acc.aabb.Dimensions()
	assertCoord("dx", dx, 10.25)
	assertCoord("dy", dy, 3)
	assertCoord("dz", dz, 5)
}
