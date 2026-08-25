// Package objparse implements a single-pass, streaming Wavefront OBJ parser.
//
// It is intentionally dependency-free: tokenization uses strings.Fields and
// strconv.ParseFloat (no regexp), and vertex storage is avoided so memory stays
// O(1) regardless of file size. Faces are index-resolved and emitted to a
// Visitor but never retained — the AABB accumulator (and later validate stage)
// only need vertex coordinates and object names.
package objparse

import (
	"bufio"
	"fmt"
	"io"
	"strconv"
	"strings"
)

// Visitor receives parsed geometry as a stream. Implementations must not retain
// references to the indices slice passed to VisitFace.
type Visitor interface {
	// VisitVertex receives one vertex coordinate. Coordinates are in the
	// OBJ file's native axis convention (Blender export: Y is up).
	VisitVertex(x, y, z float64)
	// VisitObject is called for each `o` (object) or `g` (group) statement.
	// The name is the remainder of the line, trimmed, or "" for an anonymous
	// object/group.
	VisitObject(name string)
	// VisitFace receives the zero-based vertex indices of one face. AABB
	// accumulation ignores this; it exists so later stages (validation) can
	// consume topology without this package depending on them.
	VisitFace(indices []int)
}

// ParseError describes a line that could not be parsed.
type ParseError struct {
	Line int
	Msg  string
}

func (e *ParseError) Error() string {
	return fmt.Sprintf("objparse: line %d: %s", e.Line, e.Msg)
}

// Parser streams OBJ input to a Visitor.
type Parser struct {
	v    Visitor
	seen int // number of vertex (v) records seen so far
}

// New returns a Parser that emits parsed geometry to v.
func New(v Visitor) *Parser {
	return &Parser{v: v}
}

// maxScannerBuffer raises bufio.Scanner's default 64 KiB token limit so long
// `f` polygon-fan lines do not fail. 8 MiB is far beyond any realistic face.
const maxScannerBuffer = 8 * 1024 * 1024

// Parse reads a complete OBJ stream from r and emits it to the Visitor. It
// stops at the first malformed vertex line or unresolvable face index.
func (p *Parser) Parse(r io.Reader) error {
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 64*1024), maxScannerBuffer)

	line := 0
	for sc.Scan() {
		line++
		if err := p.parseLine(line, sc.Text()); err != nil {
			return err
		}
	}
	if err := sc.Err(); err != nil {
		return fmt.Errorf("objparse: read: %w", err)
	}
	return nil
}

func (p *Parser) parseLine(line int, text string) error {
	// Strip a trailing comment (everything from a `#` on).
	if i := strings.IndexByte(text, '#'); i >= 0 {
		text = text[:i]
	}
	text = strings.TrimSpace(text)
	if text == "" {
		return nil
	}

	fields := strings.Fields(text)
	switch fields[0] {
	case "v":
		return p.parseVertex(line, fields[1:])
	case "o", "g":
		name := strings.TrimSpace(strings.Join(fields[1:], " "))
		p.v.VisitObject(name)
		return nil
	case "f":
		return p.parseFace(line, fields[1:])
	default:
		// Unknown or non-geometry statements (vt, vn, usemtl, mtllib, s,
		// etc.) are skipped.
		return nil
	}
}

func (p *Parser) parseVertex(line int, fields []string) error {
	if len(fields) < 3 {
		return &ParseError{Line: line, Msg: "vertex requires 3 numeric coordinates"}
	}
	var xyz [3]float64
	for i := 0; i < 3; i++ {
		f, err := strconv.ParseFloat(fields[i], 64)
		if err != nil {
			return &ParseError{Line: line, Msg: fmt.Sprintf("invalid vertex coordinate %q", fields[i])}
		}
		xyz[i] = f
	}
	p.v.VisitVertex(xyz[0], xyz[1], xyz[2])
	p.seen++
	return nil
}

func (p *Parser) parseFace(line int, fields []string) error {
	if len(fields) < 3 {
		return nil // not a valid polygon; skip without aborting
	}
	indices := make([]int, 0, len(fields))
	for _, f := range fields {
		// f entries are v, v/vt, v/vt/vn, or v//vn. Only the first number
		// (the vertex index) matters for index resolution.
		token := f
		if i := strings.IndexByte(token, '/'); i >= 0 {
			token = token[:i]
		}
		idx, err := strconv.Atoi(token)
		if err != nil {
			return nil // malformed face reference; skip whole face line
		}
		resolved, err := resolve(idx, p.seen)
		if err != nil {
			return &ParseError{Line: line, Msg: err.Error()}
		}
		indices = append(indices, resolved)
	}
	p.v.VisitFace(indices)
	return nil
}

// resolve maps an OBJ face vertex index to a zero-based index.
//
//	idx > 0  -> idx-1            (1-based positive)
//	idx < 0  -> seen+idx         (negative relative to last seen vertex)
//	idx == 0 -> invalid
func resolve(idx, seen int) (int, error) {
	if idx > 0 {
		if idx-1 >= seen {
			return 0, fmt.Errorf("face index %d exceeds %d declared vertices", idx, seen)
		}
		return idx - 1, nil
	}
	if idx < 0 {
		resolved := seen + idx
		if resolved < 0 {
			return 0, fmt.Errorf("face index %d resolves before first vertex", idx)
		}
		return resolved, nil
	}
	return 0, fmt.Errorf("face index 0 is not valid")
}
