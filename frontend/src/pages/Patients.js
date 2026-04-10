import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";

import { getRequestErrorMessage } from "../services/api";

const Patients = () => {
  const [query, setQuery] = useState("");
  const resourceKey = useMemo(() => ["patients", query.trim()], [query]);
  const {
    data: patients = [],
    error,
    isLoading,
  } = useSWR(resourceKey);

  if (isLoading) {
    return <section className="panel">Loading patient directory...</section>;
  }

  if (error) {
    return <section className="panel error-panel">{getRequestErrorMessage(error, "Unable to load the patient directory.")}</section>;
  }

  return (
    <div className="page-grid">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Patient directory</p>
          <h2>Clinical roster</h2>
          <p className="subtle-copy">Search the monitored roster by name, MRN, diagnosis, or care unit.</p>
        </div>
        <label className="field hero-search-field">
          <span>Search patients</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by patient, MRN, diagnosis, or care unit"
          />
        </label>
      </section>

      <section className="panel full-span">
        <div className="panel-header">
          <h3>Roster</h3>
          <span className="subtle-copy">{patients.length} results</span>
        </div>

        <div className="directory-grid">
          {patients.map((patient) => (
            <Link key={patient.patient_id} className="roster-card directory-card" to={`/patients/${patient.patient_id}`}>
              <div>
                <strong>{patient.name}</strong>
                <p className="subtle-copy">
                  {patient.care_unit} | {patient.diagnosis}
                </p>
                <p className="subtle-copy">
                  MRN {patient.mrn} | Age {patient.age} | {patient.sex}
                </p>
              </div>
              <span className="tone tone-low">#{patient.patient_id}</span>
            </Link>
          ))}
          {patients.length === 0 ? <p className="subtle-copy">No patients matched the current search.</p> : null}
        </div>
      </section>
    </div>
  );
};

export default Patients;
