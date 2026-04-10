import React, { useEffect, useMemo, useState } from "react";
import useSWR from "swr";

import { useAuth } from "../context/AuthContext";
import { useOperationsStream } from "../hooks/useOperationsStream";
import { createReportJob, downloadReportArtifact, getRequestErrorMessage } from "../services/api";

const toneClassName = (tone) => `tone tone-${tone || "low"}`;

const Reports = () => {
  const { user } = useAuth();
  const [selectedPatientId, setSelectedPatientId] = useState(1001);
  const [activeJobId, setActiveJobId] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const {
    snapshot,
    connected: liveFeedConnected,
    lastEventAt,
    error: liveFeedError,
  } = useOperationsStream(Boolean(user));

  const {
    data: patients = [],
    error: patientsError,
    isLoading: patientsLoading,
  } = useSWR(user ? ["patients"] : null);

  const {
    data: queue = [],
    error: queueError,
    isLoading: queueLoading,
    mutate: mutateQueue,
  } = useSWR(user ? ["reportJobs", 20] : null, {
    refreshInterval: liveFeedConnected ? 0 : 6000,
  });

  useEffect(() => {
    if (!patients.length) {
      return;
    }
    if (!patients.some((patient) => patient.patient_id === selectedPatientId)) {
      setSelectedPatientId(patients[0].patient_id);
    }
  }, [patients, selectedPatientId]);

  const {
    data: job = null,
    error: jobError,
    mutate: mutateJob,
  } = useSWR(user && activeJobId ? ["reportJob", activeJobId] : null, {
    refreshInterval: liveFeedConnected ? 0 : activeJobId ? 4000 : 0,
  });

  useEffect(() => {
    if (!snapshot?.active_jobs) {
      return;
    }

    mutateQueue(snapshot.active_jobs, false);

    if (!activeJobId) {
      return;
    }

    const matchingJob = snapshot.active_jobs.find((item) => item.job_id === activeJobId);
    if (matchingJob) {
      mutateJob(matchingJob, false);
    }
  }, [activeJobId, mutateJob, mutateQueue, snapshot]);

  const selectedPatient = useMemo(
    () => patients.find((patient) => patient.patient_id === selectedPatientId) || null,
    [patients, selectedPatientId]
  );

  const currentJob = job || queue.find((item) => item.job_id === activeJobId) || null;

  const queueSummary = useMemo(
    () =>
      queue.reduce(
        (summary, item) => {
          summary[item.status] = (summary[item.status] || 0) + 1;
          return summary;
        },
        { queued: 0, running: 0, completed: 0, failed: 0 }
      ),
    [queue]
  );

  const reportMetrics = useMemo(
    () => [
      { label: "Recent jobs", value: queue.length, tone: "low" },
      { label: "Queued", value: queueSummary.queued, tone: queueSummary.queued > 0 ? "medium" : "low" },
      { label: "Running", value: queueSummary.running, tone: queueSummary.running > 0 ? "medium" : "low" },
      { label: "Completed", value: queueSummary.completed, tone: "low" },
      { label: "Failed", value: queueSummary.failed, tone: queueSummary.failed > 0 ? "critical" : "low" },
      {
        label: "Open flags",
        value: selectedPatient?.risk_flags?.length || 0,
        tone: (selectedPatient?.risk_flags?.length || 0) > 0 ? "high" : "low",
      },
    ],
    [queue.length, queueSummary.completed, queueSummary.failed, queueSummary.queued, queueSummary.running, selectedPatient]
  );

  const workspaceError =
    error ||
    getRequestErrorMessage(patientsError, "") ||
    getRequestErrorMessage(queueError, "") ||
    getRequestErrorMessage(jobError, "") ||
    "";

  const generate = async () => {
    try {
      setSubmitting(true);
      setError("");
      const idempotencyKey =
        typeof window !== "undefined" && window.crypto?.randomUUID ? window.crypto.randomUUID() : `${selectedPatientId}-${Date.now()}`;
      const response = await createReportJob(selectedPatientId, idempotencyKey);
      setActiveJobId(response.job_id);
      mutateQueue((current = []) => [response, ...current.filter((item) => item.job_id !== response.job_id)], false);
      mutateJob(response, false);
    } catch (requestError) {
      setError(getRequestErrorMessage(requestError, "Report generation failed."));
    } finally {
      setSubmitting(false);
    }
  };

  if (patientsLoading || queueLoading) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Loading report workspace...</p>
        </section>
      </div>
    );
  }

  if (workspaceError) {
    return (
      <div className="page-grid">
        <section className="panel full-span error-panel">
          <strong className="error-text">Unable to load report workspace</strong>
          <p>{workspaceError}</p>
          <button className="secondary-button small-button" type="button" onClick={() => window.location.reload()}>
            Reload
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="page-grid reports-grid">
      <section className="hero-panel report-hero">
        <div>
          <p className="eyebrow">Report operations</p>
          <h2>Report workspace</h2>
          <p className="subtle-copy">Queue patient report packages, watch execution, and pull finished artifacts.</p>
        </div>

        <div className="hero-badges">
          <span className={toneClassName(liveFeedConnected ? "low" : liveFeedError ? "high" : "medium")}>
            Live queue {lastEventAt ? new Date(lastEventAt).toLocaleTimeString() : "starting"}
          </span>
          <span className="tone tone-low">{queueSummary.completed} completed</span>
          <span className={toneClassName(queueSummary.failed > 0 ? "critical" : "low")}>
            {queueSummary.failed} failed
          </span>
        </div>
      </section>

      <section className="metrics-grid workspace-kpi-grid">
        {reportMetrics.map((metric) => (
          <article key={metric.label} className={`metric-card metric-card-${metric.tone}`}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className="panel panel-span-5 report-intake-panel">
        <div className="panel-header">
          <div className="panel-header-stack">
            <h3>Report intake</h3>
            <p>Select a patient and queue a new report package.</p>
          </div>
          <span className="subtle-copy">{selectedPatient ? selectedPatient.care_unit : "Patient selection"}</span>
        </div>

        <div className="form-grid">
          <label className="field">
            <span>Patient</span>
            <select value={selectedPatientId} onChange={(event) => setSelectedPatientId(Number(event.target.value))}>
              {patients.map((patient) => (
                <option key={patient.patient_id} value={patient.patient_id}>
                  {patient.name} ({patient.patient_id})
                </option>
              ))}
            </select>
          </label>

          <article className="status-card elevated-card">
            <span>Diagnosis</span>
            <strong>{selectedPatient?.diagnosis || "Select a patient"}</strong>
          </article>

          <article className="status-card elevated-card">
            <span>Open flags</span>
            <strong>{selectedPatient?.risk_flags?.length || 0}</strong>
          </article>

          <article className="status-card elevated-card">
            <span>Medications</span>
            <strong>{selectedPatient?.medications?.length || 0}</strong>
          </article>
        </div>

        <button className="primary-button accent-button launch-button" type="button" onClick={generate} disabled={submitting}>
          <span>{submitting ? "Queueing report..." : "Generate report package"}</span>
          <strong>{selectedPatient ? selectedPatient.name : "Select patient"}</strong>
        </button>
      </section>

      <section className="panel panel-span-7">
        <div className="panel-header">
          <div className="panel-header-stack">
            <h3>Active job detail</h3>
            <p>Track the selected job through each execution stage.</p>
          </div>
          <span className="subtle-copy">{currentJob ? currentJob.job_id : "No active selection"}</span>
        </div>

        {currentJob ? (
          <article className="report-card report-job-card elevated-card">
            <div className="panel-header">
              <div className="panel-header-stack">
                <h4>Patient {currentJob.patient_id}</h4>
                <p>{new Date(currentJob.created_at).toLocaleString()}</p>
              </div>
              <span
                className={toneClassName(
                  currentJob.status === "failed" ? "critical" : currentJob.status === "running" ? "medium" : "low"
                )}
              >
                {currentJob.status}
              </span>
            </div>

            <div className="registry-meta-grid">
              <article>
                <span>Workflow stage</span>
                <strong>{currentJob.workflow_stage.replaceAll("_", " ")}</strong>
              </article>
              <article>
                <span>Progress</span>
                <strong>{currentJob.progress_percent}%</strong>
              </article>
              <article>
                <span>Attempts</span>
                <strong>
                  {currentJob.attempt_count}/{currentJob.max_attempts}
                </strong>
              </article>
              <article>
                <span>Worker</span>
                <strong>{currentJob.worker_id || "Dispatcher pending"}</strong>
              </article>
            </div>

            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${currentJob.progress_percent}%` }} />
            </div>

            <div className="report-job-meta">
              <span>Created {new Date(currentJob.created_at).toLocaleString()}</span>
              <span>Updated {new Date(currentJob.updated_at).toLocaleString()}</span>
            </div>

            {currentJob.error ? <p className="error-text">{currentJob.error}</p> : null}

            <div className="report-actions-row">
              <button
                className="secondary-button"
                type="button"
                disabled={currentJob.status !== "completed"}
                onClick={() => downloadReportArtifact(currentJob.job_id)}
              >
                Download artifact
              </button>
              <button className="secondary-button" type="button" onClick={() => setActiveJobId("")}>
                Clear selection
              </button>
            </div>
          </article>
        ) : (
          <article className="empty-state-card elevated-card">
            <strong>No active report job</strong>
            <p className="subtle-copy">Queue a report to watch execution move through the live workflow.</p>
          </article>
        )}
      </section>

      <section className="panel full-span">
        <div className="panel-header">
          <div className="panel-header-stack">
            <h3>Queue history</h3>
            <p>Recent report packages and their latest execution state.</p>
          </div>
          <span className="subtle-copy">{queue.length} recent jobs</span>
        </div>

        <div className="queue-list">
          {queue.map((item) => (
            <button
              key={item.job_id}
              className={`roster-card ${item.job_id === activeJobId ? "is-active" : ""}`}
              type="button"
              onClick={() => setActiveJobId(item.job_id)}
            >
              <div className="directory-card-copy">
                <strong>Patient {item.patient_id}</strong>
                <p className="subtle-copy">
                  {item.workflow_stage.replaceAll("_", " ")} &middot; {item.progress_percent}% complete
                </p>
              </div>
              <div className="queue-meta">
                <span className={toneClassName(item.status === "failed" ? "critical" : item.status === "running" ? "medium" : "low")}>
                  {item.status}
                </span>
                <span className="subtle-copy">{new Date(item.updated_at).toLocaleString()}</span>
              </div>
            </button>
          ))}
          {queue.length === 0 ? <p className="subtle-copy">No report jobs are available yet.</p> : null}
        </div>
      </section>
    </div>
  );
};

export default Reports;
