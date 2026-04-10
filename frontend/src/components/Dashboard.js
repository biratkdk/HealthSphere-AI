import React from "react";
import { Link } from "react-router-dom";

import AlertsPanel from "./AlertsPanel";
import ImagingResults from "./ImagingResults";
import NotificationsPanel from "./NotificationsPanel";
import PatientVitals from "./PatientVitals";
import SystemStatusPanel from "./SystemStatusPanel";

const toneClassName = (tone) => `tone tone-${tone || "low"}`;

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
    return <section className="panel">Loading care operations view...</section>;
  }

  if (error) {
    return <section className="panel error-panel">{error}</section>;
  }

  if (!summary) {
    return <section className="panel">No patient summary available.</section>;
  }

  const roster = patients.slice(0, 8);
  const liveFeedLabel = liveFeedLastEventAt ? new Date(liveFeedLastEventAt).toLocaleTimeString() : "connecting";
  const riskSnapshot = [
    {
      label: "ICU deterioration",
      value: `${Math.round(summary.icu_risk.icu_risk * 100)}%`,
      tone: summary.icu_risk.risk_band,
    },
    {
      label: "Diabetes watch",
      value: `${Math.round(summary.disease_risk.diabetes_risk * 100)}%`,
      tone: summary.disease_risk.overall_risk_band,
    },
    {
      label: "Cardiac signal",
      value: `${Math.round(summary.disease_risk.heart_disease_risk * 100)}%`,
      tone: summary.disease_risk.overall_risk_band,
    },
    {
      label: "Sepsis watch",
      value: `${Math.round(summary.disease_risk.sepsis_watch_risk * 100)}%`,
      tone: summary.disease_risk.overall_risk_band,
    },
  ];

  return (
    <div className="page-grid dashboard-grid">
      <section className="hero-panel command-hero">
        <div className="hero-copy">
          <p className="eyebrow">Operations command center</p>
          <h2>{summary.patient.name}</h2>
          <p className="subtle-copy">
            {summary.patient.care_unit} | {summary.patient.diagnosis} | Last updated{" "}
            {new Date(summary.patient.last_updated).toLocaleString()}
          </p>

          <div className="hero-badges">
            <span className={toneClassName(summary.icu_risk.risk_band)}>{summary.icu_risk.risk_band} acuity</span>
            <span className={toneClassName(summary.treatment.priority)}>{summary.treatment.priority} treatment priority</span>
            <span className="tone tone-low">{summary.patient.risk_flags.length} active flags</span>
            <span className={toneClassName(liveFeedConnected ? "low" : liveFeedError ? "high" : "medium")}>
              live sync {liveFeedLabel}
            </span>
          </div>
        </div>

        <div className="hero-actions hero-actions-grid">
          <label className="field">
            <span>Active patient</span>
            <select value={selectedPatientId} onChange={(event) => onPatientChange(Number(event.target.value))}>
              {patients.map((patient) => (
                <option key={patient.patient_id} value={patient.patient_id}>
                  {patient.name} ({patient.patient_id})
                </option>
              ))}
            </select>
          </label>

          <div className="quick-action-row">
            <Link className="primary-button accent-button" to="/reports">
              Generate report
            </Link>
            <Link className="secondary-button" to={`/patients/${summary.patient.patient_id}`}>
              Open patient workspace
            </Link>
          </div>

          <div className="quick-action-row">
            <Link className="secondary-button" to="/notifications">
              Review inbox
            </Link>
            <Link className="secondary-button" to="/profile">
              Edit profile
            </Link>
          </div>
        </div>
      </section>

      <section className="metrics-grid">
        {metrics.map((metric) => (
          <article key={metric.label} className={`metric-card metric-card-${metric.tone || "low"}`}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className="panel panel-span-4">
        <div className="panel-header">
          <h3>Patient roster</h3>
          <Link className="subtle-link" to="/patients">
            {patients.length} monitored patients
          </Link>
        </div>

        <div className="roster-list">
          {roster.map((patient) => {
            const isActive = patient.patient_id === summary.patient.patient_id;
            return (
              <button
                key={patient.patient_id}
                className={`roster-card ${isActive ? "is-active" : ""}`}
                type="button"
                onClick={() => onPatientChange(patient.patient_id)}
              >
                <div>
                  <strong>{patient.name}</strong>
                  <p className="subtle-copy">
                    {patient.care_unit} | {patient.diagnosis}
                  </p>
                </div>
                <span className="subtle-copy">#{patient.patient_id}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="panel panel-span-8">
        <div className="panel-header">
          <h3>Coordinated care plan</h3>
          <span className={toneClassName(summary.treatment.priority)}>{summary.treatment.priority}</span>
        </div>

        <p className="subtle-copy">{summary.treatment.rationale}</p>
        <ul className="action-list">
          {summary.treatment.actions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>

        <div className="risk-grid">
          {riskSnapshot.map((item) => (
            <article key={item.label} className="status-card elevated-card">
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <span className={toneClassName(item.tone)}>{item.tone}</span>
            </article>
          ))}
        </div>
      </section>

      <PatientVitals summary={summary} />

      <section className="panel">
        <div className="panel-header">
          <h3>Report activity</h3>
          <span className="subtle-copy">
            {analytics ? `${analytics.report_queue.queued} queued | ${analytics.report_queue.running} running` : "Queue feed"}
          </span>
        </div>

        <div className="queue-list">
          {reportJobs.slice(0, 6).map((job) => (
            <article key={job.job_id} className="queue-row elevated-card">
              <div>
                <strong>Patient {job.patient_id}</strong>
                <p className="subtle-copy">{new Date(job.created_at).toLocaleString()}</p>
                <p className="subtle-copy">
                  {job.workflow_stage.replaceAll("_", " ")} | attempt {job.attempt_count}/{job.max_attempts}
                </p>
              </div>
              <div className="queue-meta">
                <span className={toneClassName(job.status === "failed" ? "critical" : job.status === "running" ? "medium" : "low")}>
                  {job.status}
                </span>
                <span className="subtle-copy">{job.progress_percent}% complete</span>
                <span className="subtle-copy">{job.requested_by || "system"}</span>
              </div>
            </article>
          ))}
          {reportJobs.length === 0 ? <p className="subtle-copy">No report jobs are active right now.</p> : null}
        </div>
      </section>

      <NotificationsPanel notifications={notifications} onMarkRead={onNotificationRead} />
      <ImagingResults patientId={summary.patient.patient_id} />
      <AlertsPanel alerts={alerts} patientAlerts={summary.open_alerts} />
      <SystemStatusPanel analytics={analytics} reportJobs={reportJobs} />

      {canViewModels ? (
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
                  <span className={toneClassName(model.validation_status === "approved" ? "low" : "medium")}>
                    {model.validation_status}
                  </span>
                </div>

                <div className="registry-meta-grid">
                  <article>
                    <span>Version</span>
                    <strong>{model.version}</strong>
                  </article>
                  <article>
                    <span>Serving mode</span>
                    <strong>{model.serving_mode}</strong>
                  </article>
                  <article>
                    <span>Artifact</span>
                    <strong>{model.artifact_available ? "packaged" : "unavailable"}</strong>
                  </article>
                  <article>
                    <span>Owner</span>
                    <strong>{model.owner}</strong>
                  </article>
                </div>

                <p className="subtle-copy registry-artifact-path">{model.artifact_path}</p>

                {model.monitoring_tags?.length ? (
                  <div className="registry-tag-row">
                    {model.monitoring_tags.map((tag) => (
                      <span key={tag} className="tone tone-low">
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : null}

                {model.notes?.length ? (
                  <ul className="registry-note-list">
                    {model.notes.map((note) => (
                      <li key={note} className="subtle-copy">
                        {note}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
};

export default Dashboard;
