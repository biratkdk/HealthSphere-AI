from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.enterprise_repository import (
    alerts_for_patient,
    build_patient_timeline,
    get_patient,
    list_handoff_notes,
    list_patient_tasks,
    list_patients,
)
from backend.app.ml_utils import predict_disease, predict_icu_risk, recommend_treatment
from backend.app.models import (
    Alert,
    DiseaseRiskResponse,
    HandoffNote,
    IcuRiskResponse,
    MissionControlAction,
    MissionControlSignal,
    PatientMissionControl,
    PatientRecord,
    PatientSummary,
    PatientTask,
    PatientTimelineEvent,
    TreatmentRecommendation,
    UserProfile,
    WorkflowSnapshot,
)


def _resolve_organization_id(current_user: UserProfile | None = None, organization_id: int | None = None) -> int:
    resolved = organization_id or getattr(current_user, "organization_id", None)
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account is not attached to an organization.")
    return resolved


def get_patient_or_404(
    db: Session,
    patient_id: int,
    current_user: UserProfile | None = None,
    organization_id: int | None = None,
) -> PatientRecord:
    resolved_organization_id = _resolve_organization_id(current_user, organization_id)
    patient = get_patient(db, resolved_organization_id, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} was not found.",
        )
    return patient


def list_patient_records(
    db: Session,
    current_user: UserProfile,
    query: str | None = None,
    limit: int = 200,
) -> list[PatientRecord]:
    return list_patients(db, _resolve_organization_id(current_user), query=query, limit=limit)


def get_icu_prediction(db: Session, patient_id: int, current_user: UserProfile) -> IcuRiskResponse:
    patient = get_patient_or_404(db, patient_id, current_user)
    return predict_icu_risk(patient)


def get_disease_prediction(db: Session, patient_id: int, current_user: UserProfile) -> DiseaseRiskResponse:
    patient = get_patient_or_404(db, patient_id, current_user)
    return predict_disease(patient)


def get_treatment_plan(db: Session, patient_id: int, current_user: UserProfile) -> TreatmentRecommendation:
    patient = get_patient_or_404(db, patient_id, current_user)
    icu_risk = predict_icu_risk(patient)
    disease_risk = predict_disease(patient)
    return recommend_treatment(patient, icu_risk, disease_risk)


def _elapsed_minutes(timestamp: datetime | None, *, now: datetime | None = None) -> int | None:
    if timestamp is None:
        return None
    reference = now or datetime.now(UTC)
    return max(0, int((reference - timestamp).total_seconds() // 60))


def _push_signal(
    bucket: list[MissionControlSignal],
    seen: set[tuple[str, str]],
    *,
    title: str,
    detail: str,
    tone: str,
    source: str,
) -> None:
    cleaned_title = title.strip()
    cleaned_detail = detail.strip()
    key = (source, cleaned_title.lower())
    if not cleaned_title or not cleaned_detail or key in seen:
        return
    bucket.append(MissionControlSignal(title=cleaned_title, detail=cleaned_detail, tone=tone, source=source))
    seen.add(key)


def _push_action(
    bucket: list[MissionControlAction],
    seen: set[tuple[str, str]],
    *,
    title: str,
    detail: str,
    priority: str,
    owner_hint: str | None = None,
    due_hint: str | None = None,
    linked_task_id: str | None = None,
) -> None:
    cleaned_title = title.strip()
    cleaned_detail = detail.strip()
    key = (cleaned_title.lower(), linked_task_id or "")
    if not cleaned_title or not cleaned_detail or key in seen:
        return
    bucket.append(
        MissionControlAction(
            title=cleaned_title,
            detail=cleaned_detail,
            priority=priority,
            owner_hint=owner_hint,
            due_hint=due_hint,
            linked_task_id=linked_task_id,
        )
    )
    seen.add(key)


def _format_follow_up(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}m"
    hours, remainder = divmod(minutes, 60)
    return f"{hours}h {remainder}m" if remainder else f"{hours}h"


def _workflow_snapshot(tasks: list[PatientTask], handoffs: list[HandoffNote]) -> WorkflowSnapshot:
    last_handoff = handoffs[0] if handoffs else None
    return WorkflowSnapshot(
        open_tasks=sum(task.status == "open" for task in tasks),
        in_progress_tasks=sum(task.status == "in_progress" for task in tasks),
        blocked_tasks=sum(task.status == "blocked" for task in tasks),
        completed_tasks=sum(task.status == "completed" for task in tasks),
        overdue_tasks=sum(task.is_overdue for task in tasks if task.status != "completed"),
        due_soon_tasks=sum(task.is_due_soon for task in tasks if task.status != "completed"),
        unassigned_tasks=sum(task.status != "completed" and task.ownership_status == "unassigned" for task in tasks),
        last_handoff_at=last_handoff.created_at if last_handoff else None,
        last_handoff_summary=last_handoff.summary if last_handoff else None,
        handoff_age_minutes=last_handoff.freshness_minutes if last_handoff else None,
    )


def _build_changed_signals(
    *,
    open_alerts: list[Alert],
    tasks: list[PatientTask],
    handoffs: list[HandoffNote],
    timeline: list[PatientTimelineEvent],
) -> list[MissionControlSignal]:
    items: list[MissionControlSignal] = []
    seen: set[tuple[str, str]] = set()

    sorted_alerts = sorted(open_alerts, key=lambda alert: {"critical": 4, "high": 3, "medium": 2, "low": 1}[alert.severity], reverse=True)
    if sorted_alerts:
        alert = sorted_alerts[0]
        _push_signal(
            items,
            seen,
            title=f"Alert pressure: {alert.title}",
            detail=alert.description,
            tone=alert.severity,
            source="alert",
        )

    task_update = next(
        (
            task
            for task in tasks
            if task.status in {"blocked", "in_progress"} or (task.status != "completed" and task.is_overdue)
        ),
        None,
    )
    if task_update is not None:
        task_tone = "critical" if task_update.is_overdue else ("high" if task_update.status == "blocked" else "medium")
        _push_signal(
            items,
            seen,
            title=f"Workflow update: {task_update.title}",
            detail=f"{task_update.status.replace('_', ' ')}. {task_update.due_label or 'No due time set.'}",
            tone=task_tone,
            source="task",
        )

    if handoffs:
        note = handoffs[0]
        detail = note.what_changed[0] if note.what_changed else note.details
        _push_signal(
            items,
            seen,
            title=f"Latest handoff: {note.summary}",
            detail=detail,
            tone="medium",
            source="handoff",
        )

    for category, title_prefix, tone in (("lab", "Lab update", "medium"), ("imaging", "Imaging update", "medium"), ("report", "Report flow", "low")):
        event = next((entry for entry in timeline if entry.category == category), None)
        if event is not None:
            _push_signal(
                items,
                seen,
                title=f"{title_prefix}: {event.label}",
                detail=event.summary,
                tone=tone,
                source=category,
            )

    return items[:4]


def _build_why_now_signals(
    *,
    icu_risk: IcuRiskResponse,
    disease_risk: DiseaseRiskResponse,
    open_alerts: list[Alert],
    tasks: list[PatientTask],
    handoffs: list[HandoffNote],
) -> list[MissionControlSignal]:
    items: list[MissionControlSignal] = []
    seen: set[tuple[str, str]] = set()

    risk_detail = ", ".join(icu_risk.drivers[:3]) or "The current ICU model score remains elevated."
    _push_signal(
        items,
        seen,
        title=f"ICU risk is {round(icu_risk.icu_risk * 100)}%",
        detail=risk_detail,
        tone=icu_risk.risk_band,
        source="risk",
    )
    if disease_risk.overall_risk_band in {"high", "critical"} or disease_risk.sepsis_watch_risk >= 0.5:
        _push_signal(
            items,
            seen,
            title="Disease surveillance is elevated",
            detail=(
                f"Sepsis watch {round(disease_risk.sepsis_watch_risk * 100)}%, "
                f"heart disease {round(disease_risk.heart_disease_risk * 100)}%, "
                f"diabetes {round(disease_risk.diabetes_risk * 100)}%."
            ),
            tone=disease_risk.overall_risk_band,
            source="risk",
        )

    unresolved_alerts = [alert for alert in open_alerts if not alert.acknowledged]
    if unresolved_alerts:
        _push_signal(
            items,
            seen,
            title=f"{len(unresolved_alerts)} unresolved alert{'s' if len(unresolved_alerts) != 1 else ''}",
            detail="The patient still has active alert pressure that needs acknowledgement or follow-through.",
            tone="high" if len(unresolved_alerts) > 1 else unresolved_alerts[0].severity,
            source="alert",
        )

    blocked_tasks = [task for task in tasks if task.status == "blocked"]
    overdue_tasks = [task for task in tasks if task.status != "completed" and task.is_overdue]
    unassigned_tasks = [task for task in tasks if task.status != "completed" and task.ownership_status == "unassigned"]
    if blocked_tasks or overdue_tasks or unassigned_tasks:
        fragments: list[str] = []
        if overdue_tasks:
            fragments.append(f"{len(overdue_tasks)} overdue")
        if blocked_tasks:
            fragments.append(f"{len(blocked_tasks)} blocked")
        if unassigned_tasks:
            fragments.append(f"{len(unassigned_tasks)} unassigned")
        _push_signal(
            items,
            seen,
            title="Execution risk is building",
            detail=f"{', '.join(fragments).capitalize()} tasks need ownership and closure.",
            tone="high" if overdue_tasks or blocked_tasks else "medium",
            source="task",
        )

    if handoffs:
        handoff = handoffs[0]
        if handoff.freshness_minutes >= 480:
            _push_signal(
                items,
                seen,
                title="Shift context is getting stale",
                detail=f"Last handoff was {handoff.freshness_minutes // 60}h ago. Refresh it before the next escalation.",
                tone="medium",
                source="handoff",
            )
    else:
        _push_signal(
            items,
            seen,
            title="No recent handoff recorded",
            detail="Document what changed, pending items, and watch-outs before the next team transition.",
            tone="medium",
            source="handoff",
        )

    return items[:4]


def _build_next_actions(
    *,
    treatment: TreatmentRecommendation,
    tasks: list[PatientTask],
    handoffs: list[HandoffNote],
) -> list[MissionControlAction]:
    items: list[MissionControlAction] = []
    seen: set[tuple[str, str]] = set()

    prioritized_tasks = sorted(
        (task for task in tasks if task.status != "completed"),
        key=lambda task: (
            0 if task.is_overdue else 1 if task.status == "blocked" else 2 if task.ownership_status == "unassigned" else 3,
            {"critical": 0, "high": 1, "medium": 2, "low": 3}[task.priority],
            task.due_in_minutes if task.due_in_minutes is not None else 10**9,
            -task.age_minutes,
        ),
    )
    for task in prioritized_tasks[:3]:
        _push_action(
            items,
            seen,
            title=task.title,
            detail=f"{task.detail} Current state: {task.status.replace('_', ' ')}.",
            priority="critical" if task.is_overdue else task.priority,
            owner_hint=task.assignee_username or "Unassigned",
            due_hint=task.due_label,
            linked_task_id=task.task_id,
        )

    latest_handoff = handoffs[0] if handoffs else None
    if latest_handoff and latest_handoff.pending_items:
        _push_action(
            items,
            seen,
            title="Close pending handoff items",
            detail=" | ".join(latest_handoff.pending_items[:2]),
            priority="high",
            owner_hint=latest_handoff.author_username,
            due_hint=f"Last handoff {latest_handoff.freshness_minutes}m ago",
        )
    elif latest_handoff is None:
        _push_action(
            items,
            seen,
            title="Publish a structured handoff",
            detail="Capture what changed, pending items, and watch-outs before the next team transition.",
            priority="medium",
        )

    for action in treatment.actions:
        _push_action(
            items,
            seen,
            title=action,
            detail=treatment.rationale,
            priority=treatment.priority,
            due_hint=f"Follow up in {_format_follow_up(treatment.recommended_follow_up_minutes)}",
        )

    return items[:5]


def _build_mission_control(
    *,
    icu_risk: IcuRiskResponse,
    disease_risk: DiseaseRiskResponse,
    treatment: TreatmentRecommendation,
    open_alerts: list[Alert],
    tasks: list[PatientTask],
    handoffs: list[HandoffNote],
    timeline: list[PatientTimelineEvent],
) -> PatientMissionControl:
    return PatientMissionControl(
        changed=_build_changed_signals(open_alerts=open_alerts, tasks=tasks, handoffs=handoffs, timeline=timeline),
        why_now=_build_why_now_signals(
            icu_risk=icu_risk,
            disease_risk=disease_risk,
            open_alerts=open_alerts,
            tasks=tasks,
            handoffs=handoffs,
        ),
        next_actions=_build_next_actions(treatment=treatment, tasks=tasks, handoffs=handoffs),
        workflow=_workflow_snapshot(tasks, handoffs),
    )


def get_patient_summary(db: Session, patient_id: int, current_user: UserProfile) -> PatientSummary:
    organization_id = _resolve_organization_id(current_user)
    patient = get_patient_or_404(db, patient_id, current_user)
    icu_risk = predict_icu_risk(patient)
    disease_risk = predict_disease(patient)
    treatment = recommend_treatment(patient, icu_risk, disease_risk)
    open_alerts = alerts_for_patient(db, organization_id, patient_id)
    tasks = list_patient_tasks(db, organization_id, patient_id)
    recent_handoffs = list_handoff_notes(db, organization_id, patient_id, limit=6)
    timeline = build_patient_timeline(db, organization_id, patient_id, limit=12)
    return PatientSummary(
        patient=patient,
        icu_risk=icu_risk,
        disease_risk=disease_risk,
        treatment=treatment,
        open_alerts=open_alerts,
        tasks=tasks,
        recent_handoffs=recent_handoffs,
        mission_control=_build_mission_control(
            icu_risk=icu_risk,
            disease_risk=disease_risk,
            treatment=treatment,
            open_alerts=open_alerts,
            tasks=tasks,
            handoffs=recent_handoffs,
            timeline=timeline,
        ),
    )


def get_patient_summary_for_organization(db: Session, organization_id: int, patient_id: int) -> PatientSummary:
    patient = get_patient_or_404(db, patient_id, organization_id=organization_id)
    icu_risk = predict_icu_risk(patient)
    disease_risk = predict_disease(patient)
    treatment = recommend_treatment(patient, icu_risk, disease_risk)
    open_alerts = alerts_for_patient(db, organization_id, patient_id)
    tasks = list_patient_tasks(db, organization_id, patient_id)
    recent_handoffs = list_handoff_notes(db, organization_id, patient_id, limit=6)
    timeline = build_patient_timeline(db, organization_id, patient_id, limit=12)
    return PatientSummary(
        patient=patient,
        icu_risk=icu_risk,
        disease_risk=disease_risk,
        treatment=treatment,
        open_alerts=open_alerts,
        tasks=tasks,
        recent_handoffs=recent_handoffs,
        mission_control=_build_mission_control(
            icu_risk=icu_risk,
            disease_risk=disease_risk,
            treatment=treatment,
            open_alerts=open_alerts,
            tasks=tasks,
            handoffs=recent_handoffs,
            timeline=timeline,
        ),
    )
