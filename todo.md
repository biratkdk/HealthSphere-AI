# HealthSphere AI Premium Todo

## Verified starting point

This todo list is grounded in the current project state rather than a blank-sheet product wish list.

- Repository root is `d:\HealthSphere AI`.
- Git remote points to `https://github.com/biratkdk/HealthSphere-AI.git`.
- Current frontend surface already includes:
  - public landing
  - operations dashboard
  - patient directory
  - patient detail
  - reports
  - notifications
  - profile
  - admin
- Current backend surface already includes:
  - auth and provider catalog
  - session refresh and session revocation
  - patients, patient summary, timeline, tasks, and handoffs
  - imaging upload, storage, and retrieval
  - analytics overview
  - notifications and alerts
  - queue-first report jobs
  - admin users, invites, and audit logs
  - operations event stream
- Active database is PostgreSQL:
  - database: `healthsphere_ai`
  - migration: `0002_enterprise_hardening`
  - public tables: `15`
- Current workflow baseline:
  - monitor operations queue
  - inspect a patient
  - upload and review imaging
  - queue and monitor a report job
  - read notifications
  - manage sessions/profile/admin access
- Current deployment linkage:
  - local Vercel project link points to frontend project `health-sphere-ai`
  - frontend is already live on Vercel
  - split frontend/backend deployment remains the intended production model

## Product aim

HealthSphere AI should become a clinical operations command system, not a generic health AI app.

The product should compress the whole care-ops loop into one place:

1. detect who needs attention
2. explain why they need attention
3. recommend the next action
4. execute and assign the action
5. track what changed
6. prove what happened later

## Program structure

The work below is ordered so the product gets more premium without becoming harder to use.

### Phase 0: Platform baseline and UX hardening

Status: partially present

Already present:

- routed frontend with responsive baseline
- secure auth/session model
- Postgres-backed persistence
- SSE live feed
- Vercel deployments

Add next:

- fix responsive navigation and viewport safety on phones and small tablets
- remove content obstruction from sticky/fixed navigation patterns
- standardize mobile spacing, panel density, and action placement
- create a single reusable page layout contract for hero, controls, content, and sticky actions
- tighten empty states, error states, loading states, and no-data flows
- audit all pages for overflow, horizontal scroll, hidden buttons, and clipped actions
- reduce front-end inconsistency between landing style and signed-in product style
- clean split-domain deployment ergonomics:
  - validate same-origin mode
  - validate split frontend/backend mode
  - prevent local `.vercel` confusion between frontend and backend projects
- create a read-only demo mode or demo workspace path for presentation and testing
- add product screenshots and metadata/social previews for external sharing

Definition of done:

- no major layout break on mobile, tablet, laptop, or wide desktop
- primary actions remain visible without fighting sticky UI
- the product is usable one-handed on a phone
- demo-safe public product proof exists without exposing private data

### Phase 1: Patient Mission Control

Status: partial foundation exists in patient detail

Already present:

- vitals
- medications
- care flags
- tasks
- handoffs
- imaging studies
- patient timeline

Missing premium depth:

- a top-level patient delta summary:
  - what changed since last shift
  - what changed in the last 1 hour, 6 hours, and 24 hours
- a "why this patient is hot" panel using risk drivers, labs, vitals, imaging, and alerts
- a "next best actions" rail with priority, owner, due-by time, and rationale
- structured risk cards with evidence and trend movement
- compare current status vs baseline/prior snapshot
- care-unit context:
  - who else is at similar risk
  - what queue dependencies are blocking action
- quick actions:
  - create task
  - create handoff
  - queue report
  - acknowledge alert
  - request imaging follow-up
- compact shift-ready summary mode for bedside or rounds

Backend/data work:

- create patient summary snapshot assembler optimized for fast reads
- support delta summaries over time windows
- support explanation payloads tied to patient evidence
- support next-action recommendation payloads

Definition of done:

- one patient page answers:
  - what changed
  - why it matters
  - what happens next
  - who owns it

### Phase 2: Closed-loop tasks and handoffs

Status: partial foundation exists

Already present:

- task creation
- task completion
- handoff creation
- patient timeline logging

Missing premium depth:

- task owner assignment
- due date and due time
- SLA class
- overdue and breach state
- escalation rules
- task dependencies
- comments and status history
- shift ownership
- handoff templates by scenario
- unresolved items section in handoffs
- required fields for high-severity handoffs
- handoff acknowledgment and acceptance
- handoff quality scoring or completeness checks

Backend/data work:

- extend task and handoff schema
- add escalation scheduler and overdue calculations
- add task event history
- add handoff acknowledgment records

Definition of done:

- tasks and handoffs are operational objects with accountability, not just notes

### Phase 3: Imaging Triage Workbench

Status: partial foundation exists

Already present:

- imaging upload
- analysis result
- stored study record
- imaging download
- imaging-linked notifications

Missing premium depth:

- prioritized study queue
- review states:
  - uploaded
  - triage pending
  - under review
  - escalated
  - signed off
- current vs prior study comparison
- structured findings entry
- severity and confidence explanation
- image quality flags
- reviewer attribution and review timestamp
- explicit linkage from study review to task creation and report workflow
- study filters by unit, severity, age, and review status

Backend/data work:

- add imaging review status model
- support reviewer notes and structured findings
- support study prioritization and queue ordering
- expose filtered imaging worklist endpoints

Definition of done:

- imaging moves through a real review workflow instead of a single upload result

### Phase 4: Report Studio

Status: strong queue-first foundation exists

Already present:

- durable report jobs
- workflow stages
- retries
- active job detail
- artifact download

Missing premium depth:

- report editor and preview studio
- template library by use case
- evidence-backed sections populated from patient context
- draft, review, approved, released states
- report version history
- "what changed since last report" block
- reviewer notes and approval step
- one-click outputs for:
  - clinical handoff
  - rounding summary
  - discharge-style summary
  - admin review packet

Backend/data work:

- support richer report templates and rendered sections
- store report versions and review status
- support reviewer approval metadata

Definition of done:

- reports become a governed output workflow, not just a generated file

### Phase 5: Population Operations Lens

Status: analytics overview exists but is still shallow

Already present:

- analytics overview
- care-unit counts
- open alerts
- queue counters
- notification counters

Missing premium depth:

- unit-level command boards
- morning rounds view
- unresolved critical alerts board
- overdue tasks board
- report turnaround board
- imaging backlog board
- discharge readiness or step-down watchlist
- cohort filters and saved views
- role-based default dashboards
- watchlists that can be shared or pinned

Backend/data work:

- saved filters and saved views
- cohort query endpoints
- board-specific summary endpoints

Definition of done:

- operators can move from patient-by-patient mode to unit-level command mode without leaving the product

### Phase 6: Contextual assistant

Status: not yet built as a product feature

Target shape:

- patient-scoped assistant
- queue-scoped assistant
- evidence-grounded answers
- action-producing assistant, not small talk

Core outputs:

- summarize the last shift
- explain why risk increased
- draft handoff
- draft report starter
- propose next actions
- identify blockers
- generate patient brief for rounds

Rules:

- every answer must cite in-product evidence
- no unsupported advice
- actions should be producible directly from the assistant output

Backend/data work:

- retrieval layer over patient summary, labs, imaging, tasks, notifications, and timeline
- prompt governance
- audit logging for assistant actions
- reusable assistant response contracts

Definition of done:

- the assistant saves operator time and produces usable work, not generic text

### Phase 7: Clinical Playbooks

Status: not yet built

Target shape:

- diagnosis-linked playbooks
- escalation guides
- checklist bundles
- calculator modules
- report templates
- care bundle suggestions

Examples:

- respiratory decline playbook
- sepsis watch playbook
- chest imaging escalation playbook
- diabetes watch checklist

Definition of done:

- users can move from detected risk to a trusted structured action pathway inside the same product

### Phase 8: Outcome and workflow analytics

Status: only baseline operational counters exist

Add:

- alert-to-action time
- task completion time
- report turnaround time
- imaging review turnaround time
- handoff completion/acknowledgment rate
- overdue workload by care unit
- queue bottleneck detection
- model performance and drift monitoring
- operator workload and throughput views

Definition of done:

- the product can prove it improves workflow, not just display activity

### Phase 9: Performance, speed, and reliability

Status: good baseline exists, but premium speed requires more product-side optimization

Add:

- precomputed patient summary snapshots
- delta caching for live updates
- prefetch likely next patient data
- faster report packet assembly
- prioritized job dispatch based on urgency and queue age
- thumbnail and metadata caching for imaging
- safer SSE reconnect behavior and stream recovery
- better failure visibility for async jobs
- background warm paths for common pages

Definition of done:

- the product feels fast because the workflow is pre-organized, not just because the UI is animated

### Phase 10: Enterprise controls and integrations

Status: partially present

Already present:

- local auth
- provider-ready auth model
- RBAC
- audit logs
- invite codes
- session management

Add:

- stronger SSO rollout
- organization-level settings
- richer admin controls
- audit export
- policy configuration
- external identity mapping
- PACS/RIS integration path
- FHIR/HL7 integration path
- webhook/event integration path
- enterprise retention controls

Definition of done:

- the platform is easier to adopt in real organizations without custom one-off changes

## Recommended build order

1. Phase 0 UX hardening and responsive cleanup
2. Phase 1 Patient Mission Control
3. Phase 2 Closed-loop tasks and handoffs
4. Phase 3 Imaging Triage Workbench
5. Phase 4 Report Studio
6. Phase 5 Population Operations Lens
7. Phase 6 Contextual assistant
8. Phase 7 Clinical Playbooks
9. Phase 8 Outcome and workflow analytics
10. Phase 9 Performance and reliability
11. Phase 10 Enterprise controls and integrations

## Immediate next implementation targets

- finish mobile and tablet responsive hardening
- reshape patient detail into Patient Mission Control
- extend tasks and handoffs with ownership, due time, and SLA behavior
- start imaging review state model
- start report template/version model

