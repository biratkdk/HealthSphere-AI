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
    if (!snapshot) {
      return;
    }

    if (snapshot.active_jobs) {
      mutateQueue(snapshot.active_jobs, false);
      if (activeJobId) {
        const matchingJob = snapshot.active_jobs.find((item) => item.job_id === activeJobId);
        if (matchingJob) {
          mutateJob(matchingJob, false);
        }
      }
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

  const loading = patientsLoading || queueLoading;
  if (loading) {
    return (
      <div className="page-grid">
        <section className="panel full-span loading-panel">
          <div className="spinner" />
          <p>Loading report workspace&hellip;</p>
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
          <p className="eyebrow">Care report orchestration</p>
          <h2>Generate patient briefing</h2>
          <p className="subtle-copy">
            Queue a durable clinical handoff package, track workflow stage progression, and deliver stored artifacts without
            holding the request open.
          </p>
        </div>

        <div className="hero-badges">
          <span className={toneClassName(liveFeedConnected ? "low" : liveFeedError ? "high" : "medium")}>
            live queue {lastEventAt ? new Date(lastEventAt).toLocaleTimeString() : "starting"}
          </span>
          <span className="tone tone-low">{queueSummary.queued} queued</span>
          <span className="tone tone-medium">{queueSummary.running} running</span>
          <span className={toneClassName(queueSummary.failed > 0 ? "critical" : "low")}>
            {queueSummary.completed} completed
          </span>
        </div>
      </section>

      <section className="panel panel-span-5 report-intake-panel">
        <div className="panel-header">
          <h3>Report intake</h3>
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
          <h3>Active job detail</h3>
          <span className="subtle-copy">{currentJob ? currentJob.job_id : "No active selection"}</span>
        </div>

        {currentJob ? (
          <article className="report-card report-job-card elevated-card">
            <div className="panel-header">
              <div>
                <strong>Patient {currentJob.patient_id}</strong>
                <p className="subtle-copy">{new Date(currentJob.created_at).toLocaleString()}</p>
              </div>
              <span className={toneClassName(currentJob.status === "failed" ? "critical" : currentJob.status === "running" ? "medium" : "low")}>
                {currentJob.status}
              </span>
            </div>

            <h4>{currentJob.workflow_stage.replaceAll("_", " ")}</h4>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${currentJob.progress_percent}%` }} />
            </div>
            <div className="report-job-meta">
              <span>{currentJob.progress_percent}% complete</span>
              <span>
                attempt {currentJob.attempt_count}/{currentJob.max_attempts}
              </span>
              <span>{currentJob.worker_id || "dispatcher pending"}</span>
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
            <p className="subtle-copy">
              Queue a report to watch the workflow stage move from claim, summary assembly, artifact persistence, and delivery.
            </p>
          </article>
        )}
      </section>

      <section className="panel full-span">
        <div className="panel-header">
          <h3>Queue history</h3>
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
              <div>
                <strong>Patient {item.patient_id}</strong>
                <p className="subtle-copy">
                  {item.workflow_stage.replaceAll("_", " ")} | {item.progress_percent}% complete
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
