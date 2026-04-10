import React from "react";

import LoginPanel from "./LoginPanel";
import PatientVitals from "./PatientVitals";
import RiskRadarChart from "./RiskRadarChart";
import SystemStatusPanel from "./SystemStatusPanel";
import "../styles/public-landing.css";

const platformPillars = [
  {
    label: "Mission control",
    title: "See what changed first",
    detail: "The signed-in product is built around delta visibility, accountable follow-through, and the next clinical action.",
  },
  {
    label: "Workflow engine",
    title: "Keep ownership visible",
    detail: "Tasks, handoffs, due state, and unresolved pressure remain attached to the patient and the care unit.",
  },
  {
    label: "Imaging and reports",
    title: "Move from review to release",
    detail: "Imaging context and report delivery stay inside the same operating system instead of splitting across tools.",
  },
];

const platformIndex = [
  {
    code: "01",
    status: "Live",
    title: "Patient Mission Control",
    detail: "What changed, why it matters now, and the next accountable actions on one patient surface.",
    points: ["Mission control summary", "Open alerts and acknowledgements", "Timeline, labs, tasks, and imaging in one view"],
  },
  {
    code: "02",
    status: "Live",
    title: "Ownership and SLA Engine",
    detail: "Workflow stays explicit with assignees, due states, overdue pressure, and structured handoffs.",
    points: ["Ownership status and due labels", "Structured what-changed and pending items", "Task and handoff pressure in context"],
  },
  {
    code: "03",
    status: "Live",
    title: "Imaging Review Lane",
    detail: "Clinical review stays attached to the patient record instead of becoming a disconnected upload flow.",
    points: ["DICOM-aware upload guard", "Imaging context tied to the patient", "Synthetic demo imaging already linked in product proof"],
  },
  {
    code: "04",
    status: "Live",
    title: "Report Orchestration",
    detail: "Reports move through queue, progress, and delivery states with clearer operational visibility.",
    points: ["Queue and workflow stages", "Progress tracking", "Release context tied to imaging and patient state"],
  },
  {
    code: "05",
    status: "Live",
    title: "Governance and Admin",
    detail: "Sessions, roles, invites, notifications, and audit visibility are product primitives, not afterthoughts.",
    points: ["Role-aware sessions", "Admin and invite controls", "Audit-ready operating model"],
  },
  {
    code: "06",
    status: "Next",
    title: "Population Command Boards",
    detail: "The next layer brings ICU risk boards, overdue workflow boards, and unit-level control into the same shell.",
    points: ["Care-unit pressure views", "Overdue task and unresolved-alert boards", "Outcome and throughput analytics"],
  },
];

const heroMetrics = [
  { label: "High acuity", value: "68%", detail: "ICU deterioration watch", tone: "high" },
  { label: "Imaging review", value: "04", detail: "priority studies in lane", tone: "medium" },
  { label: "Report queue", value: "03", detail: "active release steps", tone: "medium" },
  { label: "Audit events", value: "124", detail: "tracked this shift", tone: "low" },
];

const demoSummary = {
  patient: {
    name: "Aarav Sharma",
    patient_id: 1001,
    care_unit: "ICU North",
    diagnosis: "Respiratory decline",
    last_updated: "2026-04-10T10:18:00Z",
    risk_flags: ["oxygen escalation", "portable imaging", "rapid review"],
    vitals: {
      heart_rate: 108,
      respiratory_rate: 24,
      systolic_bp: 98,
      temperature_c: 37.8,
      oxygen_saturation: 91,
      pain_score: 4,
    },
    labs: [
      { name: "CRP", value: "18.4", unit: "mg/L", collected_at: "2026-04-10T09:10:00Z" },
      { name: "Lactate", value: "2.1", unit: "mmol/L", collected_at: "2026-04-10T09:05:00Z" },
      { name: "WBC", value: "14.2", unit: "x10^9/L", collected_at: "2026-04-10T08:52:00Z" },
      { name: "D-dimer", value: "0.87", unit: "mg/L", collected_at: "2026-04-10T08:34:00Z" },
      { name: "Creatinine", value: "1.1", unit: "mg/dL", collected_at: "2026-04-10T08:20:00Z" },
      { name: "Procalcitonin", value: "0.42", unit: "ng/mL", collected_at: "2026-04-10T08:12:00Z" },
    ],
  },
  icu_risk: {
    icu_risk: 0.68,
    risk_band: "high",
    drivers: [
      "Escalating oxygen demand over the last two hours.",
      "Portable imaging confirms the need for fast review.",
      "Nursing interventions are increasing in frequency.",
    ],
  },
  disease_risk: {
    diabetes_risk: 0.29,
    heart_disease_risk: 0.57,
    sepsis_watch_risk: 0.43,
    overall_risk_band: "high",
  },
  imaging: {
    anomaly_score: 0.72,
  },
  treatment: {
    priority: "high",
    recommended_follow_up_minutes: 15,
    rationale: "Portable chest imaging and respiratory trend warrant close follow-up.",
    actions: [
      "Portable chest review in queue.",
      "Respiratory reassessment in 15 minutes.",
      "Escalate if oxygen saturation drops below 90%.",
    ],
  },
};

const demoAnalytics = {
  total_patients: 124,
  open_alerts: 7,
  critical_alerts: 2,
  unread_notifications: 12,
  report_queue: {
    queued: 3,
    running: 1,
  },
  capabilities: {
    task_execution_mode: "dispatcher",
    storage_backend: "postgres + object store",
    live_updates_enabled: true,
    metrics_enabled: true,
    oidc_enabled: false,
  },
  care_units: [
    { care_unit: "ICU North", patient_count: 18, open_alerts: 3 },
    { care_unit: "Stepdown East", patient_count: 34, open_alerts: 2 },
    { care_unit: "Ward South", patient_count: 49, open_alerts: 1 },
    { care_unit: "ED Hold", patient_count: 23, open_alerts: 1 },
  ],
};

const demoReportJobs = [
  {
    job_id: "rpt-1042",
    patient_id: 1001,
    status: "running",
    workflow_stage: "clinical_review",
    progress_percent: 68,
    requested_by: "radiology",
    created_label: "10:12 NPT",
  },
  {
    job_id: "rpt-1040",
    patient_id: 1044,
    status: "queued",
    workflow_stage: "draft_assembly",
    progress_percent: 24,
    requested_by: "ward_a",
    created_label: "10:04 NPT",
  },
  {
    job_id: "rpt-1038",
    patient_id: 998,
    status: "delivered",
    workflow_stage: "released",
    progress_percent: 100,
    requested_by: "icu_north",
    created_label: "09:52 NPT",
  },
];

const accessNotes = [
  {
    title: "Live stack",
    detail: "Frontend, FastAPI APIs, PostgreSQL persistence, reports, notifications, and admin lanes are already connected.",
  },
  {
    title: "Enterprise posture",
    detail: "Role-aware sessions, provider-ready auth, and audit logging give the product a credible operating model.",
  },
];

const imagingFindings = [
  "Synthetic imaging from the project demo dataset is linked directly to the review lane.",
  "Finding context stays attached to the patient, report state, and follow-up timing.",
  "Operators can move from image review to delivery without switching products.",
];

const queueTone = {
  queued: "low",
  running: "medium",
  delivered: "low",
  failed: "critical",
};

const PublicLanding = ({ theme, setTheme }) => {
  const nextTheme = theme === "dark" ? "light" : "dark";
  const themeLabel = theme === "dark" ? "Day mode" : "Night mode";

  return (
    <div className="public-shell">
      <header className="public-header">
        <div className="public-brand">
          <div className="public-brand-mark">HS</div>
          <div className="public-brand-copy">
            <p className="public-mono-label">Clinical operations platform</p>
            <h1>HealthSphere AI</h1>
            <p>Patient risk, imaging review, reports, notifications, and accountable handoffs in one workspace.</p>
          </div>
        </div>

        <nav className="public-nav" aria-label="Public navigation">
          <a href="#platform">Platform</a>
          <a href="#index">Index</a>
          <a href="#evidence">Proof</a>
          <a href="#access">Access</a>
        </nav>

        <div className="public-header-actions">
          <button
            className="theme-toggle"
            type="button"
            onClick={() => setTheme(nextTheme)}
            title={`Switch to ${nextTheme} mode`}
            aria-label={`Switch to ${nextTheme} mode`}
          >
            {themeLabel}
          </button>
          <a className="secondary-button small-button" href="#access">
            Enter workspace
          </a>
        </div>
      </header>

      <main className="public-main">
        <section className="public-hero-panel" id="platform">
          <div className="public-hero-copy">
            <div className="public-kicker-row">
              <span className="public-kicker-pill">Working product stack</span>
              <span className="public-mono-label">Cleaner front door. Same serious system.</span>
            </div>

            <h2>The clinical operating system for patient pressure, imaging review, and report release.</h2>

            <p className="public-lead">
              HealthSphere AI turns the active care queue into one managed workspace: live pressure, imaging context,
              staged reports, and accountable handoffs.
            </p>

            <div className="public-hero-actions">
              <a className="primary-button accent-button" href="#access">
                Enter the live system
              </a>
              <a className="secondary-button" href="#evidence">
                See product proof
              </a>
            </div>

            <div className="public-pillar-grid" aria-label="Platform pillars">
              {platformPillars.map((pillar) => (
                <article key={pillar.title} className="public-pillar-card">
                  <p className="public-mono-label">{pillar.label}</p>
                  <h3>{pillar.title}</h3>
                  <p>{pillar.detail}</p>
                </article>
              ))}
            </div>
          </div>

          <aside className="public-command-window public-app-surface" aria-label="Command workspace preview">
            <div className="public-window-topbar">
              <div className="public-window-dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <p>Operations / Aarav Sharma / ICU North</p>
              <span className="public-window-badge">Read-only product slice</span>
            </div>

            <div className="public-window-metrics">
              {heroMetrics.map((metric) => (
                <article key={metric.label} className={`metric-card metric-card-${metric.tone}`}>
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  <small>{metric.detail}</small>
                </article>
              ))}
            </div>

            <div className="public-window-grid">
              <article className="panel public-embedded-panel public-command-chart">
                <RiskRadarChart summary={demoSummary} />
              </article>

              <article className="panel public-embedded-panel public-command-flow">
                <div className="panel-header">
                  <div>
                    <p className="public-mono-label">Workflow lane</p>
                    <h3>Imaging to report release</h3>
                  </div>
                  <span className="tone tone-low">3 active jobs</span>
                </div>

                <div className="queue-list public-tight-list">
                  {demoReportJobs.map((job) => (
                    <article key={job.job_id} className="queue-row elevated-card">
                      <div>
                        <strong>Patient {job.patient_id}</strong>
                        <p className="subtle-copy">{job.created_label}</p>
                        <p className="subtle-copy">{job.workflow_stage.replaceAll("_", " ")}</p>
                      </div>
                      <div className="queue-meta">
                        <span className={`tone tone-${queueTone[job.status] || "low"}`}>{job.status}</span>
                        <span className="subtle-copy">{job.progress_percent}%</span>
                        <span className="subtle-copy">{job.requested_by}</span>
                      </div>
                    </article>
                  ))}
                </div>

                <div className="public-window-footer">
                  <span className="public-window-tag">Imaging linked</span>
                  <span className="public-window-tag">Report staged</span>
                  <span className="public-window-tag">Audit ready</span>
                </div>
              </article>
            </div>
          </aside>
        </section>

        <section className="public-section public-index-section" id="index">
          <div className="public-section-heading public-section-heading-wide">
            <p className="public-mono-label">Platform index</p>
            <h2>The product lanes are richer than the reference app, but aligned to HealthSphere AI&apos;s real core.</h2>
            <p>
              This is not a wellness dashboard or a generic education site. The feature system is organized around
              clinical operations: patient control, ownership, imaging, reports, governance, and the next population
              command layer.
            </p>
          </div>

          <div className="public-index-grid">
            {platformIndex.map((item) => (
              <article key={item.title} className="public-index-card">
                <div className="public-index-top">
                  <span className="public-index-code">{item.code}</span>
                  <span className={`public-index-status public-index-status-${item.status.toLowerCase()}`}>{item.status}</span>
                </div>
                <div className="public-index-copy">
                  <h3>{item.title}</h3>
                  <p>{item.detail}</p>
                </div>
                <ul className="public-index-list">
                  {item.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>

        <section className="public-section" id="evidence">
          <div className="public-section-heading">
            <p className="public-mono-label">Product proof</p>
            <h2>Real product surfaces, not concept-only marketing.</h2>
            <p>
              The landing now shows the actual dashboard language of the signed-in product, paired with a synthetic
              demo patient and project imaging asset.
            </p>
          </div>

          <div className="public-proof-grid">
            <div className="public-proof-card public-proof-vitals public-app-surface">
              <PatientVitals summary={demoSummary} />
            </div>

            <div className="public-proof-card public-proof-system public-app-surface">
              <SystemStatusPanel analytics={demoAnalytics} reportJobs={demoReportJobs} />
            </div>

            <div className="public-proof-card public-proof-imaging public-app-surface">
              <article className="panel public-imaging-proof-panel">
                <div className="panel-header">
                  <div>
                    <p className="public-mono-label">Imaging proof</p>
                    <h3>Clinical review stays attached to delivery state</h3>
                  </div>
                  <span className="tone tone-medium">synthetic demo</span>
                </div>

                <div className="public-imaging-figure">
                  <img
                    src="/landing-imaging-demo.jpg"
                    alt="Synthetic clinical imaging demo from the HealthSphere AI project dataset."
                    loading="lazy"
                  />
                  <div className="public-imaging-overlay">
                    <span className="risk-badge risk-high">Opacity watch</span>
                    <span className="risk-badge risk-medium">Priority review</span>
                  </div>
                </div>

                <ul className="public-imaging-list">
                  {imagingFindings.map((finding) => (
                    <li key={finding}>{finding}</li>
                  ))}
                </ul>

                <div className="queue-row elevated-card public-inline-queue">
                  <div>
                    <strong>Linked release step</strong>
                    <p className="subtle-copy">Draft report remains staged until the imaging review is acknowledged.</p>
                  </div>
                  <div className="queue-meta">
                    <span className="tone tone-medium">reviewing</span>
                    <span className="subtle-copy">68%</span>
                  </div>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section className="public-section public-access-section" id="access">
          <div className="public-access-layout">
            <div className="public-access-copy">
              <p className="public-mono-label">Secure operator access</p>
              <h2>Enter the live workspace through a calmer front door.</h2>
              <p>
                The presentation is more disciplined now, but the substance is the same: authenticated sessions,
                backend APIs, PostgreSQL records, report workflow, imaging review, notifications, and admin control.
              </p>

              <div className="public-access-note-grid">
                {accessNotes.map((note) => (
                  <article key={note.title} className="public-access-note">
                    <strong>{note.title}</strong>
                    <p>{note.detail}</p>
                  </article>
                ))}
              </div>
            </div>

            <LoginPanel defaultMode="signin" variant="embedded" />
          </div>
        </section>
      </main>
    </div>
  );
};

export default PublicLanding;
