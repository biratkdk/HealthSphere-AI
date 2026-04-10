import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import useSWR from "swr";

import {
  createReportJob,
  downloadImagingStudy,
  getRequestErrorMessage,
  updateImagingStudyReview,
} from "../services/api";

const toneClassName = (tone) => `tone tone-${tone || "low"}`;

const priorityTone = (priority) => {
  if (priority === "urgent") {
    return "critical";
  }
  if (priority === "priority") {
    return "medium";
  }
  return "low";
};

const statusTone = (status) => {
  if (status === "escalated") {
    return "critical";
  }
  if (status === "pending_review") {
    return "medium";
  }
  if (status === "reviewed") {
    return "low";
  }
  return "low";
};

const ImagingWorkbench = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedStudyId, setSelectedStudyId] = useState(searchParams.get("study") || "");
  const [form, setForm] = useState({
    priority: "routine",
    review_notes: "",
    escalation_reason: "",
  });
  const [actionBusy, setActionBusy] = useState("");
  const [actionError, setActionError] = useState("");
  const [reportBusy, setReportBusy] = useState(false);
  const [reportNotice, setReportNotice] = useState("");

  const { data: workbench = null, error, isLoading, mutate } = useSWR(["imagingWorkbench", statusFilter, 30]);

  const selectedItem = useMemo(() => {
    if (!workbench?.items?.length) {
      return null;
    }
    return workbench.items.find((item) => item.study.study_id === selectedStudyId) || workbench.items[0];
  }, [selectedStudyId, workbench]);

  useEffect(() => {
    if (!selectedItem) {
      return;
    }
    if (selectedItem.study.study_id !== selectedStudyId) {
      setSelectedStudyId(selectedItem.study.study_id);
    }
    if (searchParams.get("study") !== selectedItem.study.study_id) {
      setSearchParams({ study: selectedItem.study.study_id });
    }
  }, [searchParams, selectedItem, selectedStudyId, setSearchParams]);

  useEffect(() => {
    if (!selectedItem) {
      return;
    }
    setForm({
      priority: selectedItem.study.priority,
      review_notes: selectedItem.study.review_notes || "",
      escalation_reason: selectedItem.study.escalation_reason || "",
    });
    setActionError("");
    setReportNotice("");
  }, [selectedItem?.study.study_id]);

  const summary = workbench?.summary || {
    total: 0,
    pending_review: 0,
    reviewed: 0,
    escalated: 0,
    signed_off: 0,
    urgent: 0,
    priority: 0,
    overdue: 0,
  };

  const applyReviewStatus = async (reviewStatus) => {
    if (!selectedItem) {
      return;
    }

    try {
      setActionBusy(reviewStatus);
      setActionError("");
      await updateImagingStudyReview(selectedItem.study.study_id, {
        review_status: reviewStatus,
        priority: form.priority,
        review_notes: form.review_notes,
        escalation_reason: reviewStatus === "escalated" ? form.escalation_reason : undefined,
      });
      await mutate();
    } catch (requestError) {
      setActionError(getRequestErrorMessage(requestError, "Unable to update imaging review state."));
    } finally {
      setActionBusy("");
    }
  };

  const queueReport = async () => {
    if (!selectedItem) {
      return;
    }

    try {
      setReportBusy(true);
      setReportNotice("");
      const idempotencyKey =
        typeof window !== "undefined" && window.crypto?.randomUUID
          ? window.crypto.randomUUID()
          : `${selectedItem.study.patient_id}-${Date.now()}`;
      const response = await createReportJob(selectedItem.study.patient_id, idempotencyKey);
      setReportNotice(`Report ${response.job_id.slice(0, 8)} queued for patient ${selectedItem.study.patient_id}.`);
    } catch (requestError) {
      setActionError(getRequestErrorMessage(requestError, "Unable to queue a linked report."));
    } finally {
      setReportBusy(false);
    }
  };

  if (isLoading) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Loading imaging workbench&hellip;</p>
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-grid">
        <section className="panel full-span error-panel">
          <strong className="error-text">Unable to load imaging workbench</strong>
          <p>{getRequestErrorMessage(error, "Please try again.")}</p>
          <button className="secondary-button small-button" type="button" onClick={() => window.location.reload()}>
            Reload
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="page-grid imaging-workbench-grid">
      <section className="hero-panel command-hero">
        <div>
          <p className="eyebrow">Imaging workbench</p>
          <h2>Clinical review lane</h2>
          <p className="subtle-copy">
            Move from uploaded study to reviewed, escalated, or signed-off state while keeping patient context and report
            workflow attached.
          </p>
          <div className="hero-badges">
            <span className={toneClassName(summary.pending_review > 0 ? "medium" : "low")}>
              {summary.pending_review} pending review
            </span>
            <span className={toneClassName(summary.escalated > 0 ? "critical" : "low")}>
              {summary.escalated} escalated
            </span>
            <span className={toneClassName(summary.overdue > 0 ? "critical" : "low")}>{summary.overdue} overdue</span>
          </div>
        </div>

        <div className="hero-actions hero-actions-grid">
          <Link className="secondary-button" to="/population">
            Open population board
          </Link>
          <Link className="secondary-button" to="/reports">
            Open report queue
          </Link>
          <Link className="secondary-button" to="/patients">
            Browse patients
          </Link>
        </div>
      </section>

      <section className="metrics-grid">
        {[
          { label: "Studies in lane", value: summary.total, tone: "low" },
          { label: "Urgent review", value: summary.urgent, tone: summary.urgent > 0 ? "critical" : "low" },
          { label: "Priority review", value: summary.priority, tone: summary.priority > 0 ? "medium" : "low" },
          { label: "Escalated", value: summary.escalated, tone: summary.escalated > 0 ? "critical" : "low" },
          { label: "Signed off", value: summary.signed_off, tone: "low" },
          { label: "Overdue review", value: summary.overdue, tone: summary.overdue > 0 ? "critical" : "low" },
        ].map((metric) => (
          <article key={metric.label} className={`metric-card metric-card-${metric.tone}`}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className="panel full-span">
        <div className="panel-header">
          <h3>Workbench filters</h3>
          <span className="subtle-copy">{summary.total} visible studies</span>
        </div>
        <div className="filter-row population-filter-row">
          {[
            ["all", "All"],
            ["pending_review", "Pending"],
            ["reviewed", "Reviewed"],
            ["escalated", "Escalated"],
            ["signed_off", "Signed off"],
          ].map(([value, label]) => (
            <button
              key={value}
              className={`filter-chip ${statusFilter === value ? "active" : ""}`}
              type="button"
              onClick={() => setStatusFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      <section className="panel panel-span-4">
        <div className="panel-header">
          <h3>Study queue</h3>
          <span className="subtle-copy">{workbench?.items?.length || 0} studies</span>
        </div>

        <div className="queue-list workbench-study-list">
          {workbench?.items?.map((item) => (
            <button
              key={item.study.study_id}
              className={`roster-card workbench-study-card ${selectedItem?.study.study_id === item.study.study_id ? "is-active" : ""}`}
              type="button"
              onClick={() => {
                setSelectedStudyId(item.study.study_id);
                setSearchParams({ study: item.study.study_id });
              }}
            >
              <div>
                <strong>{item.patient_name}</strong>
                <p className="subtle-copy">
                  {item.care_unit} &middot; {item.diagnosis}
                </p>
                <div className="workflow-tag-row">
                  <span className={toneClassName(priorityTone(item.study.priority))}>{item.study.priority}</span>
                  <span className={toneClassName(statusTone(item.study.review_status))}>
                    {item.study.review_status.replaceAll("_", " ")}
                  </span>
                </div>
              </div>
              <div className="queue-meta">
                <span className="subtle-copy">{item.study.review_due_label || "No due time"}</span>
              </div>
            </button>
          ))}
          {!workbench?.items?.length ? <p className="subtle-copy">No studies match the current filter.</p> : null}
        </div>
      </section>

      <section className="panel panel-span-8">
        <div className="panel-header">
          <h3>Study detail</h3>
          <span className="subtle-copy">{selectedItem ? selectedItem.study.study_id : "No selection"}</span>
        </div>

        {selectedItem ? (
          <div className="workbench-detail-grid">
            <article className="analysis-card workbench-analysis-card">
              <div className="workbench-detail-top">
                <div>
                  <strong>{selectedItem.patient_name}</strong>
                  <p className="subtle-copy">
                    {selectedItem.care_unit} &middot; {selectedItem.diagnosis}
                  </p>
                </div>
                <div className="workflow-tag-row">
                  <span className={toneClassName(priorityTone(selectedItem.study.priority))}>{selectedItem.study.priority}</span>
                  <span className={toneClassName(statusTone(selectedItem.study.review_status))}>
                    {selectedItem.study.review_status.replaceAll("_", " ")}
                  </span>
                  <span className={toneClassName(selectedItem.study.is_review_overdue ? "critical" : "low")}>
                    {selectedItem.study.review_due_label || "No due time"}
                  </span>
                </div>
              </div>

              <div className="analysis-metrics">
                <span>{selectedItem.unresolved_alerts} unresolved alerts</span>
                <span>{selectedItem.overdue_tasks} overdue tasks</span>
                {selectedItem.study.analysis ? (
                  <>
                    <span>Confidence {Math.round(selectedItem.study.analysis.confidence * 100)}%</span>
                    <span>Anomaly {Math.round(selectedItem.study.analysis.anomaly_score * 100)}%</span>
                  </>
                ) : null}
              </div>

              <p className="subtle-copy">
                {selectedItem.study.analysis?.result || "Stored study available for review."}
              </p>
              <p className="subtle-copy">
                {selectedItem.next_action || selectedItem.study.analysis?.suggested_next_step || "Review and annotate the study."}
              </p>

              <div className="quick-action-row">
                <Link className="secondary-button" to={`/patients/${selectedItem.study.patient_id}`}>
                  Open mission control
                </Link>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => downloadImagingStudy(selectedItem.study.study_id, selectedItem.study.filename)}
                >
                  Download study
                </button>
              </div>
            </article>

            <article className="analysis-card workbench-form-card">
              <div className="panel-header">
                <h4>Review controls</h4>
                <span className="subtle-copy">Operator actions</span>
              </div>

              <div className="form-grid">
                <label className="field">
                  <span>Priority lane</span>
                  <select
                    value={form.priority}
                    onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value }))}
                  >
                    <option value="routine">Routine</option>
                    <option value="priority">Priority</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </label>
              </div>

              <label className="field">
                <span>Review notes</span>
                <textarea
                  value={form.review_notes}
                  onChange={(event) => setForm((current) => ({ ...current, review_notes: event.target.value }))}
                  placeholder={"What changed?\nWhat did you confirm?\nWhat should happen next?"}
                />
              </label>

              <label className="field">
                <span>Escalation reason</span>
                <textarea
                  value={form.escalation_reason}
                  onChange={(event) => setForm((current) => ({ ...current, escalation_reason: event.target.value }))}
                  placeholder={"Why does this study need escalation?\nWho needs to review it?\nWhat is blocking sign-off?"}
                />
              </label>

              <div className="workflow-actions workbench-actions">
                <button
                  className="secondary-button small-button"
                  type="button"
                  disabled={Boolean(actionBusy)}
                  onClick={() => applyReviewStatus("pending_review")}
                >
                  {actionBusy === "pending_review" ? "Updating..." : "Return to queue"}
                </button>
                <button
                  className="secondary-button small-button"
                  type="button"
                  disabled={Boolean(actionBusy)}
                  onClick={() => applyReviewStatus("reviewed")}
                >
                  {actionBusy === "reviewed" ? "Updating..." : "Mark reviewed"}
                </button>
                <button
                  className="secondary-button small-button"
                  type="button"
                  disabled={Boolean(actionBusy)}
                  onClick={() => applyReviewStatus("escalated")}
                >
                  {actionBusy === "escalated" ? "Updating..." : "Escalate"}
                </button>
                <button
                  className="primary-button accent-button small-button"
                  type="button"
                  disabled={Boolean(actionBusy)}
                  onClick={() => applyReviewStatus("signed_off")}
                >
                  {actionBusy === "signed_off" ? "Updating..." : "Sign off"}
                </button>
              </div>

              <div className="quick-action-row">
                <button className="secondary-button" type="button" disabled={reportBusy} onClick={queueReport}>
                  {reportBusy ? "Queueing..." : "Queue linked report"}
                </button>
              </div>

              {actionError ? <p className="error-text">{actionError}</p> : null}
              {reportNotice ? <p className="success-text">{reportNotice}</p> : null}
            </article>

            <article className="analysis-card workbench-linked-reports">
              <div className="panel-header">
                <h4>Linked reports</h4>
                <Link className="subtle-link" to="/reports">
                  Open reports
                </Link>
              </div>
              <div className="queue-list">
                {selectedItem.linked_reports.map((report) => (
                  <article key={report.job_id} className="queue-row elevated-card">
                    <div>
                      <strong>{report.job_id}</strong>
                      <p className="subtle-copy">{report.workflow_stage.replaceAll("_", " ")}</p>
                    </div>
                    <div className="queue-meta">
                      <span className={toneClassName(report.status === "failed" ? "critical" : report.status === "running" ? "medium" : "low")}>
                        {report.status}
                      </span>
                      <span className="subtle-copy">{report.progress_percent}%</span>
                    </div>
                  </article>
                ))}
                {selectedItem.linked_reports.length === 0 ? (
                  <p className="subtle-copy">No linked report jobs yet. Queue one from this lane if needed.</p>
                ) : null}
              </div>
            </article>
          </div>
        ) : (
          <article className="empty-state-card elevated-card">
            <strong>No study selected</strong>
            <p className="subtle-copy">Choose a study from the queue to review it.</p>
          </article>
        )}
      </section>
    </div>
  );
};

export default ImagingWorkbench;
