# ADR 0001: Separate Experience, Service, and Intelligence Layers

## Status

Accepted

## Context

The platform needs a clean contract between the user interface, API layer, and model workflows so each area can evolve without repeated cross-layer rewrites.

## Decision

Use:

- a React application for operations workflows
- a FastAPI service for stable request and response contracts
- a dedicated ML workspace for datasets, notebooks, and training code
- independent platform assets for runtime and infrastructure concerns

## Consequences

- clearer ownership and deployment boundaries
- simpler testing at the API and UI layer
- clearer separation between artifact-backed inference and deterministic fallback heuristics
- more explicit governance for model lifecycle changes
