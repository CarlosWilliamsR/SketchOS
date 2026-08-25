# Archive Report: csg-boolean-wall-openings-obj-export

- **Status**: success (intentional-with-warnings — one deferred manual E2E task)
- **Archived to**: `openspec/changes/archive/2026-08-24-csg-boolean-wall-openings-obj-export/`
- **Artifact store**: hybrid (`both`) — OpenSpec filesystem + Engram
- **Archive date**: 2026-08-24

## Executive Summary

Archived the CSG boolean wall openings + OBJ export change. All three capability deltas were synced into the base specs (`arch-macros` created, `blender-mcp-client` and `backend-service` modified+extended). Verification passed with warnings: 0 critical findings, 52 tests passing, 16/16 scenarios compliant. The single open item — task 4.2 manual Blender E2E — is deferred (no Blender in CI) and is not archive-blocking per orchestrator final-state facts.

## Final State

| Metric | Value |
|--------|-------|
| Tasks | 10/11 complete; task 4.2 deferred |
| Test suite | `uv run pytest tests -q` → 52 passed (exit 0) |
| Build | byte-compile clean (`uv run python -m compileall -q src`, exit 0) |
| Verify verdict | PASS WITH WARNINGS — 0 CRITICAL, 1 WARNING (deferred E2E), 1 SUGGESTION (R4 "meshes joined" wording vs deferred join) |
| Requirements | 9/9 (arch-macros 4, blender-mcp-client 3, backend-service 2) |
| Scenarios | 16/16 compliant |
| Review gate | absent — no review ever discovered for this candidate; archive proceeds under ordinary policy |

## Task Completion Reconciliation

Task `4.2 — Manual/deferred E2E (real boolean DIFFERENCE cutout + OBJ in Blender)` remains unchecked (`- [ ]`) in `tasks.md` and in the Engram tasks observation #14. This is a deferred manual verification task, not an implementation task: there is no Blender runtime in CI, so it can never be completed in this environment. The orchestrator's final-state facts explicitly mark it DEFERRED and not archive-blocking, and `verify-report.md` / `apply-progress.md` both record it as a documented gap (not a blocker). Per the Task Completion Gate exceptional-repair path, this archive proceeds on the orchestrator's explicit instruction, and this reconciliation reason is recorded here for the audit trail.

## Spec Sync

| Domain | Action | Requirements |
|--------|--------|--------------|
| `arch-macros` | Created (new full spec) | 4 requirements, 6 scenarios |
| `blender-mcp-client` | Updated (MODIFIED `Code generation` + ADDED `Opening cutout geometry`, `Deterministic modifier lifecycle`) | preserved `Validation before execution`, `Blender MCP invocation`, `Transport isolation` |
| `backend-service` | Updated (MODIFIED `Tool registration` + ADDED `Optional OBJ export`) | preserved `Server bootstrapping` |
| `arch-dsl` | Unchanged | — |

## Files Changed

| File | Action |
|------|--------|
| `backend/src/sketchos_backend/arch_macros.py` | New |
| `backend/tests/test_arch_macros.py` | New |
| `backend/src/sketchos_backend/blender_client.py` | Modified |
| `backend/src/sketchos_backend/server.py` | Modified |
| `backend/tests/test_blender_client.py` | Modified |
| `backend/tests/test_server.py` | Modified |

## Archive Contents

- proposal.md ✅
- exploration.md ✅
- design.md ✅
- tasks.md ✅ (10/11 complete; 4.2 deferred)
- specs/ (arch-macros, blender-mcp-client, backend-service) ✅
- apply-progress.md ✅
- verify-report.md ✅
- archive-report.md ✅ (this file)

## Engram Observation IDs Read (traceability)

| Artifact | Observation ID |
|----------|----------------|
| proposal | #11 |
| spec | #12 |
| design | #13 |
| tasks | #14 |
| verify-report | #16 |
| apply-progress | #15 |
| explore | #10 |

Note: Engram `spec` observation #12 is a stale snapshot — it predates the backend-service delta (written in apply slice 3) and omits it. The OpenSpec delta file `specs/backend-service/spec.md` (matched by `verify-report.md` 9/9 requirements) is the authoritative spec source for the merge.

## Risks

- Deferred manual E2E (task 4.2): real boolean DIFFERENCE cutout correctness and OBJ file output are proven only by deterministic string assertions plus a fake-`bpy` script harness, not a live Blender run. Accepted as a documented WARNING.
- Suggestion (non-blocking): `arch-macros` R4 prose says "meshes joined" but the design resolves this vacuously (join deferred). Consider tightening the wording in a future change.

## Verdict

SDD cycle complete. The change is planned, implemented, verified (PASS WITH WARNINGS), and archived. Ready for the next change.
