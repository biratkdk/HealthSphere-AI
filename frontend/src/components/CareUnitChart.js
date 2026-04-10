import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      <span>{payload[0].value} patients</span>
      {payload[1] ? <span style={{ color: "var(--critical)" }}>{payload[1].value} alerts</span> : null}
    </div>
  );
};

const CareUnitChart = ({ careUnits = [] }) => {
  if (!careUnits.length) return null;

  const data = careUnits.map((u) => ({
    name: u.care_unit.replace(" Unit", "").replace("Unit", "").trim(),
    patients: u.patient_count,
    alerts: u.open_alerts,
  }));

  return (
    <div className="chart-container">
      <div className="panel-header" style={{ marginBottom: 12 }}>
        <h4>Care unit census</h4>
        <span className="subtle-copy">{careUnits.reduce((s, u) => s + u.patient_count, 0)} total</span>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} barSize={14} margin={{ top: 0, right: 8, left: -24, bottom: 0 }}>
          <XAxis
            dataKey="name"
            tick={{ fill: "var(--muted)", fontSize: 10, fontFamily: "IBM Plex Sans" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "var(--muted)", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "var(--teal-soft)" }} />
          <Bar dataKey="patients" radius={[6, 6, 0, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.alerts > 0 ? "var(--coral)" : "var(--teal)"}
                fillOpacity={0.72}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default CareUnitChart;
