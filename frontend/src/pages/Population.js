import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";

import { getRequestErrorMessage } from "../services/api";

const riskClassName = (tone) => {
  const map = {
    critical: "risk-critical",
    high: "risk-high",
    medium: "risk-medium",
    low: "risk-low",
  };
  return `risk-badge ${map[tone] || "risk-low"}`;
};

const toneClassName = (tone) => `tone tone-${tone || "low"}`;

const Population = () => {
  const [unitFilter, setUnitFilter] = useState("all");
  const { data: board = null, error, isLoading } = useSWR(["populationBoard"]);

  const filteredPatients = useMemo(() => {
    if (!board) {
      return [];
    }
    return unitFilter === "all"
      ? board.hottest_patients
      : board.hottest_patients.filter((patient) => patient.care_unit === unitFilter);
  }, [board, unitFilter]);

  const filteredTasks = useMemo(() => {
    if (!board) {
      return [];
    }
    return unitFilter === "all" ? board.overdue_tasks : board.overdue_tasks.filter((task) => task.care_unit === unitFilter);
  }, [board, unitFilter]);

  const filteredAlerts = useMemo(() => {
    if (!board) {
      return [];
    }
    return unitFilter === "all"
      ? board.unresolved_alerts
      : board.unresolved_alerts.filter((alert) => alert.care_unit === unitFilter);
  }, [board, unitFilter]);

  const filteredImaging = useMemo(() => {
    if (!board) {
      return [];
    }
    return unitFilter === "all" ? board.imaging_queue : board.imaging_queue.filter((item) => item.care_unit === unitFilter);
  }, [board, unitFilter]);

  if (isLoading) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Loading population operations board&hellip;</p>
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-grid">
        <section className="panel full-span error-panel">
          <strong className="error-text">Unable to load population board</strong>
          <p>{getRequestErrorMessage(error, "Please try again.")}</p>
          <button className="secondary-button small-button" type="button" onClick={() => window.location.reload()}>
            Reload
          </button>
        </section>
      </div>
    );
  }

  if (!board) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Waiting for command data&hellip;</p>
        </section>
      </div>
    );
  }

  const metrics = [
    { label: "Patients monitored", value: board.totals.total_patients, tone: "low" },
    { label: "High-risk roster", value: board.totals.high_risk_patients, tone: "high" },
    { label: "Unresolved alerts", value: board.totals.unresolved_alerts, tone: board.totals.unresolved_alerts > 0 ? "high" : "low" },
    { label: "Overdue tasks", value: board.totals.overdue_tasks, tone: board.totals.overdue_tasks > 0 ? "critical" : "low" },
    {
      label: "Imaging reviews pending",
      value: board.totals.pending_imaging_reviews,
      tone: board.totals.pending_imaging_reviews > 0 ? "medium" : "low",
    },
    { label: "Reports running", value: board.totals.running_reports, tone: board.totals.running_reports > 0 ? "medium" : "low" },
  ];

  return (
    <div className="page-grid population-grid">
      <section className="hero-panel command-hero population-hero">
        <div>
          <p className="eyebrow">Population operations</p>
          <h2>Care-unit command board</h2>
          <p className="subtle-copy">Track unit pressure, overdue work, alerts, and imaging review from one board.</p>
          <div className="hero-badges">
            <span className="tone tone-low">{board.care_units.length} care units</span>
            <span className={toneClassName(board.totals.overdue_tasks > 0 ? "critical" : "low")}>
              {board.totals.overdue_tasks} overdue tasks
            </span>
            <span className={toneClassName(board.totals.pending_imaging_reviews > 0 ? "medium" : "low")}>
              {board.totals.pending_imaging_reviews} imaging reviews pending
            </span>
          </div>
        </div>

        <div className="hero-actions hero-actions-grid">
          <Link className="primary-button accent-button" to="/imaging">
            Open imaging workbench
          </Link>
          <Link className="secondary-button" to="/reports">
            Open report queue
          </Link>
          <Link className="secondary-button" to="/patients">
            Browse patient directory
          </Link>
        </div>
      </section>

      <section className="metrics-grid">
        {metrics.map((metric) => (
          <article key={metric.label} className={`metric-card metric-card-${metric.tone}`}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className="panel panel-span-4">
        <div className="panel-header">
          <h3>Care-unit pressure</h3>
          <span className="subtle-copy">{board.care_units.length} active lanes</span>
        </div>

        <div className="filter-row population-filter-row">
          <button
            className={`filter-chip ${unitFilter === "all" ? "active" : ""}`}
            type="button"
            onClick={() => setUnitFilter("all")}
          >
            All units
            <span className="filter-chip-count">{board.totals.total_patients}</span>
          </button>
          {board.care_units.map((unit) => (
            <button
              key={unit.care_unit}
              className={`filter-chip ${unitFilter === unit.care_unit ? "active" : ""}`}
              type="button"
              onClick={() => setUnitFilter(unit.care_unit)}
            >
              {unit.care_unit}
              <span className="filter-chip-count">{unit.patient_count}</span>
            </button>
          ))}
        </div>

        <div className="care-unit-grid population-unit-grid">
          {board.care_units.map((unit) => (
            <article key={unit.care_unit} className="care-unit-card elevated-card">
              <span>{unit.care_unit}</span>
              <strong>{unit.patient_count} patients</strong>
              <div className="workflow-tag-row">
                <span className={toneClassName(unit.high_risk_patients > 0 ? "high" : "low")}>
                  {unit.high_risk_patients} high-risk
                </span>
                <span className={toneClassName(unit.unresolved_alerts > 0 ? "high" : "low")}>
                  {unit.unresolved_alerts} alerts
                </span>
                <span className={toneClassName(unit.overdue_tasks > 0 ? "critical" : "low")}>
                  {unit.overdue_tasks} overdue
                </span>
                <span className={toneClassName(unit.pending_imaging_reviews > 0 ? "medium" : "low")}>
                  {unit.pending_imaging_reviews} imaging
                </span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel panel-span-8">
        <div className="panel-header">
          <h3>Hottest patients</h3>
          <span className="subtle-copy">{filteredPatients.length} patients in focus</span>
        </div>

        <div className="population-command-list">
          {filteredPatients.map((patient) => (
            <Link key={patient.patient_id} className="population-patient-card elevated-card" to={`/patients/${patient.patient_id}`}>
              <div className="population-card-header">
                <div>
                  <strong>{patient.name}</strong>
                  <p className="subtle-copy">
                    {patient.care_unit} &middot; {patient.diagnosis}
                  </p>
                </div>
                <span className={riskClassName(patient.priority_tone)}>{patient.priority_tone}</span>
              </div>

              <div className="workflow-tag-row">
                <span className="tone tone-low">ICU {Math.round(patient.icu_risk * 100)}%</span>
                <span className={toneClassName(patient.unresolved_alerts > 0 ? "high" : "low")}>
                  {patient.unresolved_alerts} alerts
                </span>
                <span className={toneClassName(patient.overdue_tasks > 0 ? "critical" : "low")}>
                  {patient.overdue_tasks} overdue
                </span>
                <span className={toneClassName(patient.pending_imaging_reviews > 0 ? "medium" : "low")}>
                  {patient.pending_imaging_reviews} imaging
                </span>
              </div>

              <p className="subtle-copy population-primary-signal">{patient.primary_signal}</p>
              {patient.next_action ? (
                <div className="population-next-action">
                  <span className="population-meta-label">Next action</span>
                  <strong>{patient.next_action}</strong>
                </div>
              ) : null}
            </Link>
          ))}
          {filteredPatients.length === 0 ? (
            <article className="empty-state-card elevated-card">
              <strong>No patients match the current unit filter</strong>
              <p className="subtle-copy">Switch units to review a different care lane.</p>
            </article>
          ) : null}
        </div>
      </section>

      <section className="panel panel-span-6">
        <div className="panel-header">
          <h3>Overdue workflow board</h3>
          <span className="subtle-copy">{filteredTasks.length} tasks</span>
        </div>

        <div className="queue-list">
          {filteredTasks.map((task) => (
            <article key={task.task_id} className="queue-row workflow-task-row workflow-task-overdue">
              <div className="workflow-task-copy">
                <strong>{task.title}</strong>
                <p className="subtle-copy">
                  {task.patient_name} &middot; {task.care_unit}
                </p>
              </div>
              <div className="queue-meta">
                <span className={toneClassName(task.priority)}>{task.priority}</span>
                <span className="tone tone-critical">{task.due_label}</span>
                <span className="subtle-copy">{task.assignee_username || "Unassigned"}</span>
              </div>
            </article>
          ))}
          {filteredTasks.length === 0 ? <p className="subtle-copy">No overdue tasks in the selected lane.</p> : null}
        </div>
      </section>

      <section className="panel panel-span-6">
        <div className="panel-header">
          <h3>Unresolved alert board</h3>
          <span className="subtle-copy">{filteredAlerts.length} alerts</span>
        </div>

        <div className="queue-list">
          {filteredAlerts.map((alert) => (
            <article key={alert.alert_id} className="queue-row elevated-card">
              <div>
                <strong>{alert.title}</strong>
                <p className="subtle-copy">
                  {alert.patient_name} &middot; {alert.care_unit}
                </p>
                <p className="subtle-copy">{alert.description}</p>
              </div>
              <div className="queue-meta">
                <span className={toneClassName(alert.severity)}>{alert.severity}</span>
                <span className="subtle-copy">{new Date(alert.created_at).toLocaleString()}</span>
              </div>
            </article>
          ))}
          {filteredAlerts.length === 0 ? <p className="subtle-copy">No unresolved alerts in the selected lane.</p> : null}
        </div>
      </section>

      <section className="panel full-span">
        <div className="panel-header">
          <h3>Imaging review pressure</h3>
          <Link className="subtle-link" to="/imaging">
            Open workbench
          </Link>
        </div>

        <div className="queue-list">
          {filteredImaging.map((item) => (
            <Link key={item.study_id} className="queue-row elevated-card" to={`/imaging?study=${item.study_id}`}>
              <div>
                <strong>{item.patient_name}</strong>
                <p className="subtle-copy">
                  {item.care_unit} &middot; study {item.study_id.slice(0, 8)}
                </p>
                <p className="subtle-copy">{item.suggested_next_step || "Review the study in the imaging lane."}</p>
              </div>
              <div className="queue-meta">
                <span className={toneClassName(item.priority === "urgent" ? "critical" : item.priority === "priority" ? "medium" : "low")}>
                  {item.priority}
                </span>
                <span className={toneClassName(item.review_status === "escalated" ? "critical" : item.review_status === "pending_review" ? "medium" : "low")}>
                  {item.review_status.replaceAll("_", " ")}
                </span>
                <span className="subtle-copy">{item.review_due_label || "No due time"}</span>
              </div>
            </Link>
          ))}
          {filteredImaging.length === 0 ? <p className="subtle-copy">No imaging review items in the selected lane.</p> : null}
        </div>
      </section>
    </div>
  );
};

export default Population;
