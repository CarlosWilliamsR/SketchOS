# Archive Report: uiux-cad-bim-dark-mode

**Change**: CAD/BIM Dark Mode Studio UI Redesign
**Archived**: 2026-08-30
**Mode**: Hybrid (OpenSpec + Engram)
**Status**: Complete ✅

---

## Final State Summary

### Delivery Facts
- **Tasks**: 35/35 complete (10 Phase-1 + 12 Phase-2 + 13 Phase-3, all checked in persisted artifact)
- **Tests**: 171/171 passing across 10 files (zero failures, zero skipped)
- **Requirements**: 18/18 fully satisfied
- **Scenarios**: 31/31 compliant
- **Build**: ✅ `npm run build` → astro static output, 606 modules transformed, 1 page built
- **CRITICAL Issues**: 0
- **WARNING Issues**: 4 assertion-quality (CSS-class smoke assertions, non-blocking)
- **Blockers**: 0

### Verification Verdict
**PASS** — strict verify envelope `gentle-ai.verify-result/v1` reports `verdict: pass`, evidence revision `355d627`, 18/18 requirements, 31/31 scenarios, `test_exit_code: 0`, `build_exit_code: 0`.

### Final-State Authority — resolved facts (outrank stale snapshots)

1. **Verification PASS (post-remediation)**: The earlier FAIL (3 UNTESTED scenarios) was resolved by remediation commit `355d627`, which added 3 covering tests (Layout.astro fonts, camera preset active-state, clip slider). No production code changed in remediation — test-only.
2. **3 prior critical bugs FIXED** (root cause of an even earlier verify FAIL):
   - SceneStatsContext now uses explicit `setStats` (no implicit ref-to-state propagation).
   - Clipping planes use array concatenation with independent Z/Y booleans (not scalar).
   - HUD shows "—" empty state (not numeric 0).
3. **Final commit SHA `355d627`** (test-only remediation) is HEAD. Prior commits: PR #1 `9aae9e1` (dark theme + SVG icons), PR #2 `1fee15b` (3-tab dashboard + BYOK modal), PR #3 `df1d83e` (clay viewport + clip planes + camera presets + HUD).
4. **Total tasks 35/35** complete across 3 stacked PRs (stacked-to-main). Note: verify-report (#87) carries an internal "27" task count that contradicts its own 1.1–1.10 / 2.1–2.12 / 3.1–3.13 breakdown (10+12+13 = 35). Resolved toward the persisted tasks artifact (35 checked) and orchestrator final-state facts, per Final-State Authority ranking.

### Acknowledged Non-Regression Deviations (recorded as-is, not re-litigated)

| Deviation | Nature | Status |
|-----------|--------|--------|
| PCFSoftShadowMap | Proposal/tasks exclude shadow maps; design marks "Deferred" | Out-of-scope, acknowledged |
| Per-material clipping wording vs spec `renderer.clippingPlanes` | Three.js clips per-material (`localClippingEnabled`); array-concat logic matches spec exactly, only assignment target wording differs | Acknowledged, not a regression |
| Lerp factor 0.08 vs spec 0.1 | Implementation followed design/tasks (`CAMERA_LERP_FACTOR = 0.08`) | Minor numeric discrepancy, acknowledged |

### Delivery Facts
- 3 stacked PRs merged to main (stacked-to-main strategy).
- `/api` proxy contract preserved intact (`astro.config.mjs` + `api.js` paths unchanged; only header injection added).

---

## Spec Sync

Four delta specs were synced into the main spec tree. Three are new capability domains (mechanical copy — no prior main spec); one is a modification to an existing domain (ADDED requirements appended).

| Domain | Action | Requirements | Scenarios |
|--------|--------|--------------|-----------|
| `cad-dark-theme` | Created (new capability) | 4 added | 6 |
| `byok-api-key-modal` | Created (new capability) | 6 added | 8 |
| `viewport-controls` | Created (new capability) | 5 added | 10 |
| `frontend-validator-dashboard` | Updated (3 ADDED requirements appended) | 3 added (5 → 8 total) | 7 |

**Totals**: 18 requirements, 31 scenarios — consistent with the verify envelope.

### Source of Truth Updated

- `openspec/specs/cad-dark-theme/spec.md` (created from change delta — new capability)
- `openspec/specs/byok-api-key-modal/spec.md` (created from change delta — new capability)
- `openspec/specs/viewport-controls/spec.md` (created from change delta — new capability)
- `openspec/specs/frontend-validator-dashboard/spec.md` (modified — 3 requirements appended under existing `## Requirements`; all 5 prior requirements preserved)

---

## Mechanical Copy Verification

All archive operations performed via shell (`cp`, `mv`, `git mv`, `diff -r`) with mandatory readback. Zero model Read/Write used for artifact content transfer.

### New Capability Spec Sync (3 × mechanical copy)

```bash
Source: openspec/changes/uiux-cad-bim-dark-mode/specs/{domain}/spec.md
Target: openspec/specs/{domain}/spec.md
Verification: diff -r (source vs. temp copy) → 0 differences
```

- `cad-dark-theme`: `diff -r` empty ✓
- `byok-api-key-modal`: `diff -r` empty ✓
- `viewport-controls`: `diff -r` empty ✓

### Modified Spec Merge (frontend-validator-dashboard)

Appended delta requirement block (lines 5+) verbatim to the existing main spec via shell (`tail -n +5` + append). Definitive verification: reconstructed expected file (`git show HEAD:...spec.md` + delta block) diffed against the merged file → **0 differences**.

### Archive Move (Change Folder)

```bash
Source: openspec/changes/uiux-cad-bim-dark-mode
Target: openspec/changes/archive/2026-08-30-uiux-cad-bim-dark-mode
Verification: diff -r (pre-move snapshot vs. target) → 0 differences
```

`git mv` succeeded; source directory confirmed gone; `diff -r` readback empty ✓.

### Archive Contents

- ✅ proposal.md (5,961 bytes)
- ✅ exploration.md (15,254 bytes)
- ✅ design.md (5,532 bytes)
- ✅ tasks.md (7,394 bytes, 35/35 tasks checked)
- ✅ apply-progress.md (8,066 bytes)
- ✅ verify-report.md (11,844 bytes)
- ✅ specs/ (4 delta specs: cad-dark-theme, byok-api-key-modal, viewport-controls, frontend-validator-dashboard)

### Archive Verification Checklist

- [x] Main specs updated correctly (3 created, 1 merged)
- [x] Change folder moved to archive
- [x] Archive contains all artifacts (proposal, exploration, design, tasks, apply-progress, verify-report, specs)
- [x] Archived `tasks.md` has no unchecked implementation tasks (`grep '\- \[ \]'` → none)
- [x] Active changes directory no longer has this change
- [x] Verbatim `diff -r` readback output empty (no differences)

---

## Task Completion Reconciliation

No reconciliation required. The persisted `tasks.md` artifact already reflects final state — all 35 implementation tasks (1.1–1.10, 2.1–2.12, 3.1–3.13) are checked `[x]`. The Task Completion Gate passed with zero stale checkboxes.

---

## Engram Artifact Traceability

All artifacts persisted to Engram with complete observation chain:

| Artifact | Observation ID | Title | Created |
|----------|---------------|-------|---------|
| Proposal | #82 | sdd/uiux-cad-bim-dark-mode/proposal | 2026-08-26 11:39:25 |
| Spec | #83 | sdd/uiux-cad-bim-dark-mode/spec | 2026-08-26 11:43:52 |
| Design | #84 | sdd/uiux-cad-bim-dark-mode/design | 2026-08-26 11:47:16 |
| Tasks | #85 | sdd/uiux-cad-bim-dark-mode/tasks | 2026-08-26 11:49:42 |
| Apply Progress | #86 | sdd/uiux-cad-bim-dark-mode/apply-progress | 2026-08-26 11:54:13 |
| Verify Report | #87 | sdd/uiux-cad-bim-dark-mode/verify-report | 2026-08-26 12:22:27 |

**Full artifact chain**: proposal → spec → design → tasks → apply-progress → verify-report → archive-report

### Review Gate

`reviewGate` was structurally ABSENT from this candidate's status — no `reviews/` directory in the change folder and no review transaction/ledger/receipt/gate-context topics in Engram. Per the Native Review Receipt Gate, archive proceeded under ordinary repository policy (kill switch off / no review ever started for this candidate). No review artifacts exist to read.

---

## Key Learnings

### Technical Discoveries

1. Three.js clips per-material, not per-renderer: setting `localClippingEnabled=true` plus per-material `clippingPlanes` is the correct target when a renderer also carries default materials; the spec's `renderer.clippingPlanes` wording is a conceptual shorthand, and the array-concat logic is what actually matters for Z+Y combinability.

2. jsdom clamps `input type="range"` values to the element's `max` attribute: clip-slider tests must stay within the plane's `max=±maxDim` bound (maxDim=1 for empty test groups) or `fireEvent.change` silently clamps the value and the assertion sees the wrong constant.

3. React `<input type="range">` onChange fires correctly via `fireEvent.change` in @testing-library/react — no need for the more heavyweight `user-event` keyboard path for slider assertions.

### SDD Process Insights

1. Final-state facts in the archive launch prompt outranked the verify-report snapshot's internal "27 tasks" figure; the persisted tasks artifact (35 checked) and the prompt's 35/35 claim were the authoritative reconciliation basis.

2. Test-only remediation (commit `355d627`) is a valid way to close UNTESTED scenarios against already-shipped production code: no RED is possible because no production behavior changes, and each test asserts real existing behavior — coverage-closure, not TDD cycle.

3. The `/api` proxy contract (astro.config.mjs + api.js paths) surviving 3 stacked PRs is a strong regression signal that header injection can be added without touching routing.

---

## SDD Cycle Complete

**Change lifecycle**: Proposed → Specified → Designed → Tasked → Implemented (3 stacked PRs + 1 test-only remediation) → Verified (PASS) → **Archived** ✅

**Verification verdict**: PASS (zero blockers, zero critical findings, 18/18 requirements, 31/31 scenarios, 171/171 tests).

**Archive operations**:
- ✅ 3 new capability specs created under `openspec/specs/`
- ✅ 1 existing spec merged (`frontend-validator-dashboard`, +3 requirements)
- ✅ Change folder moved to `openspec/changes/archive/2026-08-30-uiux-cad-bim-dark-mode/`
- ✅ All mechanical copies verified byte-identical via `diff -r` (zero differences)
- ✅ Engram archive report persisted with complete observation chain

**Next**: Ready for the next SDD change. The CAD/BIM dark studio UI is now part of the canonical spec repository and production codebase.
