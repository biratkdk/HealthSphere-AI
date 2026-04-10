import React from "react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <strong>{payload[0].payload.subject}</strong>
      <span>{Math.round(payload[0].value)}%</span>
    </div>
  );
};

const RiskRadarChart = ({ summary }) => {
  const dr = summary.disease_risk;
  const ir = summary.icu_risk;

  const data = [
    { subject: "ICU Risk", value: Math.round(ir.icu_risk * 100), fullMark: 100 },
    { subject: "Diabetes", value: Math.round(dr.diabetes_risk * 100), fullMark: 100 },
    { subject: "Cardiac", value: Math.round(dr.heart_disease_risk * 100), fullMark: 100 },
    { subject: "Sepsis", value: Math.round(dr.sepsis_watch_risk * 100), fullMark: 100 },
    { subject: "Anomaly", value: Math.round((summary.imaging?.anomaly_score ?? 0) * 100), fullMark: 100 },
  ];

  const maxRisk = Math.max(...data.map((d) => d.value));
  const radarColor = maxRisk >= 65 ? "#a23f3f" : maxRisk >= 35 ? "#ca674c" : "#0b6f70";

  return (
    <div className="chart-container">
      <div className="panel-header">
        <h3>Risk profile</h3>
        <span className={`tone tone-${ir.risk_band}`}>{ir.risk_band} acuity</span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <RadarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
          <PolarGrid stroke="var(--line)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: "var(--muted)", fontSize: 11, fontFamily: "IBM Plex Sans" }}
          />
          <Radar
            dataKey="value"
            stroke={radarColor}
            fill={radarColor}
            fillOpacity={0.18}
            strokeWidth={2}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default RiskRadarChart;
