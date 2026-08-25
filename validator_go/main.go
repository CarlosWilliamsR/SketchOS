// Command validator-go parses a Blender-exported .obj file, computes the
// Axis-Aligned Bounding Box, and validates geometric regulations for walls.
//
// It is a single-pass streaming validator: the OBJ parser feeds a visitor that
// accumulates one global AABB and one AABB per named object, wall rules run
// against each wall-classified object, and a deterministic JSON report is
// written to stdout or the -output file.
//
// Exit codes: 0 = pass (no violations), 1 = violations found, 2 = parse or
// input error. Diagnostics go to stderr; JSON goes to stdout/-output.
package main

import (
	"flag"
	"fmt"
	"io"
	"os"

	"github.com/sketchos/validator-go/internal/aabb"
	"github.com/sketchos/validator-go/internal/objparse"
	"github.com/sketchos/validator-go/internal/report"
	"github.com/sketchos/validator-go/internal/validate"
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

// run wires flag parsing, OBJ parsing, AABB accumulation, wall validation, and
// report writing. It returns the process exit code (0 pass / 1 violations /
// 2 parse or input error). Diagnostics are written to stderr; the JSON report
// is written to stdout (default) or the -output file.
func run(args []string, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("validator-go", flag.ContinueOnError)
	fs.SetOutput(stderr)

	input := fs.String("input", "", "path to the .obj file to validate (required)")
	output := fs.String("output", "", "write the JSON report to this file (default: stdout)")
	printDefaults := fs.Bool("print-defaults", false, "print the default thresholds as JSON and exit")
	minHeight := fs.Float64("min-height", 2.0, "minimum wall height in meters (0 = unenforced)")
	maxHeight := fs.Float64("max-height", 0, "maximum wall height in meters (0 = unenforced)")
	minThickness := fs.Float64("min-thickness", 0.1, "minimum wall thickness in meters (0 = unenforced)")
	maxThickness := fs.Float64("max-thickness", 0, "maximum wall thickness in meters (0 = unenforced)")

	if err := fs.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return 0
		}
		return 2
	}
	if *printDefaults {
		if err := report.WriteDefaults(stdout, validate.DefaultThresholds()); err != nil {
			fmt.Fprintf(stderr, "validator-go: write defaults: %v\n", err)
			return 2
		}
		return 0
	}
	if *input == "" {
		fmt.Fprintln(stderr, "validator-go: -input is required")
		return 2
	}

	f, err := os.Open(*input)
	if err != nil {
		fmt.Fprintf(stderr, "validator-go: open %q: %v\n", *input, err)
		return 2
	}
	defer f.Close()

	m := newModel()
	if err := objparse.New(m).Parse(f); err != nil {
		fmt.Fprintf(stderr, "validator-go: %v\n", err)
		return 2
	}

	thresholds := validate.Thresholds{
		MinHeight:    *minHeight,
		MaxHeight:    *maxHeight,
		MinThickness: *minThickness,
		MaxThickness: *maxThickness,
	}
	objects, violations := m.result(thresholds)
	r := report.NewReport(m.global, objects, violations)

	var w io.Writer = stdout
	if *output != "" {
		out, err := os.Create(*output)
		if err != nil {
			fmt.Fprintf(stderr, "validator-go: create %q: %v\n", *output, err)
			return 2
		}
		defer out.Close()
		w = out
	}
	if err := report.Write(w, r); err != nil {
		fmt.Fprintf(stderr, "validator-go: write report: %v\n", err)
		return 2
	}
	return report.ExitCode(violations)
}

// model is the objparse.Visitor wiring the parser into AABB accumulation. It
// keeps one global AABB (all vertices) and one AABB per named object, keyed by
// the current `o`/`g` name. Anonymous vertices (before any object statement)
// contribute to the global AABB only.
type model struct {
	global *aabb.AABB
	boxes  map[string]*aabb.AABB
	order  []string // first-vertex-seen order of object names (deterministic)
	cur    string   // current object/group name
}

func newModel() *model {
	return &model{
		global: aabb.New(),
		boxes:  make(map[string]*aabb.AABB),
	}
}

func (m *model) VisitVertex(x, y, z float64) {
	m.global.Extend(x, y, z)
	if m.cur == "" {
		return
	}
	b, ok := m.boxes[m.cur]
	if !ok {
		b = aabb.New()
		m.boxes[m.cur] = b
		m.order = append(m.order, m.cur)
	}
	b.Extend(x, y, z)
}

func (m *model) VisitObject(name string) { m.cur = name }
func (m *model) VisitFace(indices []int) {}

// result derives per-object measurements and wall violations in deterministic
// first-seen order. Wall rules are applied only to wall-classified objects.
func (m *model) result(t validate.Thresholds) ([]report.ObjectMeasurement, []validate.Violation) {
	objects := make([]report.ObjectMeasurement, 0, len(m.order))
	var violations []validate.Violation
	for _, name := range m.order {
		w := validate.NewWall(name, m.boxes[name])
		objects = append(objects, report.ObjectMeasurement{
			Name:      w.Name,
			Height:    w.Height,
			Thickness: w.Thickness,
		})
		if validate.Classify(name) == validate.KindWall {
			violations = validate.ValidateWall(violations, w, t)
		}
	}
	return objects, violations
}
