# Presentation Audit

## Scope

This audit compares:

- current repo and split deployment:
  - frontend: `https://health-sphere-ai-pi.vercel.app/`
  - backend: `https://healthsphere-ai-backendvercelapp.vercel.app/`
- public comparison site:
  - `https://healthsphere-ai.vercel.app/`

Audit date: 2026-04-10

## Implementation Status

Status update: 2026-04-10

- phase 1 is now implemented in the frontend
- unauthenticated traffic now lands on a dedicated public-facing product page instead of a bare auth wall
- the auth experience is embedded into that landing flow rather than being the whole story
- the new public entry highlights current live strengths and separates next-lane concepts from already-shipped capability

## Verified Deployment Facts

### Our current split deployment

- the frontend HTML describes itself as a clinical operations console
- the frontend bundle contains route/module names for:
  - patients
  - reports
  - notifications
  - profile
  - admin
  - imaging
  - analytics
- the frontend bundle contains the deployed backend base URL
- the backend responds successfully on:
  - `/health/live`
  - `/api/v1/health/live`
  - `/api/v1/auth/providers`
- provider catalog currently exposes:
  - password login enabled
  - Google disabled
  - Facebook disabled

### Important split-deployment behavior

- `https://health-sphere-ai-pi.vercel.app/api/v1/health/live` returns the frontend HTML shell, not backend JSON
- this means the frontend deployment is not reverse-proxying `/api` to the backend
- the current app depends on the baked backend base URL in the frontend bundle rather than same-origin API forwarding

This is not inherently broken, but it is less elegant and less obvious than a same-origin deployment story.

### Public comparison site

The public site presents HealthSphere AI as a consumer-facing health education platform. The deployed bundle exposes public-facing modules such as:

- Disease Encyclopedia
- Pandemic Analytics
- AI Health Assistant
- Health Dashboard
- Add Health Entry
- Calculators

The public site appears optimized for first impression and broad browsing rather than authenticated clinical operations.

## Honest Comparison

### First impression

Winner: public comparison site

Why:

- clearer public landing experience
- stronger hero messaging
- richer public feature storytelling
- easier for an unauthenticated visitor to understand instantly

### Product depth

Winner: our current project

Why:

- real backend
- real auth and session model
- PostgreSQL-backed data model
- patient workflows
- report orchestration
- imaging storage and analysis
- notifications
- admin and audit flows
- deployment split already live

### Alignment with the current project goal

Winner: our current project

Why:

- this repo is a clinical operations system
- the public comparison site is a health education product
- the old public features are useful as presentation inspiration, but not as the core product direction

## What We Can Borrow Without Losing Product Focus

These are worth adapting:

- public landing hero with clear story and visual confidence
- feature showcase cards with strong copy and icons
- clean public routing for non-auth visitors
- richer motion, visual hierarchy, and branded sectioning
- public product modules that explain value before login
- guided demo or preview storytelling

These should be adapted, not copied literally:

- `Disease Encyclopedia` -> `Clinical Knowledge Center` or `Triage Knowledge Cards`
- `Pandemic Analytics` -> `Population Risk & Operations Analytics`
- `AI Health Assistant` -> `Clinical Ops Assistant`
- `Calculators` -> `Clinical Risk Calculators`
- `Add Health Entry` -> `Create Patient Note`, `Create Task`, or `Submit Imaging Study`

These should probably not be copied as-is:

- consumer wellness framing
- general self-help health education positioning
- broad public symptom guidance that dilutes the clinical operations identity

## Gaps Before Ours Clearly Wins On Presentation

### Gap 1: no public-facing landing page

Current behavior:

- unauthenticated users land in a clean but utilitarian sign-up/sign-in panel

Why it loses:

- it explains access, not product value
- it does not sell the system before asking for trust

Needed:

- dedicated landing page for unauthenticated visitors
- clear hero, product promise, screenshots, feature sections, deployment trust signals

### Gap 2: product story is hidden behind auth

Current behavior:

- the strongest UI work appears after sign-in

Why it loses:

- public visitors cannot see the dashboard quality, charts, workflow depth, or clinical focus

Needed:

- read-only demo mode or curated screenshots
- guided preview of dashboard, reports, patient workspace, and imaging flow

### Gap 3: deployment story is technically correct but not elegant

Current behavior:

- frontend is on one domain
- backend is on another domain
- `/api` on the frontend domain is not proxied to the backend

Why it loses:

- harder to reason about manually
- less polished for demos and operations

Needed:

- choose a single canonical frontend URL
- either proxy `/api` through the frontend domain or clearly standardize split-domain env handling and messaging

### Gap 4: auth presentation is too operational for first contact

Current behavior:

- login panel is good for a working app
- it is not strong enough as the first public brand experience

Needed:

- brand-led auth wrapper
- stronger supporting copy
- "why this matters" modules around the auth card

### Gap 5: public proof is thin

Current behavior:

- the repo is stronger than the public comparison site technically
- but the public-facing deployment does not showcase enough of that strength

Needed:

- screenshots or animated previews
- architecture/value summary
- workflow cards:
  - monitor
  - triage
  - coordinate
  - report
  - audit

### Gap 6: feature framing can be more memorable

Current behavior:

- current app labels are sensible and professional
- they are less "sticky" than the public comparison site's named modules

Needed:

- strong branded framing for product pillars
- examples:
  - Command Center
  - Clinical Knowledge
  - Imaging Triage
  - Report Orchestration
  - Care Coordination
  - Governance Trail

## Recommended Build Order

### Phase 1: fast presentation wins

- add a real landing page for logged-out users
- keep the existing auth panel but place it below or behind a stronger product story
- add screenshots or read-only preview cards for:
  - dashboard
  - patient workspace
  - reports
  - imaging
  - admin

### Phase 2: public feature adaptation

- add a clinical knowledge section inspired by the public site's encyclopedia concept
- add richer analytics storytelling inspired by the public site's analytics sections
- add a branded assistant concept only if it remains aligned with operations and evidence use

### Phase 3: deployment polish

- make one public canonical domain the default
- clean up same-origin or split-origin API behavior
- add stronger metadata, social preview, and demo-friendly copy

## Recommendation

Do not turn this repo into the public comparison site.

Do:

- keep the clinical operations core
- borrow the public site's storytelling discipline
- borrow its public browsing confidence
- borrow its feature packaging

That gives the best outcome:

- our current technical depth
- plus a public presentation layer strong enough to win first impression
