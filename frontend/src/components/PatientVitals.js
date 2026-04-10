import React from "react";

const PatientVitals = ({ summary }) => {
  const vitals = summary.patient.vitals;

  return (
    <section className="panel">
      <div className="panel-header">
        <h3>Physiologic trend</h3>
        <span className="subtle-copy">Patient {summary.patient.patient_id}</span>
      </div>

      <div className="vitals-grid">
        <article>
          <span>Heart rate</span>
          <strong>{vitals.heart_rate} bpm</strong>
        </article>
        <article>
          <span>Respiratory rate</span>
          <strong>{vitals.respiratory_rate} rpm</strong>
        </article>
        <article>
          <span>Systolic pressure</span>
          <strong>{vitals.systolic_bp} mmHg</strong>
        </article>
        <article>
          <span>Temperature</span>
          <strong>{vitals.temperature_c} C</strong>
        </article>
        <article>
          <span>Oxygen saturation</span>
          <strong>{vitals.oxygen_saturation}%</strong>
        </article>
        <article>
          <span>Pain score</span>
          <strong>{vitals.pain_score}/10</strong>
        </article>
      </div>

      <div className="split-panel">
        <div>
          <h4>Risk drivers</h4>
          <ul className="action-list compact">
            {summary.icu_risk.drivers.map((driver) => (
              <li key={driver}>{driver}</li>
            ))}
          </ul>
        </div>
        <div>
          <h4>Latest labs</h4>
          <ul className="data-list">
            {summary.patient.labs.map((lab) => (
              <li key={`${lab.name}-${lab.collected_at}`}>
                <span>{lab.name}</span>
                <strong>
                  {lab.value} {lab.unit}
                </strong>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
};

export default PatientVitals;
