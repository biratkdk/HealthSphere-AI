# Population + Imaging Sprint

## Goal

This sprint closes the next two premium roadmap gaps without drifting away from HealthSphere AI's core product.

Targets:

1. ship a real Population Operations board
2. ship a real Imaging Triage Workbench
3. keep the work aligned with the current backend, data model, PostgreSQL setup, GitHub repo, and Vercel deployment flow

## Grounded starting state

Before the sprint started, the repo already had:

- patient mission-control summaries and workflow pressure signals in the backend
- patient-level tasks, handoffs, alerts, imaging, and report jobs
- analytics overview widgets, but no dedicated population command page
- imaging upload and storage, but no durable review-state workflow
- split frontend/backend Vercel deployment
- local PostgreSQL configured for development

The highest-leverage move was to avoid inventing a second product and instead expose the operational data already modeled by the backend.

## Two-hour execution slice

### 0:00-0:20

- audit current patient, analytics, imaging, and report flows
- confirm which models and endpoints can be reused
- identify the minimum schema work needed for imaging review workflow

### 0:20-0:55

- add imaging review workflow fields to persisted study records
- add API models for population board and imaging workbench
- add backend aggregation logic for unit pressure, hottest patients, overdue workflow, unresolved alerts, and imaging queue

### 0:55-1:25

- add frontend Population Operations page
- add frontend Imaging Workbench page
- wire both into the authenticated app shell and navigation
- keep both pages responsive within the new enterprise layout

### 1:25-1:45

- add review-state mutation controls for imaging studies
- connect linked report creation from the imaging lane
- verify route-aware header state and navigation behavior

### 1:45-2:00

- run backend tests
- run frontend production build
- prepare commit/deploy/push path

## Delivered in this sprint

### Population Operations board

- care-unit command view
- unit filter chips
- hottest-patient roster
- overdue workflow board
- unresolved alert board
- imaging review pressure section

### Imaging Triage Workbench

- prioritized study queue
- review states:
  - pending review
  - reviewed
  - escalated
  - signed off
- reviewer notes and escalation reason capture
- priority lane controls
- linked report queue action
- selected-study detail with patient context, alerts, overdue tasks, and imaging analysis summary

### Backend additions

- imaging review workflow fields persisted on `imaging_studies`
- population board endpoint
- imaging workbench endpoint
- imaging review update endpoint
- tests covering the new flows

## Not part of this sprint

These remain for the next deeper product passes:

- report studio with draft/approve/release workflow
- patient-scoped assistant with evidence-backed outputs
- clinical playbooks
- broader population outcome analytics
- PACS/FHIR/HL7 enterprise integrations

## Definition of done for this sprint

- the product can move from patient-level mission control to unit-level command mode
- imaging is no longer a file upload dead-end
- the new work fits the existing HealthSphere AI workflow instead of introducing a second product identity
