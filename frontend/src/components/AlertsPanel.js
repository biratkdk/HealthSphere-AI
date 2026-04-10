import React from "react";

const AlertsPanel = ({ alerts, patientAlerts }) => {
  return (
    <section className="panel">
      <div className="panel-header">
        <h3>Operational alerts</h3>
        <span className="subtle-copy">{alerts.length} total alerts</span>
      </div>

      <div className="split-panel">
        <div>
          <h4>Patient-specific</h4>
          <ul className="alert-list">
            {patientAlerts.map((alert) => (
              <li key={alert.alert_id} className={`alert-item severity-${alert.severity}`}>
                <strong>{alert.title}</strong>
                <p>{alert.description}</p>
              </li>
            ))}
            {patientAlerts.length === 0 ? <li className="subtle-copy">No open alerts for the active patient.</li> : null}
          </ul>
        </div>

        <div>
          <h4>System queue</h4>
          <ul className="alert-list">
            {alerts.map((alert) => (
              <li key={alert.alert_id} className={`alert-item severity-${alert.severity}`}>
                <div className="alert-title-row">
                  <strong>{alert.title}</strong>
                  <span>Patient {alert.patient_id}</span>
                </div>
                <p>{alert.description}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
};

export default AlertsPanel;

