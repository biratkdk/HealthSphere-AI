import React from "react";

const SystemStatusPanel = ({ analytics, reportJobs = [] }) => {
  if (!analytics) {
    return (
      <section className="panel">
        <div className="panel-header">
          <h3>System status</h3>
        </div>
        <p className="subtle-copy">Analytics are not available yet.</p>
      </section>
    );
  }

  const capabilityCards = [
    { label: "Task execution", value: analytics.capabilities.task_execution_mode },
    { label: "Storage", value: analytics.capabilities.storage_backend },
    { label: "Single sign-on", value: analytics.capabilities.oidc_enabled ? "enabled" : "disabled" },
    { label: "Metrics", value: analytics.capabilities.metrics_enabled ? "enabled" : "disabled" },
    { label: "Live updates", value: analytics.capabilities.live_updates_enabled ? "enabled" : "disabled" },
  ];

  return (
    <section className="panel">
      <div className="panel-header">
        <h3>System status</h3>
        <span className="subtle-copy">
          Queue {analytics.report_queue.queued} queued | {analytics.report_queue.running} running
        </span>
      </div>

        <div className="status-grid">
          {capabilityCards.map((capability) => (
          <article key={capability.label} className="status-card elevated-card">
            <span>{capability.label}</span>
            <strong>{capability.value}</strong>
          </article>
          ))}
        </div>

      <div className="panel-section">
        <div className="panel-header">
          <h4>Care units</h4>
          <span className="subtle-copy">{analytics.care_units.length} monitored units</span>
        </div>
        <div className="care-unit-grid">
          {analytics.care_units.map((careUnit) => (
            <article key={careUnit.care_unit} className="care-unit-card elevated-card">
              <strong>{careUnit.care_unit}</strong>
              <span>{careUnit.patient_count} patients</span>
              <span>{careUnit.open_alerts} open alerts</span>
            </article>
          ))}
        </div>
      </div>

      <div className="panel-section">
        <div className="panel-header">
          <h4>Recent report jobs</h4>
          <span className="subtle-copy">{reportJobs.length} tracked</span>
        </div>
        <div className="queue-list">
          {reportJobs.slice(0, 4).map((job) => (
            <article key={job.job_id} className="queue-row elevated-card">
              <div>
                <strong>Patient {job.patient_id}</strong>
                <p className="subtle-copy">
                  {job.requested_by || "system"} | {job.workflow_stage.replaceAll("_", " ")} | {job.progress_percent}%
                </p>
              </div>
              <span className={`tone tone-${job.status === "failed" ? "critical" : job.status === "running" ? "medium" : "low"}`}>
                {job.status}
              </span>
            </article>
          ))}
          {reportJobs.length === 0 ? <p className="subtle-copy">No report jobs are available yet.</p> : null}
        </div>
      </div>
    </section>
  );
};

export default SystemStatusPanel;
