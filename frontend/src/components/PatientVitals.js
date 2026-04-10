import React from "react";

const VITAL_RANGES = {
  heart_rate:        { min: 60,  max: 100, low: 40,  high: 120, unit: "bpm",  label: "Heart Rate" },
  respiratory_rate:  { min: 12,  max: 20,  low: 8,   high: 28,  unit: "rpm",  label: "Respiratory" },
  systolic_bp:       { min: 90,  max: 120, low: 70,  high: 160, unit: "mmHg", label: "Systolic BP" },
  temperature_c:     { min: 36.1, max: 37.2, low: 35, high: 38.5, unit: "°C", label: "Temperature" },
  oxygen_saturation: { min: 95,  max: 100, low: 88,  high: 100, unit: "%",   label: "O₂ Sat" },
  pain_score:        { min: 0,   max: 3,   low: 0,   high: 10,  unit: "/10", label: "Pain Score" },
};

const getVitalStatus = (key, value) => {
  const r = VITAL_RANGES[key];
  if (!r) return "normal";
  if (value < r.low || value > r.high) return "critical";
  if (value < r.min || value > r.max) return (key === "pain_score" && value > 6) ? "alert" : "warning";
  return "normal";
};

const getBarPercent = (key, value) => {
  const r = VITAL_RANGES[key];
  if (!r) return 50;
  return Math.min(100, Math.max(0, ((value - r.low) / (r.high - r.low)) * 100));
};

const VitalCard = ({ name, value, config }) => {
  const status = getVitalStatus(name, value);
  const barPct = getBarPercent(name, value);
  return (
    <article className={`vital-card vital-${status}`}>
      <span className="vital-label">{config.label}</span>
      <span className="vital-value">
        {value}
        <span className="vital-unit"> {config.unit}</span>
      </span>
      <div className="vital-bar-track">
        <div className="vital-bar-fill" style={{ width: `${barPct}%` }} />
      </div>
    </article>
  );
};

const PatientVitals = ({ summary }) => {
  const v = summary.patient.vitals;

  return (
    <section className="panel">
      <div className="panel-header">
        <h3>Physiologic status</h3>
        <span className="subtle-copy">Patient {summary.patient.patient_id}</span>
      </div>

      <div className="vitals-grid">
        <VitalCard name="heart_rate"        value={v.heart_rate}        config={VITAL_RANGES.heart_rate} />
        <VitalCard name="respiratory_rate"  value={v.respiratory_rate}  config={VITAL_RANGES.respiratory_rate} />
        <VitalCard name="systolic_bp"       value={v.systolic_bp}       config={VITAL_RANGES.systolic_bp} />
        <VitalCard name="temperature_c"     value={v.temperature_c}     config={VITAL_RANGES.temperature_c} />
        <VitalCard name="oxygen_saturation" value={v.oxygen_saturation} config={VITAL_RANGES.oxygen_saturation} />
        <VitalCard name="pain_score"        value={v.pain_score}        config={VITAL_RANGES.pain_score} />
      </div>

      <div className="split-panel" style={{ marginTop: 18 }}>
        <div>
          <h4>Risk drivers</h4>
          {summary.icu_risk.drivers.length > 0 ? (
            <ul className="action-list compact">
              {summary.icu_risk.drivers.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          ) : (
            <p className="subtle-copy" style={{ marginTop: 10 }}>No active risk drivers.</p>
          )}
        </div>
        <div>
          <h4>Latest labs</h4>
          <ul className="data-list">
            {summary.patient.labs.slice(0, 8).map((lab) => (
              <li key={`${lab.name}-${lab.collected_at}`}>
                <span>{lab.name}</span>
                <strong>{lab.value} {lab.unit}</strong>
              </li>
            ))}
            {summary.patient.labs.length === 0 && (
              <li className="subtle-copy">No lab results on record.</li>
            )}
          </ul>
        </div>
      </div>
    </section>
  );
};

export default PatientVitals;
