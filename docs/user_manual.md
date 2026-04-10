# User Manual

## Intended users

- clinical reviewers
- care operations leads
- analytics staff
- platform administrators

## Accessing the workspace

1. Open the frontend application.
2. Create a local account from the `Sign up` tab or use `Sign in`.
3. If single sign-on is enabled, use the provider button instead of local credentials.
4. Wait for the secure session to load before navigating.

## Operations dashboard

Use the root route to review:

- active patient context
- deterioration and disease risk signals
- open alerts and unread inbox items
- report queue movement
- system capabilities and care-unit distribution

The dashboard consumes live operations events, so queue and inbox cards can refresh without a full page reload.

## Patient review

1. Open the patient workspace from the dashboard.
2. Review vitals, labs, medications, risk flags, and recent imaging studies.
3. Upload a new study when a fresh imaging triage result is required.

## Report workflow

1. Open `Reports`.
2. Select a patient.
3. Queue a report package.
4. Watch the workflow stage and progress bar move through the execution path.
5. Download the artifact after completion.

## Notification inbox

1. Open `Inbox`.
2. Review unread alert, imaging, and report notifications.
3. Mark items as read after review.

## Profile management

1. Open `Profile`.
2. Update identity and workspace preferences.
3. For local accounts, change the password by supplying the current password.
4. Save changes and confirm the success message.

## Admin review

1. Sign in with an admin account.
2. Open `Admin`.
3. Review recent audit activity and endpoint detail.

## Interpretation guidance

- critical and high signals indicate time-sensitive review
- medium signals indicate planned reassessment and closer observation
- low signals still require clinical validation and are not autonomous decisions

## Troubleshooting

- if the workspace fails to load, verify backend health first
- if reports remain queued, check the dispatcher or worker path
- if live updates stop, refresh the page and confirm the backend event stream is available
- if imaging uploads fail, verify storage configuration and file type
