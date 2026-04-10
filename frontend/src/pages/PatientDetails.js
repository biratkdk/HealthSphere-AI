import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import useSWR from "swr";

import ImagingResults from "../components/ImagingResults";
import PatientVitals from "../components/PatientVitals";
import {
  acknowledgeAlert,
  createPatientHandoff,
  createPatientTask,
  downloadImagingStudy,
  getRequestErrorMessage,
  updatePatientTask,
} from "../services/api";

const TASK_STATUS_LABELS = {
  open: "Open",
  in_progress: "In progress",
  blocked: "Blocked",
  completed: "Completed",
};

const splitStructuredLines = (value) =>
  value
    .split("\n")
    .map((entry) => entry.trim())
    .filter(Boolean);

const serializeHandoffDetails = (form) => {
  const sections = [];
  const whatChanged = splitStructuredLines(form.what_changed);
  const pendingItems = splitStructuredLines(form.pending_items);
  const watchItems = splitStructuredLines(form.watch_items);

  if (whatChanged.length) {
    sections.push("What changed");
    whatChanged.forEach((entry) => sections.push(`- ${entry}`));
  }
  if (pendingItems.length) {
    sections.push("Pending");
    pendingItems.forEach((entry) => sections.push(`- ${entry}`));
  }
  if (watchItems.length) {
    sections.push("Watch");
    watchItems.forEach((entry) => sections.push(`- ${entry}`));
  }

  return sections.join("\n");
};

const toIsoDateTime = (value) => {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toISOString();
};

const formatDateTime = (value) => {
  if (!value) {
    return "No timestamp";
  }
  return new Date(value).toLocaleString();
};

const formatRiskPercent = (value) => `${Math.round((value || 0) * 100)}%`;

const toneClassForValue = (value) => `tone tone-${value || "low"}`;

const workflowStatItems = (workflow = {}) => [
  { label: "Open", value: workflow.open_tasks ?? 0, tone: "low" },
  { label: "In progress", value: workflow.in_progress_tasks ?? 0, tone: "medium" },
  { label: "Blocked", value: workflow.blocked_tasks ?? 0, tone: "high" },
  { label: "Overdue", value: workflow.overdue_tasks ?? 0, tone: "critical" },
  { label: "Due soon", value: workflow.due_soon_tasks ?? 0, tone: "medium" },
  { label: "Unassigned", value: workflow.unassigned_tasks ?? 0, tone: "high" },
];

const TaskWorkflowActions = ({ task, onUpdate, busy }) => {
  if (task.status === "completed") {
    return <span className="tone tone-low">Completed</span>;
  }

  return (
    <div className="workflow-actions">
      {task.status === "open" ? (
        <button className="secondary-button small-button" type="button" onClick={() => onUpdate(task.task_id, { status: "in_progress" })} disabled={busy}>
          Start
        </button>
      ) : null}
      {task.status === "blocked" ? (
        <button className="secondary-button small-button" type="button" onClick={() => onUpdate(task.task_id, { status: "in_progress" })} disabled={busy}>
          Resume
        </button>
      ) : null}
      {task.status !== "blocked" ? (
        <button className="secondary-button small-button" type="button" onClick={() => onUpdate(task.task_id, { status: "blocked" })} disabled={busy}>
          Block
        </button>
      ) : null}
      <button className="secondary-button small-button" type="button" onClick={() => onUpdate(task.task_id, { status: "completed" })} disabled={busy}>
        Complete
      </button>
    </div>
  );
};

const StructuredHandoffSection = ({ title, items }) => {
  if (!items?.length) {
    return null;
  }

  return (
    <div className="handoff-section">
      <span>{title}</span>
      <ul className="action-list compact">
        {items.map((item) => (
          <li key={`${title}-${item}`}>{item}</li>
        ))}
      </ul>
    </div>
  );
};

const PatientDetails = () => {
  const { patientId } = useParams();
  const [taskForm, setTaskForm] = useState({
    title: "",
    detail: "",
    priority: "medium",
    assignee_username: "",
    due_at: "",
  });
  const [handoffForm, setHandoffForm] = useState({
    summary: "",
    what_changed: "",
    pending_items: "",
    watch_items: "",
  });
  const [actionError, setActionError] = useState("");
  const [taskBusy, setTaskBusy] = useState(false);
  const [handoffBusy, setHandoffBusy] = useState(false);
  const [taskActionId, setTaskActionId] = useState("");
  const [ackBusy, setAckBusy] = useState("");
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

  const refreshPatientContext = async () => {
    await Promise.all([mutateSummary(), mutateTimeline()]);
  };

  if (summaryLoading || studiesLoading || timelineLoading) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Loading patient workspace&hellip;</p>
        </section>
      </div>
    );
  }

  const error =
    getRequestErrorMessage(summaryError, "") ||
    getRequestErrorMessage(studiesError, "") ||
    getRequestErrorMessage(timelineError, "") ||
    "";
  if (error) {
    return (
      <div className="page-grid">
        <section className="panel full-span error-panel">
          <strong className="error-text">Unable to load patient detail</strong>
          <p>{error}</p>
          <button className="secondary-button small-button" type="button" onClick={() => window.location.reload()}>
            Reload
          </button>
        </section>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Waiting for patient data&hellip;</p>
        </section>
      </div>
    );
  }

  const missionControl = summary.mission_control || {
    changed: [],
    why_now: [],
    next_actions: [],
    workflow: {},
  };
  const workflowStats = workflowStatItems(missionControl.workflow);

  const submitTask = async (event) => {
    event.preventDefault();
    setActionError("");
    try {
      setTaskBusy(true);
      await createPatientTask(summary.patient.patient_id, {
        title: taskForm.title,
        detail: taskForm.detail,
        priority: taskForm.priority,
        assignee_username: taskForm.assignee_username.trim() || null,
        due_at: toIsoDateTime(taskForm.due_at),
      });
      await refreshPatientContext();
      setTaskForm({
        title: "",
        detail: "",
        priority: "medium",
        assignee_username: "",
        due_at: "",
      });
    } catch (requestError) {
      setActionError(getRequestErrorMessage(requestError, "Unable to create the care task."));
    } finally {
      setTaskBusy(false);
    }
  };

  const updateTaskWorkflow = async (taskId, payload) => {
    setActionError("");
    try {
      setTaskActionId(taskId);
      await updatePatientTask(summary.patient.patient_id, taskId, payload);
      await refreshPatientContext();
    } catch (requestError) {
      setActionError(getRequestErrorMessage(requestError, "Unable to update the care task."));
    } finally {
      setTaskActionId("");
    }
  };

  const handleAcknowledgeAlert = async (alertId) => {
    setActionError("");
    try {
      setAckBusy(alertId);
      await acknowledgeAlert(alertId);
      await mutateSummary();
    } catch (requestError) {
      setActionError(getRequestErrorMessage(requestError, "Unable to acknowledge the alert."));
    } finally {
      setAckBusy("");
    }
  };

  const submitHandoff = async (event) => {
    event.preventDefault();
    setActionError("");
    const details = serializeHandoffDetails(handoffForm);
    if (!details) {
      setActionError("Add at least one structured handoff detail before saving.");
      return;
    }
    try {
      setHandoffBusy(true);
      await createPatientHandoff(summary.patient.patient_id, {
        summary: handoffForm.summary,
        details,
      });
      await refreshPatientContext();
      setHandoffForm({
        summary: "",
        what_changed: "",
        pending_items: "",
        watch_items: "",
      });
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

      <section className="panel full-span mission-control-panel">
        <div className="mission-control-head">
          <div>
            <p className="eyebrow">Patient Mission Control</p>
            <h3>What changed, why it matters, and what to do next</h3>
            <p className="subtle-copy">
              ICU risk {formatRiskPercent(summary.icu_risk.icu_risk)} | Disease watch {formatRiskPercent(summary.disease_risk.sepsis_watch_risk)} | Last updated{" "}
              {formatDateTime(summary.patient.last_updated)}
            </p>
          </div>
          <div className="mission-control-meta">
            <span className={toneClassForValue(summary.icu_risk.risk_band)}>{summary.icu_risk.risk_band} ICU pressure</span>
            <span className={toneClassForValue(summary.treatment.priority)}>{summary.treatment.priority} treatment priority</span>
          </div>
        </div>

        <div className="workflow-stat-grid">
          {workflowStats.map((item) => (
            <article key={item.label} className={`workflow-stat-card workflow-stat-${item.tone}`}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </article>
          ))}
          <article className="workflow-stat-card workflow-stat-low">
            <span>Last handoff</span>
            <strong>{missionControl.workflow?.last_handoff_summary || "Not recorded"}</strong>
            <p className="subtle-copy">
              {missionControl.workflow?.handoff_age_minutes != null
                ? `${missionControl.workflow.handoff_age_minutes}m ago`
                : "Add a structured handoff for the next team."}
            </p>
          </article>
        </div>

        <div className="mission-control-grid">
          <section className="mission-column">
            <div className="panel-header">
              <h4>What changed</h4>
              <span className="subtle-copy">{missionControl.changed?.length || 0} live signals</span>
            </div>
            <div className="mission-card-list">
              {(missionControl.changed || []).map((item) => (
                <article key={`${item.source}-${item.title}`} className={`mission-card mission-card-${item.tone}`}>
                  <span className="mission-card-tag">{item.source}</span>
                  <strong>{item.title}</strong>
                  <p className="subtle-copy">{item.detail}</p>
                </article>
              ))}
              {!missionControl.changed?.length ? <p className="subtle-copy">No significant deltas are available yet.</p> : null}
            </div>
          </section>

          <section className="mission-column">
            <div className="panel-header">
              <h4>Why now</h4>
              <span className="subtle-copy">Priority context</span>
            </div>
            <div className="mission-card-list">
              {(missionControl.why_now || []).map((item) => (
                <article key={`${item.source}-${item.title}`} className={`mission-card mission-card-${item.tone}`}>
                  <span className="mission-card-tag">{item.source}</span>
                  <strong>{item.title}</strong>
                  <p className="subtle-copy">{item.detail}</p>
                </article>
              ))}
              {!missionControl.why_now?.length ? <p className="subtle-copy">No risk drivers are available yet.</p> : null}
            </div>
          </section>

          <section className="mission-column">
            <div className="panel-header">
              <h4>Next actions</h4>
              <span className="subtle-copy">{missionControl.next_actions?.length || 0} recommended moves</span>
            </div>
            <div className="mission-card-list">
              {(missionControl.next_actions || []).map((item) => (
                <article key={`${item.linked_task_id || item.title}-${item.detail}`} className={`mission-card mission-card-${item.priority}`}>
                  <span className="mission-card-tag">{item.priority}</span>
                  <strong>{item.title}</strong>
                  <p className="subtle-copy">{item.detail}</p>
                  <div className="mission-action-meta">
                    {item.owner_hint ? <span>{item.owner_hint}</span> : null}
                    {item.due_hint ? <span>{item.due_hint}</span> : null}
                  </div>
                </article>
              ))}
              {!missionControl.next_actions?.length ? <p className="subtle-copy">No recommended next actions are available yet.</p> : null}
            </div>
          </section>
        </div>
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
          <h3>Active treatment brief</h3>
          <span className={toneClassForValue(summary.treatment.priority)}>{summary.treatment.priority}</span>
        </div>
        <p className="subtle-copy">{summary.treatment.rationale}</p>
        <ul className="action-list compact">
          {summary.treatment.actions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
      </section>

      <section className="panel panel-span-7">
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
          <div className="mission-form-grid">
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
            <label className="field">
              <span>Owner</span>
              <input
                value={taskForm.assignee_username}
                onChange={(event) => setTaskForm((current) => ({ ...current, assignee_username: event.target.value }))}
                placeholder="clinician"
              />
            </label>
            <label className="field">
              <span>Due time</span>
              <input
                type="datetime-local"
                value={taskForm.due_at}
                onChange={(event) => setTaskForm((current) => ({ ...current, due_at: event.target.value }))}
              />
            </label>
          </div>
          <div className="form-actions">
            <p className="subtle-copy">Set ownership and a due time so the SLA engine can track execution risk.</p>
            <button className="primary-button accent-button" type="submit" disabled={taskBusy}>
              {taskBusy ? "Saving..." : "Add task"}
            </button>
          </div>
        </form>

        <div className="queue-list compact-list">
          {(summary.tasks || []).map((task) => (
            <article key={task.task_id} className={`queue-row workflow-task-row workflow-task-${task.sla_status}`}>
              <div className="workflow-task-copy">
                <div className="workflow-task-top">
                  <strong>{task.title}</strong>
                  <div className="workflow-tag-row">
                    <span className={toneClassForValue(task.priority)}>{task.priority}</span>
                    <span className={toneClassForValue(task.is_overdue ? "critical" : task.status === "blocked" ? "high" : "low")}>
                      {TASK_STATUS_LABELS[task.status] || task.status}
                    </span>
                    <span className={toneClassForValue(task.is_overdue ? "critical" : task.is_due_soon ? "medium" : "low")}>
                      {task.due_label || "No due time"}
                    </span>
                  </div>
                </div>
                <p className="subtle-copy">{task.detail}</p>
                <div className="workflow-task-meta">
                  <span>{task.assignee_username ? `Owner: ${task.assignee_username}` : "Owner: unassigned"}</span>
                  <span>Created by {task.created_by}</span>
                  <span>{task.age_minutes}m in queue</span>
                </div>
              </div>
              <TaskWorkflowActions task={task} onUpdate={updateTaskWorkflow} busy={taskActionId === task.task_id} />
            </article>
          ))}
          {!summary.tasks?.length ? <p className="subtle-copy">No care tasks are logged yet.</p> : null}
        </div>
      </section>

      <section className="panel panel-span-5">
        <div className="panel-header">
          <h3>Shift handoff</h3>
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
          <div className="mission-form-grid">
            <label className="field">
              <span>What changed</span>
              <textarea
                rows={3}
                value={handoffForm.what_changed}
                onChange={(event) => setHandoffForm((current) => ({ ...current, what_changed: event.target.value }))}
                placeholder={"One item per line\nOxygen requirement increased to 4L\nRepeat lactate ordered"}
              />
            </label>
            <label className="field">
              <span>Pending items</span>
              <textarea
                rows={3}
                value={handoffForm.pending_items}
                onChange={(event) => setHandoffForm((current) => ({ ...current, pending_items: event.target.value }))}
                placeholder={"One item per line\nReview repeat labs\nConfirm report release"}
              />
            </label>
            <label className="field">
              <span>Watch items</span>
              <textarea
                rows={3}
                value={handoffForm.watch_items}
                onChange={(event) => setHandoffForm((current) => ({ ...current, watch_items: event.target.value }))}
                placeholder={"One item per line\nEscalate if MAP < 65\nMonitor respiratory effort"}
              />
            </label>
          </div>
          <div className="form-actions">
            <p className="subtle-copy">Structured handoffs feed the mission-control summary and reduce shift-to-shift context loss.</p>
            <button className="primary-button accent-button" type="submit" disabled={handoffBusy}>
              {handoffBusy ? "Saving..." : "Add handoff"}
            </button>
          </div>
        </form>

        <div className="queue-list compact-list">
          {(summary.recent_handoffs || []).map((note) => (
            <article key={note.note_id} className="queue-row workflow-handoff-row">
              <div className="workflow-task-copy">
                <div className="workflow-task-top">
                  <strong>{note.summary}</strong>
                  <span className="tone tone-low">{note.freshness_minutes}m ago</span>
                </div>
                <p className="subtle-copy">
                  {note.author_username} | {formatDateTime(note.created_at)}
                </p>
                <div className="handoff-section-grid">
                  <StructuredHandoffSection title="What changed" items={note.what_changed} />
                  <StructuredHandoffSection title="Pending" items={note.pending_items} />
                  <StructuredHandoffSection title="Watch" items={note.watch_items} />
                </div>
                {!note.what_changed?.length && !note.pending_items?.length && !note.watch_items?.length ? (
                  <p className="subtle-copy">{note.details}</p>
                ) : null}
              </div>
            </article>
          ))}
          {!summary.recent_handoffs?.length ? <p className="subtle-copy">No handoff notes are available yet.</p> : null}
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
                <p className="subtle-copy">{formatDateTime(study.created_at)}</p>
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

      <section className="panel panel-span-4">
        <div className="panel-header">
          <h3>Open alerts</h3>
          <span className="subtle-copy">{summary.open_alerts?.length || 0} active signals</span>
        </div>
        <div className="queue-list compact-list">
          {(summary.open_alerts || []).map((alert) => (
            <article key={alert.alert_id} className={`queue-row severity-${alert.severity}`}>
              <div className="workflow-task-copy">
                <div className="workflow-task-top">
                  <strong>{alert.title}</strong>
                  <span className={toneClassForValue(alert.severity)}>{alert.severity}</span>
                </div>
                <p className="subtle-copy">{alert.description}</p>
                <p className="subtle-copy">{formatDateTime(alert.created_at)}</p>
              </div>
              {!alert.acknowledged ? (
                <button
                  className="secondary-button small-button"
                  type="button"
                  disabled={ackBusy === alert.alert_id}
                  onClick={() => handleAcknowledgeAlert(alert.alert_id)}
                >
                  {ackBusy === alert.alert_id ? "..." : "Acknowledge"}
                </button>
              ) : (
                <span className="tone tone-low">Acknowledged</span>
              )}
            </article>
          ))}
          {!summary.open_alerts?.length ? <p className="subtle-copy">No open alerts are active for this patient.</p> : null}
        </div>
      </section>

      <section className="panel full-span">
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
                  {event.category} | {formatDateTime(event.created_at)}
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
