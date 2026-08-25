// Validator dashboard island (client:only="react").
//
// State machine: idle → loading → loaded(pass|violations) → empty → error.
// - On mount: fetch thresholds from `/api/extract-rules`.
// - Upload `.obj`: read text locally (for the 3D view) and POST the file to
//   `/api/validate-geometry`; the returned report drives overlays + panel.
// - Autocorrect: POST a full ArchitecturalDSL payload to `/api/autocorrect`
//   and re-render the returned (corrected) report + applied fixes.

import { useEffect, useState } from 'react';
import GeometryScene from './GeometryScene.jsx';
import { fetchRules, validateGeometry, autocorrect } from '../lib/api.js';

const PHASES = { idle: 'idle', loading: 'loading', loaded: 'loaded', empty: 'empty', error: 'error' };

function formatNumber(value) {
  return Number.isFinite(value) ? String(Number.parseFloat(value.toFixed(3))) : '—';
}

export default function ValidatorDashboard() {
  const [phase, setPhase] = useState(PHASES.idle);
  const [rules, setRules] = useState(null);
  const [rulesError, setRulesError] = useState(null);
  const [result, setResult] = useState(null); // { status, report, fixes }
  const [objText, setObjText] = useState(null);
  const [fileName, setFileName] = useState(null);
  const [error, setError] = useState(null);
  const [dsl, setDsl] = useState('');

  useEffect(() => {
    let cancelled = false;
    fetchRules()
      .then((thresholds) => {
        if (!cancelled) setRules(thresholds);
      })
      .catch((err) => {
        if (!cancelled) setRulesError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const violations = result?.report?.violations ?? [];
  const fixes = result?.fixes ?? [];
  const hasViolations = violations.length > 0;

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setError(null);
    setPhase(PHASES.loading);
    try {
      const text = await file.text();
      const response = await validateGeometry(file);
      setObjText(text);
      setResult(response);
      setPhase(response?.report?.objects?.length ? PHASES.loaded : PHASES.empty);
    } catch (err) {
      setError(err.message);
      setPhase(PHASES.error);
    }
  }

  async function handleAutocorrect() {
    let payload;
    try {
      payload = JSON.parse(dsl);
    } catch {
      setError('The DSL payload is not valid JSON.');
      setPhase(PHASES.error);
      return;
    }
    setError(null);
    setPhase(PHASES.loading);
    try {
      const response = await autocorrect(payload);
      setResult(response);
      setPhase(response?.report?.objects?.length ? PHASES.loaded : PHASES.empty);
    } catch (err) {
      setError(err.message);
      setPhase(PHASES.error);
    }
  }

  function renderViewport() {
    if (phase === PHASES.loaded && objText) {
      return <GeometryScene objText={objText} report={result.report} />;
    }
    const messages = {
      idle: 'Upload a .obj file to inspect the geometry.',
      loading: 'Validating geometry…',
      empty: 'The report contains no geometry to display.',
      error: error || 'Something went wrong.',
    };
    const message =
      phase === PHASES.loaded ? 'Corrected report received — no geometry to display.' : messages[phase];
    return (
      <div className="viewport-message" role="status" aria-live="polite">
        {phase === PHASES.loading && <div className="spinner" aria-hidden="true" />}
        <p>{message}</p>
      </div>
    );
  }

  return (
    <div className="validator-dashboard">
      <aside className="side-panel">
        <h1>Validator Dashboard</h1>

        <section className="panel-section">
          <label className="upload-control">
            Upload .obj
            <input type="file" accept=".obj" onChange={handleFileChange} />
          </label>
        </section>

        {rulesError && <p className="inline-error">Thresholds unavailable: {rulesError}</p>}
        {rules && (
          <section className="panel-section">
            <h2>Thresholds</h2>
            <dl className="rules">
              <div><dt>Min height</dt><dd>{formatNumber(rules.min_height)} m</dd></div>
              <div><dt>Max height</dt><dd>{formatNumber(rules.max_height)} m</dd></div>
              <div><dt>Min thickness</dt><dd>{formatNumber(rules.min_thickness)} m</dd></div>
              <div><dt>Max thickness</dt><dd>{formatNumber(rules.max_thickness)} m</dd></div>
            </dl>
          </section>
        )}

        {phase === PHASES.loaded && (
          <section className="panel-section">
            <div className={`status-banner ${hasViolations ? 'violations' : 'pass'}`}>
              {hasViolations
                ? `${violations.length} violation${violations.length === 1 ? '' : 's'} found`
                : 'Validation passed'}
            </div>

            {hasViolations && (
              <>
                <h2>Violations</h2>
                <ul className="violation-list">
                  {violations.map((v, index) => (
                    <li key={`${v.object}-${v.type}-${index}`} className="violation">
                      <strong>{v.object}</strong>
                      <span className="violation-rule">{v.type}</span>
                      <span className="violation-measure">
                        measured {formatNumber(v.measured)} m vs threshold {formatNumber(v.threshold)} m
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}

            {fixes.length > 0 && (
              <>
                <h2>Applied fixes</h2>
                <ul className="fix-list">
                  {fixes.map((fix, index) => (
                    <li key={index}>
                      {fix.wall_id}: {fix.dimension} {formatNumber(fix.from)} → {formatNumber(fix.to)}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        )}

        <section className="panel-section">
          <h2>Autocorrect</h2>
          <p className="hint">Paste a full ArchitecturalDSL JSON payload, then re-validate.</p>
          <textarea
            className="dsl-editor"
            rows={6}
            value={dsl}
            onChange={(event) => setDsl(event.target.value)}
            placeholder='{"walls": [...], "floors": [...], ...}'
          />
          <button
            className="button"
            type="button"
            onClick={handleAutocorrect}
            disabled={phase === PHASES.loading}
          >
            Autocorrect &amp; re-validate
          </button>
        </section>
      </aside>

      <main className="viewport" aria-label="3D viewport">
        {renderViewport()}
      </main>
    </div>
  );
}
