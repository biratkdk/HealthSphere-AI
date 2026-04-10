# Incident Response Runbook

## Trigger conditions

- frontend unavailable
- backend health probes failing
- report jobs stuck or failing repeatedly
- sudden alert volume spike

## Triage steps

1. Check `/health/live` and `/health/ready`.
2. Review deployment status and recent CI activity.
3. Inspect API logs using request IDs from failing sessions.
4. Confirm downstream artifact paths and environment variables are valid.
5. Run `python scripts/smoke_test.py --base-url http://<service-host>` from an operator shell.

## Escalation criteria

- repeated backend failures after restart
- widespread report job failures
- suspected data-quality issue affecting predictions
- suspected unauthorized access or secret exposure

