import React from "react";

const SEV_LABELS = { critical: "🔴", high: "🟠", medium: "🟡", low: "🟢" };

const AlertsPanel = ({ alerts, patientAlerts }) => {
  return (
    <section className="panel">
      <div className="panel-header">
        <h3>Operational alerts</h3>
        <span className="subtle-copy">{alerts.length} total</span>
      </div>

      <div className="split-panel">
        <div>
          <h4>Patient-specific</h4>
          {patientAlerts.length === 0 ? (
            <div className="empty-state" style={{ padding: "20px 0" }}>
              <span className="empty-state-icon">✓</span>
              <span>No open alerts for this patient.</span>
            </div>
          ) : (
            <ul className="alert-list">
              {patientAlerts.map((alert) => (
                <li key={alert.alert_id} className={`alert-item severity-${alert.severity}`}>
                  <div className="alert-item-inner">
                    <div>
                      <strong>
                        {SEV_LABELS[alert.severity] || ""} {alert.title}
                      </strong>
                      <p style={{ margin: "4px 0 0", fontSize: "0.88rem", color: "var(--muted)" }}>
                        {alert.description}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h4>System queue</h4>
          {alerts.length === 0 ? (
            <div className="empty-state" style={{ padding: "20px 0" }}>
              <span className="empty-state-icon">✓</span>
              <span>Queue is clear.</span>
            </div>
          ) : (
            <ul className="alert-list">
              {alerts.map((alert) => (
                <li key={alert.alert_id} className={`alert-item severity-${alert.severity}`}>
                  <div className="alert-item-inner">
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="alert-title-row">
                        <strong>
                          {SEV_LABELS[alert.severity] || ""} {alert.title}
                        </strong>
                        <span className="subtle-copy" style={{ fontSize: "0.78rem", whiteSpace: "nowrap" }}>
                          #{alert.patient_id}
                        </span>
                      </div>
                      <p style={{ margin: "4px 0 0", fontSize: "0.88rem", color: "var(--muted)" }}>
                        {alert.description}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
};

export default AlertsPanel;
