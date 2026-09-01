// Validator dashboard island (client:only="react").
//
// State machine: idle → loading → loaded(pass|violations) → empty → error.
// - On mount: fetch thresholds from `/api/extract-rules`.
// - Upload `.obj`: read text locally (for the 3D view) and POST the file to
//   `/api/validate-geometry`; the returned report drives overlays + panel.
// - Autocorrect: POST a full ArchitecturalDSL payload to `/api/autocorrect`
//   and re-render the returned (corrected) report + applied fixes.
//
// The sidebar is a 3-tab ARIA tablist (Ingest, Regulations, Diagnostics).
// `activeTab` is orthogonal to the phase state machine — switching tabs never
// resets the upload/validation/autocorrect flow, and resolving `fetchRules`
// never resets the selected tab.

import { useEffect, useRef, useState } from 'react';
import GeometryScene from './GeometryScene.jsx';
import { fetchRules, validateGeometry, autocorrect, generateFromText } from '../lib/api.js';
import { BYOKModal } from './BYOKModal.jsx';
import { UploadIcon } from './icons/UploadIcon.jsx';
import { SketchIcon } from './icons/SketchIcon.jsx';
import { RulesIcon } from './icons/RulesIcon.jsx';
import { DiagnosticsIcon } from './icons/DiagnosticsIcon.jsx';
import { WarningIcon } from './icons/WarningIcon.jsx';
import { PassIcon } from './icons/PassIcon.jsx';

const PHASES = { idle: 'idle', loading: 'loading', loaded: 'loaded', empty: 'empty', error: 'error' };

const TABS = [
  { id: 'tab-ingest', label: 'Ingest', icon: UploadIcon },
  { id: 'tab-regulations', label: 'Regulations', icon: RulesIcon },
  { id: 'tab-diagnostics', label: 'Diagnostics', icon: DiagnosticsIcon },
];

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
  const [activeTab, setActiveTab] = useState(0);
  const [textPrompt, setTextPrompt] = useState('');
  const [textResult, setTextResult] = useState(null);
  const [textError, setTextError] = useState(null);
  const [textLoading, setTextLoading] = useState(false);
  const tabRefs = useRef([]);

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

  async function handleGenerateFromText() {
    const prompt = textPrompt.trim();
    if (!prompt) {
      setTextError('Enter a prompt describing the architecture you want to generate.');
      setTextResult(null);
      return;
    }
    setTextError(null);
    setTextResult(null);
    setTextLoading(true);
    try {
      const data = await generateFromText(prompt);
      setTextResult(JSON.stringify(data.architecture, null, 2));
    } catch (err) {
      setTextError(err.message);
    } finally {
      setTextLoading(false);
    }
  }

  // WAI-ARIA tabs keyboard pattern (automatic activation): Arrow keys move
  // focus and activate the adjacent tab; Home/End jump to the first/last tab.
  // The next index is derived from the focused tab (event.currentTarget), not
  // from `activeTab`, so manual focus + arrow-key navigation still lands
  // correctly.
  function handleTabKeyDown(event) {
    const currentIndex = tabRefs.current.indexOf(event.currentTarget);
    if (currentIndex === -1) return;

    let nextIndex;
    switch (event.key) {
      case 'ArrowRight':
        event.preventDefault();
        nextIndex = (currentIndex + 1) % TABS.length;
        break;
      case 'ArrowLeft':
        event.preventDefault();
        nextIndex = (currentIndex - 1 + TABS.length) % TABS.length;
        break;
      case 'Home':
        event.preventDefault();
        nextIndex = 0;
        break;
      case 'End':
        event.preventDefault();
        nextIndex = TABS.length - 1;
        break;
      default:
        return;
    }

    tabRefs.current[nextIndex]?.focus();
    setActiveTab(nextIndex);
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
        <header className="side-panel-header">
          <h1>Validator Dashboard</h1>
          <BYOKModal />
        </header>

        <div role="tablist" aria-label="Dashboard sections" className="tablist">
          {TABS.map((tab, index) => {
            const Icon = tab.icon;
            const selected = activeTab === index;
            return (
              <button
                key={tab.id}
                ref={(el) => {
                  tabRefs.current[index] = el;
                }}
                role="tab"
                id={tab.id}
                aria-selected={selected}
                aria-controls={`${tab.id}-panel`}
                tabIndex={selected ? 0 : -1}
                className={`tab${selected ? ' active' : ''}`}
                onClick={() => setActiveTab(index)}
                onKeyDown={handleTabKeyDown}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        <section
          role="tabpanel"
          id="tab-ingest-panel"
          aria-labelledby="tab-ingest"
          className="panel-section"
          hidden={activeTab !== 0}
        >
          <label className="upload-control">
            Upload .obj
            <input type="file" accept=".obj" onChange={handleFileChange} />
          </label>

          <div className="sketch-upload">
            <SketchIcon size={24} />
            <p className="hint">Drop a 2D sketch here to generate walls.</p>
          </div>

          <div className="text-generation">
            <label htmlFor="text-prompt">Architecture prompt</label>
            <input
              id="text-prompt"
              className="text-prompt"
              type="text"
              value={textPrompt}
              onChange={(event) => setTextPrompt(event.target.value)}
              placeholder="Describe the building you want to generate…"
            />
            <button
              className="button"
              type="button"
              onClick={handleGenerateFromText}
              disabled={textLoading}
            >
              {textLoading ? 'Generating…' : 'Generate'}
            </button>

            {textError && (
              <p className="inline-error" role="alert">{textError}</p>
            )}
            {textResult && (
              <pre className="dsl-result" data-testid="dsl-result">{textResult}</pre>
            )}
          </div>
        </section>

        <section
          role="tabpanel"
          id="tab-regulations-panel"
          aria-labelledby="tab-regulations"
          className="panel-section"
          hidden={activeTab !== 1}
        >
          {rulesError && <p className="inline-error">Thresholds unavailable: {rulesError}</p>}
          {rules && (
            <>
              <h2>Thresholds</h2>
              <dl className="rules">
                <div><dt>Min height</dt><dd>{formatNumber(rules.min_height)} m</dd></div>
                <div><dt>Max height</dt><dd>{formatNumber(rules.max_height)} m</dd></div>
                <div><dt>Min thickness</dt><dd>{formatNumber(rules.min_thickness)} m</dd></div>
                <div><dt>Max thickness</dt><dd>{formatNumber(rules.max_thickness)} m</dd></div>
              </dl>
            </>
          )}
        </section>

        <section
          role="tabpanel"
          id="tab-diagnostics-panel"
          aria-labelledby="tab-diagnostics"
          className="panel-section"
          hidden={activeTab !== 2}
        >
          {phase === PHASES.loaded && (
            <>
              <div className={`status-banner ${hasViolations ? 'violations' : 'pass'}`}>
                {hasViolations
                  ? `${violations.length} violation${violations.length === 1 ? '' : 's'} found`
                  : 'Validation passed'}
              </div>

              {hasViolations && (
                <>
                  <h2><WarningIcon size={16} /> Violations</h2>
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
                  <h2><PassIcon size={16} /> Applied fixes</h2>
                  <ul className="fix-list">
                    {fixes.map((fix, index) => (
                      <li key={index}>
                        {fix.wall_id}: {fix.dimension} {formatNumber(fix.from)} → {formatNumber(fix.to)}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          )}

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
