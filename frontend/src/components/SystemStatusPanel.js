import React from "react";
import CareUnitChart from "./CareUnitChart";

const SystemStatusPanel = ({ analytics, reportJobs = [] }) => {
  if (!analytics) {
    return (
      <section className="panel">
        <div className="panel-header"><h3>System status</h3></div>
        <div className="loading-panel" style={{ padding: "24px 0" }}>
          <div className="spinner" />
        </div>
      </section>
    );
  }

  const caps = analytics.capabilities;
  const capCards = [
    { label: "Task execution", value: caps.task_execution_mode, ok: true },
    { label: "Storage",        value: caps.storage_backend,     ok: true },
    { label: "Live updates",   value: caps.live_updates_enabled ? "enabled" : "disabled", ok: caps.live_updates_enabled },
    { label: "Metrics",        value: caps.metrics_enabled ? "enabled" : "disabled",       ok: caps.metrics_enabled },
    { label: "Single sign-on", value: caps.oidc_enabled ? "enabled" : "disabled",          ok: caps.oidc_enabled },
  ];

  return (
    <section className="panel">
      <div className="panel-header">
        <h3>System status</h3>
        <span className="subtle-copy">
          {analytics.report_queue.queued} queued &middot; {analytics.report_queue.running} running
        </span>
      </div>

      <div className="stats-row" style={{ marginBottom: 16 }}>
        <div className="stat-item">
          <span>Patients</span>
          <strong>{analytics.total_patients}</strong>
        </div>
        <div className="stat-item">
          <span>Open alerts</span>
          <strong>{analytics.open_alerts}</strong>
        </div>
        <div className="stat-item">
          <span>Critical</span>
          <strong>{analytics.critical_alerts}</strong>
        </div>
        <div className="stat-item">
          <span>Unread inbox</span>
          <strong>{analytics.unread_notifications}</strong>
        </div>
      </div>

      <div className="status-grid">
        {capCards.map((c) => (
          <article key={c.label} className="status-card elevated-card">
            <span>{c.label}</span>
            <strong style={{ color: c.ok ? "var(--teal)" : "var(--muted)" }}>{c.value}</strong>
          </article>
        ))}
      </div>

      {analytics.care_units?.length > 0 && (
        <div className="panel-section">
          <CareUnitChart careUnits={analytics.care_units} />
        </div>
      )}
    </section>
  );
};

export default SystemStatusPanel;
