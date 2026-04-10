import React from "react";
import { Link } from "react-router-dom";

import AlertsPanel from "./AlertsPanel";
import CareUnitChart from "./CareUnitChart";
import ImagingResults from "./ImagingResults";
import NotificationsPanel from "./NotificationsPanel";
import PatientVitals from "./PatientVitals";
import RiskRadarChart from "./RiskRadarChart";
import SystemStatusPanel from "./SystemStatusPanel";

const toneClass = (tone) => `tone tone-${tone || "low"}`;

const riskClass = (band) => {
  const map = { critical: "risk-critical", high: "risk-high", medium: "risk-medium", low: "risk-low" };
  return `risk-badge ${map[band] || "risk-low"}`;
};

const Dashboard = ({
  patients,
  alerts,
  analytics,
  notifications,
  reportJobs,
  summary,
  models,
  metrics,
  loading,
  error,
  selectedPatientId,
  canViewModels,
  liveFeedConnected,
  liveFeedLastEventAt,
  liveFeedError,
  onPatientChange,
  onNotificationRead,
}) => {
  if (loading) {
    return (
      <div className="page-grid dashboard-grid">
        <section className="panel loading-panel" style={{ gridColumn: "1 / -1" }}>
          <div className="spinner" />
          <p>Loading care operations&hellip;</p>
        </section>
        {[...Array(5)].map((_, i) => (
          <section key={i} className="panel" style={{ gridColumn: i === 0 ? "span 12" : "span 6" }}>
            <div className="skeleton skeleton-block" />
            <div className="skeleton skeleton-line wide" />
            <div className="skeleton skeleton-line medium" />
            <div className="skeleton skeleton-line short" />
          </section>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <section className="panel error-panel" style={{ gridColumn: "1 / -1" }}>
        <strong className="error-text">Unable to load dashboard</strong>
        <p>{error}</p>
        <button className="secondary-button small-button" type="button" onClick={() => window.location.reload()}>
          Reload
        </button>
      </section>
    );
  }

  if (!summary) {
    return (
      <section className="panel loading-panel">
        <div className="spinner" />
        <p>Waiting for patient data&hellip;</p>
      </section>
    );
  }

  const roster = patients.slice(0, 8);
  const liveFeedLabel = liveFeedLastEventAt
    ? new Date(liveFeedLastEventAt).toLocaleTimeString()
    : "connecting";

  const riskSnapshot = [
    { label: "ICU deterioration",  value: `${Math.round(summary.icu_risk.icu_risk * 100)}%`,            tone: summary.icu_risk.risk_band },
    { label: "Diabetes watch",     value: `${Math.round(summary.disease_risk.diabetes_risk * 100)}%`,   tone: summary.disease_risk.overall_risk_band },
    { label: "Cardiac signal",     value: `${Math.round(summary.disease_risk.heart_disease_risk * 100)}%`, tone: summary.disease_risk.overall_risk_band },
    { label: "Sepsis watch",       value: `${Math.round(summary.disease_risk.sepsis_watch_risk * 100)}%`, tone: summary.disease_risk.overall_risk_band },
  ];

  return (
    <div className="page-grid dashboard-grid">
      {/* ── Hero ── */}
      <section className="hero-panel command-hero">
        <div className="hero-copy">
          <p className="eyebrow">Operations command center</p>
          <h2>{summary.patient.name}</h2>
          <p className="subtle-copy">
            {summary.patient.care_unit} &middot; {summary.patient.diagnosis} &middot; Last updated{" "}
            {new Date(summary.patient.last_updated).toLocaleString()}
          </p>
          <div className="hero-badges">
            <span className={riskClass(summary.icu_risk.risk_band)}>{summary.icu_risk.risk_band} acuity</span>
            <span className={toneClass(summary.treatment.priority)}>{summary.treatment.priority} priority</span>
            <span className="tone tone-low">{summary.patient.risk_flags.length} flags</span>
            <span className={toneClass(liveFeedConnected ? "low" : liveFeedError ? "high" : "medium")}>
              <span className={`status-dot ${liveFeedConnected ? "dot-live" : liveFeedError ? "dot-error" : "dot-warn"}`} />
              {liveFeedConnected ? `live · ${liveFeedLabel}` : "syncing"}
            </span>
          </div>
        </div>

        <div className="hero-actions hero-actions-grid">
          <label className="field">
            <span>Active patient</span>
            <select value={selectedPatientId} onChange={(e) => onPatientChange(Number(e.target.value))}>
              {patients.map((p) => (
                <option key={p.patient_id} value={p.patient_id}>
                  {p.name} (#{p.patient_id})
                </option>
              ))}
            </select>
          </label>
          <div className="quick-action-row">
            <Link className="primary-button accent-button" to="/reports">Generate report</Link>
            <Link className="secondary-button" to={`/patients/${summary.patient.patient_id}`}>Open workspace</Link>
          </div>
          <div className="quick-action-row">
            <Link className="secondary-button" to="/notifications">Review inbox</Link>
            <Link className="secondary-button" to="/profile">Edit profile</Link>
          </div>
        </div>
      </section>

      {/* ── KPI metrics ── */}
      <section className="metrics-grid">
        {metrics.map((m) => (
          <article key={m.label} className={`metric-card metric-card-${m.tone || "low"}`}>
            <span>{m.label}</span>
            <strong>{m.value}</strong>
          </article>
        ))}
      </section>

      {/* ── Patient roster ── */}
      <section className="panel panel-span-4">
        <div className="panel-header">
          <h3>Patient roster</h3>
          <Link className="subtle-link" to="/patients">{patients.length} monitored</Link>
        </div>
        <div className="roster-list">
          {roster.map((p) => {
            const isActive = p.patient_id === summary.patient.patient_id;
            return (
              <button
                key={p.patient_id}
                className={`roster-card ${isActive ? "is-active" : ""}`}
                type="button"
                onClick={() => onPatientChange(p.patient_id)}
              >
                <div>
                  <strong>{p.name}</strong>
                  <p className="subtle-copy">{p.care_unit} &middot; {p.diagnosis}</p>
                </div>
                <span className="subtle-copy">#{p.patient_id}</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* ── Care plan + risk snapshot ── */}
      <section className="panel panel-span-5">
        <div className="panel-header">
          <h3>Coordinated care plan</h3>
          <span className={toneClass(summary.treatment.priority)}>{summary.treatment.priority}</span>
        </div>
        <p className="subtle-copy">{summary.treatment.rationale}</p>
        <ul className="action-list">
          {summary.treatment.actions.map((a) => <li key={a}>{a}</li>)}
        </ul>
        <div className="risk-grid" style={{ marginTop: 18 }}>
          {riskSnapshot.map((item) => (
            <article key={item.label} className="status-card elevated-card">
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <span className={riskClass(item.tone)}>{item.tone}</span>
            </article>
          ))}
        </div>
      </section>

      {/* ── Risk radar chart ── */}
      <section className="panel panel-span-3">
        <RiskRadarChart summary={summary} />
      </section>

      {/* ── Physiologic vitals ── */}
      <PatientVitals summary={summary} />

      {/* ── Report queue ── */}
      <section className="panel">
        <div className="panel-header">
          <h3>Report activity</h3>
          <span className="subtle-copy">
            {analytics
              ? `${analytics.report_queue.queued} queued · ${analytics.report_queue.running} running`
              : "Queue feed"}
          </span>
        </div>
        <div className="queue-list">
          {reportJobs.slice(0, 6).map((job) => (
            <article key={job.job_id} className="queue-row elevated-card">
              <div>
                <strong>Patient {job.patient_id}</strong>
                <p className="subtle-copy">{new Date(job.created_at).toLocaleString()}</p>
                <p className="subtle-copy">
                  {job.workflow_stage.replaceAll("_", " ")} &middot; attempt {job.attempt_count}/{job.max_attempts}
                </p>
              </div>
              <div className="queue-meta">
                <span className={toneClass(job.status === "failed" ? "critical" : job.status === "running" ? "medium" : "low")}>
                  {job.status}
                </span>
                <span className="subtle-copy">{job.progress_percent}%</span>
                <span className="subtle-copy">{job.requested_by || "system"}</span>
              </div>
            </article>
          ))}
          {reportJobs.length === 0 && (
            <div className="empty-state">
              <span className="empty-state-icon">📋</span>
              <span>No report jobs active right now.</span>
            </div>
          )}
        </div>
      </section>

      <NotificationsPanel notifications={notifications} onMarkRead={onNotificationRead} />
      <ImagingResults patientId={summary.patient.patient_id} />
      <AlertsPanel alerts={alerts} patientAlerts={summary.open_alerts} />
      <SystemStatusPanel analytics={analytics} reportJobs={reportJobs} />

      {canViewModels && models.length > 0 && (
        <section className="panel full-span">
          <div className="panel-header">
            <h3>Model registry</h3>
            <span className="subtle-copy">{models.length} active entries</span>
          </div>
          <div className="registry-list registry-grid">
            {models.map((model) => (
              <article key={model.name} className="registry-card elevated-card">
                <div className="registry-title-row">
                  <strong>{model.name}</strong>
                  <span className={toneClass(model.validation_status === "approved" ? "low" : "medium")}>
                    {model.validation_status}
                  </span>
                </div>
                <div className="registry-meta-grid">
                  <article><span>Version</span><strong>{model.version}</strong></article>
                  <article><span>Serving mode</span><strong>{model.serving_mode}</strong></article>
                  <article><span>Artifact</span><strong>{model.artifact_available ? "packaged" : "unavailable"}</strong></article>
                  <article><span>Owner</span><strong>{model.owner}</strong></article>
                </div>
                <p className="subtle-copy registry-artifact-path">{model.artifact_path}</p>
                {model.monitoring_tags?.length > 0 && (
                  <div className="registry-tag-row">
                    {model.monitoring_tags.map((tag) => (
                      <span key={tag} className="tone tone-low">{tag}</span>
                    ))}
                  </div>
                )}
                {model.notes?.length > 0 && (
                  <ul className="registry-note-list">
                    {model.notes.map((note) => (
                      <li key={note} className="subtle-copy">{note}</li>
                    ))}
                  </ul>
                )}
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default Dashboard;
