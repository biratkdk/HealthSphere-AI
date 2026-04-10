# Model Rollback Runbook

## When to roll back

- calibration drift exceeds release thresholds
- critical workflow metrics degrade after model promotion
- imaging triage confidence shifts without data explanation
- manual review finds unsafe recommendation patterns

## Rollback sequence

1. Mark the affected model entry as non-serving in the registry source of truth.
2. Repoint the serving artifact path to the prior approved version.
3. Restart or reload the backend model-serving layer.
4. Run smoke tests on prediction and reporting endpoints.
5. Document the reason, owner, and follow-up validation plan.

