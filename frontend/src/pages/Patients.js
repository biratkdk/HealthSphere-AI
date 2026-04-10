import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";

import { getRequestErrorMessage } from "../services/api";

const RISK_COLORS = {
  critical: "risk-critical",
  high: "risk-high",
  medium: "risk-medium",
  low: "risk-low",
};

const careUnitsFrom = (patients) => [...new Set(patients.map((patient) => patient.care_unit))].filter(Boolean).sort();

const Patients = () => {
  const [query, setQuery] = useState("");
  const [unitFilter, setUnitFilter] = useState("all");
  const [sortBy, setSortBy] = useState("name");

  const resourceKey = useMemo(() => ["patients", ""], []);
  const { data: allPatients = [], error, isLoading } = useSWR(resourceKey);

  const careUnits = useMemo(() => careUnitsFrom(allPatients), [allPatients]);

  const filtered = useMemo(() => {
    let list = allPatients;
    const normalizedQuery = query.trim().toLowerCase();

    if (normalizedQuery) {
      list = list.filter(
        (patient) =>
          patient.name.toLowerCase().includes(normalizedQuery) ||
          patient.mrn?.toLowerCase().includes(normalizedQuery) ||
          patient.diagnosis?.toLowerCase().includes(normalizedQuery) ||
          patient.care_unit?.toLowerCase().includes(normalizedQuery)
      );
    }

    if (unitFilter !== "all") {
      list = list.filter((patient) => patient.care_unit === unitFilter);
    }

    if (sortBy === "name") {
      list = [...list].sort((left, right) => left.name.localeCompare(right.name));
    } else if (sortBy === "id") {
      list = [...list].sort((left, right) => left.patient_id - right.patient_id);
    } else if (sortBy === "unit") {
      list = [...list].sort((left, right) => (left.care_unit || "").localeCompare(right.care_unit || ""));
    }

    return list;
  }, [allPatients, query, unitFilter, sortBy]);

  const patientMetrics = useMemo(() => {
    const elevatedRisk = allPatients.filter((patient) => ["critical", "high"].includes(patient.risk_band)).length;
    const criticalWatch = allPatients.filter((patient) => patient.risk_band === "critical").length;
    const flaggedPatients = allPatients.filter((patient) => (patient.risk_flags?.length || 0) > 0).length;

    return [
      { label: "Patients", value: allPatients.length, tone: "low" },
      { label: "Care units", value: careUnits.length, tone: "low" },
      { label: "Elevated risk", value: elevatedRisk, tone: elevatedRisk > 0 ? "high" : "low" },
      { label: "Critical watch", value: criticalWatch, tone: criticalWatch > 0 ? "critical" : "low" },
      { label: "Flagged", value: flaggedPatients, tone: flaggedPatients > 0 ? "medium" : "low" },
      { label: "Visible roster", value: filtered.length, tone: "low" },
    ];
  }, [allPatients, careUnits.length, filtered.length]);

  if (isLoading) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Loading patient directory...</p>
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
          <h2>Mission-control roster</h2>
          <p className="subtle-copy">Find the right patient quickly and move into the live workspace.</p>
        </div>
        <label className="field hero-search-field">
          <span>Search patients</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search name, MRN, diagnosis, or care unit"
          />
        </label>
      </section>

      <section className="metrics-grid workspace-kpi-grid">
        {patientMetrics.map((metric) => (
          <article key={metric.label} className={`metric-card metric-card-${metric.tone}`}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className="panel full-span">
        <div className="panel-header">
          <div className="panel-header-stack">
            <h3>Roster</h3>
            <p>Filtered by unit, diagnosis, and current search terms.</p>
          </div>
          <span className="subtle-copy">{filtered.length} results</span>
        </div>

        <div className="directory-toolbar">
          <div className="filter-row directory-filter-row">
            <button
              className={`filter-chip ${unitFilter === "all" ? "active" : ""}`}
              type="button"
              onClick={() => setUnitFilter("all")}
            >
              All units
              <span className="filter-chip-count">{allPatients.length}</span>
            </button>
            {careUnits.map((unit) => {
              const count = allPatients.filter((patient) => patient.care_unit === unit).length;
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

          <div className="sort-row directory-sort-row">
            <span>Sort by</span>
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
              <option value="name">Name</option>
              <option value="id">Patient ID</option>
              <option value="unit">Care unit</option>
            </select>
          </div>
        </div>

        <div className="directory-grid directory-grid-spaced">
          {filtered.map((patient) => (
            <Link key={patient.patient_id} className="roster-card directory-card" to={`/patients/${patient.patient_id}`}>
              <div className="directory-card-copy">
                <div className="patient-card-header">
                  <strong>{patient.name}</strong>
                  <span className={`risk-badge ${RISK_COLORS[patient.risk_band] || "risk-low"}`}>
                    {patient.risk_band || "low"}
                  </span>
                </div>
                <p className="subtle-copy">{patient.care_unit} &middot; {patient.diagnosis}</p>
                <div className="patient-meta-row">
                  <span className="tone tone-low compact-tone">MRN {patient.mrn}</span>
                  <span className="subtle-copy compact-copy">
                    Age {patient.age} &middot; {patient.sex}
                  </span>
                </div>
              </div>
              <span className="subtle-copy directory-card-id">#{patient.patient_id}</span>
            </Link>
          ))}

          {filtered.length === 0 ? (
            <div className="empty-state directory-empty-state">
              <strong>No patients matched the current filters.</strong>
              <span>Clear the current search and unit filters to restore the full roster.</span>
              <button
                className="secondary-button small-button"
                type="button"
                onClick={() => {
                  setQuery("");
                  setUnitFilter("all");
                }}
              >
                Clear filters
              </button>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
};

export default Patients;
