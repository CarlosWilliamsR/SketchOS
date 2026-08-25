package objparse

import (
	"errors"
	"strings"
	"testing"
)

// recordingVisitor captures what the parser emits for assertions.
type recordingVisitor struct {
	vertices []vertex
	objects  []string
	faces    [][]int
}

type vertex struct{ x, y, z float64 }

func (r *recordingVisitor) VisitVertex(x, y, z float64) {
	r.vertices = append(r.vertices, vertex{x, y, z})
}

func (r *recordingVisitor) VisitObject(name string) {
	r.objects = append(r.objects, name)
}

func (r *recordingVisitor) VisitFace(indices []int) {
	cp := make([]int, len(indices))
	copy(cp, indices)
	r.faces = append(r.faces, cp)
}

func TestParseHappyPath(t *testing.T) {
	input := `
# A Blender-exported wall with two quads
mtllib wall.mtl
o wall_1
v 0 0 0
v 1 0 0
v 1 0 1
v 0 0 1
v 0 3 0
v 1 3 0
v 1 3 1
v 0 3 1
vt 0.0 0.0
vn 0.0 1.0 0.0
usemtl default
s off
g group_a
f 1 2 3 4
f 5/1/1 6/2/1 7/3/1 8/4/1
f 2//1 6//1 7//1 3//1
`
	rv := &recordingVisitor{}
	p := New(rv)
	if err := p.Parse(strings.NewReader(input)); err != nil {
		t.Fatalf("Parse() error = %v, want nil", err)
	}

	if len(rv.vertices) != 8 {
		t.Fatalf("got %d vertices, want 8", len(rv.vertices))
	}
	// Spot-check the first vertex and the top of the wall.
	if got := rv.vertices[0]; got != (vertex{0, 0, 0}) {
		t.Errorf("vertices[0] = %+v, want {0 0 0}", got)
	}
	if got := rv.vertices[4]; got != (vertex{0, 3, 0}) {
		t.Errorf("vertices[4] = %+v, want {0 3 0}", got)
	}

	if len(rv.objects) != 2 {
		t.Fatalf("got %d objects, want 2", len(rv.objects))
	}
	if rv.objects[0] != "wall_1" {
		t.Errorf("objects[0] = %q, want %q", rv.objects[0], "wall_1")
	}
	if rv.objects[1] != "group_a" {
		t.Errorf("objects[1] = %q, want %q", rv.objects[1], "group_a")
	}

	if len(rv.faces) != 3 {
		t.Fatalf("got %d faces, want 3", len(rv.faces))
	}
	// Positive indices resolve 1-based -> 0-based.
	wantFirst := []int{0, 1, 2, 3}
	if len(rv.faces[0]) != len(wantFirst) {
		t.Fatalf("face[0] len = %d, want %d", len(rv.faces[0]), len(wantFirst))
	}
	for i := range wantFirst {
		if rv.faces[0][i] != wantFirst[i] {
			t.Errorf("face[0][%d] = %d, want %d", i, rv.faces[0][i], wantFirst[i])
		}
	}
}

func TestParseNegativeRelativeIndices(t *testing.T) {
	input := `v 1 0 0
v 2 0 0
v 3 0 0
v 4 0 0
f -4 -3 -2 -1
`
	rv := &recordingVisitor{}
	if err := New(rv).Parse(strings.NewReader(input)); err != nil {
		t.Fatalf("Parse() error = %v, want nil", err)
	}
	if len(rv.vertices) != 4 {
		t.Fatalf("got %d vertices, want 4", len(rv.vertices))
	}
	if len(rv.faces) != 1 {
		t.Fatalf("got %d faces, want 1", len(rv.faces))
	}
	// -4 resolves to vertex 0, -1 to vertex 3.
	want := []int{0, 1, 2, 3}
	for i := range want {
		if rv.faces[0][i] != want[i] {
			t.Errorf("face[0][%d] = %d, want %d", i, rv.faces[0][i], want[i])
		}
	}
}

func TestParseMalformedNonVertexSkipped(t *testing.T) {
	input := `v 0 0 0
this is not a valid obj line
f 1 notanumber
f 1 2
usemtl
mtllib
vt
vn
`
	rv := &recordingVisitor{}
	if err := New(rv).Parse(strings.NewReader(input)); err != nil {
		t.Fatalf("Parse() error = %v, want nil", err)
	}
	if len(rv.vertices) != 1 {
		t.Fatalf("got %d vertices, want 1", len(rv.vertices))
	}
	if len(rv.faces) != 0 {
		t.Fatalf("got %d faces, want 0 (malformed faces skipped)", len(rv.faces))
	}
}

func TestParseMalformedVertexError(t *testing.T) {
	cases := []struct {
		name  string
		input string
	}{
		{"too few fields", "v 0 0\n"},
		{"non numeric", "v 0 x 0\n"},
		{"empty v", "v\n"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rv := &recordingVisitor{}
			err := New(rv).Parse(strings.NewReader(tc.input))
			if err == nil {
				t.Fatalf("Parse() error = nil, want ParseError")
			}
			var pe *ParseError
			if !errors.As(err, &pe) {
				t.Fatalf("error type = %T, want *ParseError", err)
			}
			if pe.Line != 1 {
				t.Errorf("ParseError.Line = %d, want 1", pe.Line)
			}
		})
	}
}

func TestParseFaceIndexOutOfRangeError(t *testing.T) {
	// A positive index beyond the declared vertex count is a parse error.
	input := "v 0 0 0\nf 1 2 3\n"
	rv := &recordingVisitor{}
	err := New(rv).Parse(strings.NewReader(input))
	if err == nil {
		t.Fatal("Parse() error = nil, want ParseError for out-of-range index")
	}
	var pe *ParseError
	if !errors.As(err, &pe) {
		t.Fatalf("error type = %T, want *ParseError", err)
	}
	if pe.Line != 2 {
		t.Errorf("ParseError.Line = %d, want 2", pe.Line)
	}
}

func TestResolve(t *testing.T) {
	cases := []struct {
		name    string
		idx     int
		seen    int
		want    int
		wantErr bool
	}{
		{"positive 1-based", 1, 4, 0, false},
		{"positive mid", 3, 4, 2, false},
		{"negative relative", -1, 4, 3, false},
		{"negative relative far", -4, 4, 0, false},
		{"zero invalid", 0, 4, 0, true},
		{"positive beyond seen", 5, 4, 0, true},
		{"negative before vertex 0", -5, 4, 0, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := resolve(tc.idx, tc.seen)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("resolve(%d, %d) err = nil, want error", tc.idx, tc.seen)
				}
				return
			}
			if err != nil {
				t.Fatalf("resolve(%d, %d) error = %v, want nil", tc.idx, tc.seen, err)
			}
			if got != tc.want {
				t.Errorf("resolve(%d, %d) = %d, want %d", tc.idx, tc.seen, got, tc.want)
			}
		})
	}
}
