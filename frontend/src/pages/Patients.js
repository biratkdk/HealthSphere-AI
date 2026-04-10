import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";

import { getRequestErrorMessage } from "../services/api";

const RISK_COLORS = {
  critical: "risk-critical",
  high:     "risk-high",
  medium:   "risk-medium",
  low:      "risk-low",
};

const careUnitsFrom = (patients) => {
  const units = [...new Set(patients.map((p) => p.care_unit))].filter(Boolean).sort();
  return units;
};

const Patients = () => {
  const [query, setQuery]   = useState("");
  const [unitFilter, setUnitFilter] = useState("all");
  const [sortBy, setSortBy] = useState("name");

  const resourceKey = useMemo(() => ["patients", ""], []);
  const { data: allPatients = [], error, isLoading } = useSWR(resourceKey);

  const careUnits = useMemo(() => careUnitsFrom(allPatients), [allPatients]);

  const filtered = useMemo(() => {
    let list = allPatients;
    const q = query.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.mrn?.toLowerCase().includes(q) ||
          p.diagnosis?.toLowerCase().includes(q) ||
          p.care_unit?.toLowerCase().includes(q)
      );
    }
    if (unitFilter !== "all") {
      list = list.filter((p) => p.care_unit === unitFilter);
    }
    if (sortBy === "name") {
      list = [...list].sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === "id") {
      list = [...list].sort((a, b) => a.patient_id - b.patient_id);
    } else if (sortBy === "unit") {
      list = [...list].sort((a, b) => (a.care_unit || "").localeCompare(b.care_unit || ""));
    }
    return list;
  }, [allPatients, query, unitFilter, sortBy]);

  if (isLoading) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Loading patient directory&hellip;</p>
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-grid">
        <section className="panel full-span error-panel">
          <strong className="error-text">Unable to load patient directory</strong>
          <p>{getRequestErrorMessage(error, "Please try again.")}</p>
        </section>
      </div>
    );
  }

  return (
    <div className="page-grid">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Patient directory</p>
          <h2>Clinical roster</h2>
          <p className="subtle-copy">
            {allPatients.length} patients monitored across {careUnits.length} care units.
          </p>
        </div>
        <label className="field hero-search-field">
          <span>Search patients</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Name, MRN, diagnosis, care unit…"
          />
        </label>
      </section>

      <section className="panel full-span">
        <div className="panel-header">
          <h3>Roster</h3>
          <span className="subtle-copy">{filtered.length} results</span>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12 }}>
          <div className="filter-row" style={{ marginTop: 0 }}>
            <button
              className={`filter-chip ${unitFilter === "all" ? "active" : ""}`}
              type="button"
              onClick={() => setUnitFilter("all")}
            >
              All
              <span className="filter-chip-count">{allPatients.length}</span>
            </button>
            {careUnits.map((unit) => {
              const count = allPatients.filter((p) => p.care_unit === unit).length;
              return (
                <button
                  key={unit}
                  className={`filter-chip ${unitFilter === unit ? "active" : ""}`}
                  type="button"
                  onClick={() => setUnitFilter(unit)}
                >
                  {unit}
                  <span className="filter-chip-count">{count}</span>
                </button>
              );
            })}
          </div>
          <div className="sort-row" style={{ marginTop: 0 }}>
            <span>Sort by</span>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="name">Name</option>
              <option value="id">Patient ID</option>
              <option value="unit">Care unit</option>
            </select>
          </div>
        </div>

        <div className="directory-grid" style={{ marginTop: 18 }}>
          {filtered.map((p) => (
            <Link key={p.patient_id} className="roster-card directory-card" to={`/patients/${p.patient_id}`}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="patient-card-header">
                  <strong>{p.name}</strong>
                  <span className={`risk-badge ${RISK_COLORS[p.risk_band] || "risk-low"}`}>
                    {p.risk_band || "low"}
                  </span>
                </div>
                <p className="subtle-copy">{p.care_unit} &middot; {p.diagnosis}</p>
                <div className="patient-meta-row">
                  <span className="tone tone-low" style={{ fontSize: "0.76rem", padding: "3px 8px" }}>
                    MRN {p.mrn}
                  </span>
                  <span className="subtle-copy" style={{ fontSize: "0.78rem" }}>
                    Age {p.age} &middot; {p.sex}
                  </span>
                </div>
              </div>
              <span className="subtle-copy" style={{ fontSize: "0.82rem", flexShrink: 0 }}>
                #{p.patient_id}
              </span>
            </Link>
          ))}
          {filtered.length === 0 && (
            <div className="empty-state" style={{ gridColumn: "1 / -1" }}>
              <span className="empty-state-icon">🔍</span>
              <span>No patients matched the current filters.</span>
              <button
                className="secondary-button small-button"
                type="button"
                onClick={() => { setQuery(""); setUnitFilter("all"); }}
              >
                Clear filters
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default Patients;
