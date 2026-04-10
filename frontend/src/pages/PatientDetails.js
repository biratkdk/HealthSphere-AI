import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import useSWR from "swr";

import ImagingResults from "../components/ImagingResults";
import PatientVitals from "../components/PatientVitals";
import {
  createPatientHandoff,
  createPatientTask,
  downloadImagingStudy,
  getRequestErrorMessage,
  updatePatientTask,
} from "../services/api";

const PatientDetails = () => {
  const { patientId } = useParams();
  const [taskForm, setTaskForm] = useState({ title: "", detail: "", priority: "medium" });
  const [handoffForm, setHandoffForm] = useState({ summary: "", details: "" });
  const [actionError, setActionError] = useState("");
  const [taskBusy, setTaskBusy] = useState(false);
  const [handoffBusy, setHandoffBusy] = useState(false);
  const {
    data: summary = null,
    error: summaryError,
    isLoading: summaryLoading,
    mutate: mutateSummary,
  } = useSWR(patientId ? ["patientSummary", patientId] : null);
  const {
    data: studies = [],
    error: studiesError,
    isLoading: studiesLoading,
  } = useSWR(patientId ? ["patientImaging", patientId, 6] : null);
  const {
    data: timeline = [],
    error: timelineError,
    isLoading: timelineLoading,
    mutate: mutateTimeline,
  } = useSWR(patientId ? ["patientTimeline", patientId, 30] : null);

  if (summaryLoading || studiesLoading || timelineLoading) {
    return <section className="panel">Loading patient detail...</section>;
  }

  const error =
    getRequestErrorMessage(summaryError, "") ||
    getRequestErrorMessage(studiesError, "") ||
    getRequestErrorMessage(timelineError, "") ||
    "";
  if (error) {
    return <section className="panel error-panel">{error}</section>;
  }

  if (!summary) {
    return <section className="panel">No patient detail available.</section>;
  }

  const submitTask = async (event) => {
    event.preventDefault();
    setActionError("");
    try {
      setTaskBusy(true);
      const created = await createPatientTask(summary.patient.patient_id, taskForm);
      mutateSummary(
        (current) =>
          current
            ? {
                ...current,
                tasks: [created, ...(current.tasks || [])],
              }
            : current,
        false
      );
      mutateTimeline();
      setTaskForm({ title: "", detail: "", priority: "medium" });
    } catch (requestError) {
      setActionError(getRequestErrorMessage(requestError, "Unable to create the care task."));
    } finally {
      setTaskBusy(false);
    }
  };

  const markTaskComplete = async (taskId) => {
    setActionError("");
    try {
      const updated = await updatePatientTask(summary.patient.patient_id, taskId, { status: "completed" });
      mutateSummary(
        (current) =>
          current
            ? {
                ...current,
                tasks: current.tasks.map((task) => (task.task_id === updated.task_id ? updated : task)),
              }
            : current,
        false
      );
      mutateTimeline();
    } catch (requestError) {
      setActionError(getRequestErrorMessage(requestError, "Unable to update the care task."));
    }
  };

  const submitHandoff = async (event) => {
    event.preventDefault();
    setActionError("");
    try {
      setHandoffBusy(true);
      const created = await createPatientHandoff(summary.patient.patient_id, handoffForm);
      mutateSummary(
        (current) =>
          current
            ? {
                ...current,
                recent_handoffs: [created, ...(current.recent_handoffs || [])].slice(0, 6),
              }
            : current,
        false
      );
      mutateTimeline();
      setHandoffForm({ summary: "", details: "" });
    } catch (requestError) {
      setActionError(getRequestErrorMessage(requestError, "Unable to save the handoff note."));
    } finally {
      setHandoffBusy(false);
    }
  };

  return (
    <div className="page-grid">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Patient detail</p>
          <h2>{summary.patient.name}</h2>
          <p className="subtle-copy">
            {summary.patient.sex} | {summary.patient.age} years | {summary.patient.care_unit}
          </p>
        </div>
        <Link className="secondary-button" to="/">
          Back to operations
        </Link>
      </section>

      <PatientVitals summary={summary} />

      <section className="panel panel-span-4">
        <div className="panel-header">
          <h3>Medication profile</h3>
          <span className="subtle-copy">{summary.patient.medications.length} active items</span>
        </div>
        <ul className="action-list compact">
          {summary.patient.medications.map((medication) => (
            <li key={medication}>{medication}</li>
          ))}
        </ul>
      </section>

      <section className="panel panel-span-4">
        <div className="panel-header">
          <h3>Care flags</h3>
          <span className="subtle-copy">{summary.patient.risk_flags.length} active flags</span>
        </div>
        <ul className="action-list compact">
          {summary.patient.risk_flags.map((flag) => (
            <li key={flag}>{flag}</li>
          ))}
        </ul>
      </section>

      <section className="panel panel-span-4">
        <div className="panel-header">
          <h3>Care tasks</h3>
          <span className="subtle-copy">{summary.tasks?.length || 0} tracked items</span>
        </div>

        <form className="task-form" onSubmit={submitTask}>
          <label className="field">
            <span>Task title</span>
            <input
              value={taskForm.title}
              onChange={(event) => setTaskForm((current) => ({ ...current, title: event.target.value }))}
              placeholder="Arrange repeat labs"
              required
            />
          </label>
          <label className="field">
            <span>Task detail</span>
            <textarea
              rows={3}
              value={taskForm.detail}
              onChange={(event) => setTaskForm((current) => ({ ...current, detail: event.target.value }))}
              placeholder="Capture the next care action for the assigned team."
              required
            />
          </label>
          <div className="task-form-row">
            <label className="field">
              <span>Priority</span>
              <select
                value={taskForm.priority}
                onChange={(event) => setTaskForm((current) => ({ ...current, priority: event.target.value }))}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </label>
            <button className="primary-button accent-button" type="submit" disabled={taskBusy}>
              {taskBusy ? "Saving..." : "Add task"}
            </button>
          </div>
        </form>

        <div className="queue-list compact-list">
          {(summary.tasks || []).map((task) => (
            <article key={task.task_id} className="queue-row">
              <div>
                <strong>{task.title}</strong>
                <p className="subtle-copy">
                  {task.priority} | {task.status.replaceAll("_", " ")}
                </p>
                <p className="subtle-copy">{task.detail}</p>
              </div>
              {task.status !== "completed" ? (
                <button className="secondary-button small-button" type="button" onClick={() => markTaskComplete(task.task_id)}>
                  Complete
                </button>
              ) : (
                <span className="tone tone-low">completed</span>
              )}
            </article>
          ))}
          {!summary.tasks?.length ? <p className="subtle-copy">No care tasks are logged yet.</p> : null}
        </div>
      </section>

      <section className="panel panel-span-8">
        <div className="panel-header">
          <h3>Recent imaging studies</h3>
          <span className="subtle-copy">{studies.length} stored items</span>
        </div>
        <div className="queue-list">
          {studies.map((study) => (
            <article key={study.study_id} className="queue-row">
              <div>
                <strong>{study.filename}</strong>
                <p className="subtle-copy">{new Date(study.created_at).toLocaleString()}</p>
              </div>
              <div className="queue-meta">
                <span>{study.analysis?.result || "Stored study"}</span>
                <button
                  className="secondary-button small-button"
                  type="button"
                  onClick={() => downloadImagingStudy(study.study_id, study.filename)}
                >
                  Download
                </button>
              </div>
            </article>
          ))}
          {studies.length === 0 ? <p className="subtle-copy">No stored imaging studies are available yet.</p> : null}
        </div>
      </section>

      <section className="panel panel-span-5">
        <div className="panel-header">
          <h3>Handoff notes</h3>
          <span className="subtle-copy">{summary.recent_handoffs?.length || 0} recent updates</span>
        </div>

        <form className="task-form" onSubmit={submitHandoff}>
          <label className="field">
            <span>Summary</span>
            <input
              value={handoffForm.summary}
              onChange={(event) => setHandoffForm((current) => ({ ...current, summary: event.target.value }))}
              placeholder="Escalation complete"
              required
            />
          </label>
          <label className="field">
            <span>Details</span>
            <textarea
              rows={4}
              value={handoffForm.details}
              onChange={(event) => setHandoffForm((current) => ({ ...current, details: event.target.value }))}
              placeholder="Capture what changed, what is pending, and what the next team should watch."
              required
            />
          </label>
          <button className="primary-button accent-button" type="submit" disabled={handoffBusy}>
            {handoffBusy ? "Saving..." : "Add handoff"}
          </button>
        </form>

        <div className="queue-list compact-list">
          {(summary.recent_handoffs || []).map((note) => (
            <article key={note.note_id} className="queue-row">
              <div>
                <strong>{note.summary}</strong>
                <p className="subtle-copy">
                  {note.author_username} | {new Date(note.created_at).toLocaleString()}
                </p>
                <p className="subtle-copy">{note.details}</p>
              </div>
            </article>
          ))}
          {!summary.recent_handoffs?.length ? <p className="subtle-copy">No handoff notes are available yet.</p> : null}
        </div>
      </section>

      <section className="panel panel-span-7">
        <div className="panel-header">
          <h3>Patient timeline</h3>
          <span className="subtle-copy">{timeline.length} recent events</span>
        </div>

        <div className="timeline-list">
          {timeline.map((event) => (
            <article key={event.event_id} className="timeline-row">
              <div className={`timeline-marker timeline-${event.category}`} />
              <div>
                <strong>{event.label}</strong>
                <p className="subtle-copy">
                  {event.category} | {new Date(event.created_at).toLocaleString()}
                </p>
                <p className="subtle-copy">{event.summary}</p>
              </div>
            </article>
          ))}
          {timeline.length === 0 ? <p className="subtle-copy">No timeline events are available for this patient yet.</p> : null}
        </div>
      </section>

      {actionError ? <section className="panel error-panel full-span">{actionError}</section> : null}

      <ImagingResults patientId={summary.patient.patient_id} />
    </div>
  );
};

export default PatientDetails;
