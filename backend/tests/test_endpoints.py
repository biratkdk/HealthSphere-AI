import os
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import numpy as np
from fastapi.testclient import TestClient
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["DATABASE_URL_UNPOOLED"] = "sqlite://"
os.environ["SERVICE_API_KEY"] = "test-service-api-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-32chars-long"
os.environ["SESSION_SECRET_KEY"] = "test-session-secret-key-32chars"
os.environ["BOOTSTRAP_ADMIN_USERNAME"] = "admin"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "AdminPass123!"
os.environ["BOOTSTRAP_CLINICIAN_USERNAME"] = "clinician"
os.environ["BOOTSTRAP_CLINICIAN_PASSWORD"] = "ClinicianPass123!"
os.environ["BOOTSTRAP_ANALYST_USERNAME"] = "analyst"
os.environ["BOOTSTRAP_ANALYST_PASSWORD"] = "AnalystPass123!"

from backend.app.core.config import get_settings
from backend.main import app, bootstrap_application


bootstrap_application()
client = TestClient(app)
settings = get_settings()
FIXTURE_IMAGE = Path(__file__).resolve().parents[2] / "ml_pipeline" / "data" / "raw" / "imaging" / "clear_01.png"


def build_test_dicom() -> bytes:
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    dataset = FileDataset("scan.dcm", {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.Modality = "OT"
    dataset.PatientName = "Test^Patient"
    dataset.Rows = 8
    dataset.Columns = 8
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 8
    dataset.BitsStored = 8
    dataset.HighBit = 7
    dataset.PixelRepresentation = 0
    dataset.PixelData = np.arange(64, dtype=np.uint8).reshape(8, 8).tobytes()

    buffer = BytesIO()
    dataset.save_as(buffer, little_endian=True, implicit_vr=False, enforce_file_format=True)
    return buffer.getvalue()


def auth_headers(username: str = "clinician", password: str = "ClinicianPass123!") -> dict[str, str]:
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def wait_for_report_completion(job_id: str, headers: dict[str, str], attempts: int = 5) -> dict:
    for _ in range(attempts):
        response = client.get(f"/reports/jobs/{job_id}", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] == "completed":
            return payload
        client.post("/internal/jobs/dispatch", headers={"x-api-key": settings.service_api_key})
        time.sleep(0.05)
    raise AssertionError(f"Report job {job_id} did not complete after {attempts} attempts.")


def test_live_health() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"


def test_protected_endpoints_require_authentication() -> None:
    response = client.get("/patients")
    assert response.status_code == 401


def test_auth_me_returns_profile() -> None:
    response = client.get("/auth/me", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["role"] == "clinician"


def test_operations_stream_token_issues_ephemeral_token() -> None:
    response = client.get("/events/stream-token", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert len(payload["stream_token"]) > 40


def test_auth_provider_catalog() -> None:
    response = client.get("/auth/providers")
    assert response.status_code == 200
    providers = {provider["id"]: provider for provider in response.json()["providers"]}
    assert providers["password"]["available"] is True
    assert providers["google"]["brand"] == "google"
    assert providers["facebook"]["brand"] == "facebook"
    assert providers["google"]["available"] is False
    assert providers["facebook"]["available"] is False


def test_disabled_facebook_login_returns_not_found() -> None:
    response = client.get("/auth/oauth/facebook/login")
    assert response.status_code == 404


def test_signup_returns_session_and_profile() -> None:
    token = uuid4().hex[:8]
    response = client.post(
        "/auth/signup",
        json={
            "full_name": "Taylor Jordan",
            "email": f"taylor-{token}@example.com",
            "password": "StrongerPass!234",
            "role": "clinician",
            "department": "Cardiology",
            "organization": "Northstar Health",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["username"].startswith(f"taylor-{token}")
    assert payload["user"]["preferences"]["department"] == "Cardiology"


def test_profile_update_supports_preferences_and_password_change() -> None:
    token = uuid4().hex[:8]
    signup_response = client.post(
        "/auth/signup",
        json={
            "username": f"profile-{token}",
            "full_name": "Jamie Cross",
            "email": f"profile-{token}@example.com",
            "password": "ProfilePass!234",
            "role": "clinician",
        },
    )
    assert signup_response.status_code == 200
    access_token = signup_response.json()["access_token"]

    response = client.patch(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "title": "Attending Physician",
            "location": "Remote command desk",
            "dashboard_view": "patient-command",
            "current_password": "ProfilePass!234",
            "new_password": "ProfilePass!234Updated",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["preferences"]["title"] == "Attending Physician"
    assert payload["preferences"]["dashboard_view"] == "patient-command"

    relogin = client.post(
        "/auth/token",
        data={"username": f"profile-{token}", "password": "ProfilePass!234Updated"},
    )
    assert relogin.status_code == 200


def test_patient_summary_contains_predictions() -> None:
    response = client.get("/patients/1001/summary", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["patient"]["patient_id"] == 1001
    assert "icu_risk" in payload
    assert "disease_risk" in payload
    assert "treatment" in payload
    assert "mission_control" in payload
    assert "changed" in payload["mission_control"]
    assert "why_now" in payload["mission_control"]
    assert "next_actions" in payload["mission_control"]
    assert "workflow" in payload["mission_control"]


def test_patient_roster_uses_nepali_seed_pack() -> None:
    response = client.get("/patients", headers=auth_headers())
    assert response.status_code == 200
    patients = response.json()
    names = {patient["name"] for patient in patients}
    assert len(patients) >= 20
    assert {"Srijana Karki", "Nabin Shrestha", "Sabina Magar", "Suraj Maharjan"}.issubset(names)


def test_clinician_can_view_model_registry() -> None:
    response = client.get("/models/registry", headers=auth_headers())
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_report_job() -> None:
    job_response = client.post("/reports/patient/1002", headers=auth_headers())
    assert job_response.status_code == 200
    job_id = job_response.json()["job_id"]

    queue_response = client.get("/reports/jobs", headers=auth_headers())
    assert queue_response.status_code == 200
    assert any(job["job_id"] == job_id for job in queue_response.json())

    status_response = client.get(f"/reports/jobs/{job_id}", headers=auth_headers())
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["patient_id"] == 1002
    assert payload["status"] in {"queued", "running", "completed"}


def test_internal_dispatch_endpoint_accepts_service_key() -> None:
    response = client.post("/internal/jobs/dispatch", headers={"x-api-key": settings.service_api_key})
    assert response.status_code == 200
    assert "claimed" in response.json()


def test_operations_event_stream_returns_sse_payload() -> None:
    token_response = client.get("/events/stream-token", headers=auth_headers())
    assert token_response.status_code == 200
    stream_token = token_response.json()["stream_token"]

    with client.stream("GET", f"/events/operations?stream_token={stream_token}&once=true") as response:
        assert response.status_code == 200
        first_chunk = next(response.iter_text())
        assert "event:" in first_chunk
        assert "data:" in first_chunk


def test_notifications_and_analytics() -> None:
    headers = auth_headers()

    analytics_response = client.get("/analytics/overview", headers=headers)
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert analytics["total_patients"] >= 1
    assert "report_queue" in analytics

    notifications_response = client.get("/notifications", headers=headers)
    assert notifications_response.status_code == 200
    notifications = notifications_response.json()
    assert isinstance(notifications, list)

    if notifications:
        notification_id = notifications[0]["notification_id"]
        mark_response = client.post(f"/notifications/{notification_id}/read", headers=headers)
        assert mark_response.status_code == 200
        assert mark_response.json()["is_read"] is True


def test_imaging_analysis() -> None:
    payload = FIXTURE_IMAGE.read_bytes()
    response = client.post(
        "/analyze/imaging",
        data={"patient_id": "1001"},
        files={"file": ("scan.png", payload, "image/png")},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert "result" in body
    assert 0 <= body["confidence"] <= 1
    assert body["study_reference"]


def test_dicom_imaging_analysis() -> None:
    payload = build_test_dicom()
    response = client.post(
        "/analyze/imaging",
        data={"patient_id": "1001"},
        files={"file": ("scan.dcm", payload, "application/dicom")},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["study_reference"]
    assert 0 <= body["confidence"] <= 1


def test_report_artifact_download() -> None:
    headers = auth_headers()
    response = client.post("/reports/patient/1001", headers=headers)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    wait_for_report_completion(job_id, headers)

    artifact_response = client.get(f"/reports/jobs/{job_id}/artifact", headers=headers)
    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"].startswith("application/json")
    assert "\"patient_id\": 1001" in artifact_response.text


def test_imaging_study_download() -> None:
    payload = FIXTURE_IMAGE.read_bytes()
    response = client.post(
        "/analyze/imaging",
        data={"patient_id": "1001"},
        files={"file": ("scan.png", payload, "image/png")},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    study_id = response.json()["study_reference"]

    download_response = client.get(f"/imaging/studies/{study_id}/content", headers=auth_headers())
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("image/png")
    assert download_response.content == payload


def test_cookie_session_refresh_and_logout() -> None:
    with TestClient(app) as local_client:
        login_response = local_client.post(
            "/auth/token",
            data={"username": "clinician", "password": "ClinicianPass123!"},
        )
        assert login_response.status_code == 200
        assert login_response.cookies.get("healthsphere_access")
        assert login_response.cookies.get("healthsphere_refresh")

        me_response = local_client.get("/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "clinician"

        refresh_response = local_client.post("/auth/refresh")
        assert refresh_response.status_code == 200
        assert refresh_response.json()["user"]["username"] == "clinician"

        logout_response = local_client.post("/auth/logout")
        assert logout_response.status_code == 204

        after_logout = local_client.get("/auth/me")
        assert after_logout.status_code == 401


def test_patient_tasks_handoffs_and_timeline() -> None:
    headers = auth_headers()

    task_response = client.post(
        "/patients/1001/tasks",
        headers=headers,
        json={
            "title": "Repeat lactate",
            "detail": "Repeat lactate in 2 hours and update the escalation note.",
            "priority": "high",
            "assignee_username": "clinician",
            "due_at": "2030-01-01T00:00:00Z",
        },
    )
    assert task_response.status_code == 200
    task_payload = task_response.json()
    task_id = task_payload["task_id"]
    assert task_payload["ownership_status"] == "assigned"
    assert task_payload["sla_status"] == "on_track"
    assert task_payload["due_label"].startswith("Due in")

    handoff_response = client.post(
        "/patients/1001/handoffs",
        headers=headers,
        json={
            "summary": "Night shift handoff",
            "details": (
                "What changed\n"
                "- Escalation sent to covering team\n"
                "Pending\n"
                "- Repeat lactate in 2 hours\n"
                "Watch\n"
                "- Escalate if MAP < 65"
            ),
        },
    )
    assert handoff_response.status_code == 200
    handoff_payload = handoff_response.json()
    assert handoff_payload["what_changed"] == ["Escalation sent to covering team"]
    assert handoff_payload["pending_items"] == ["Repeat lactate in 2 hours"]
    assert handoff_payload["watch_items"] == ["Escalate if MAP < 65"]

    timeline_response = client.get("/patients/1001/timeline", headers=headers)
    assert timeline_response.status_code == 200
    categories = {event["category"] for event in timeline_response.json()}
    assert "task" in categories
    assert "handoff" in categories

    task_update_response = client.patch(
        f"/patients/1001/tasks/{task_id}",
        headers=headers,
        json={"status": "completed"},
    )
    assert task_update_response.status_code == 200
    assert task_update_response.json()["status"] == "completed"
    assert task_update_response.json()["sla_status"] == "completed"

    summary_response = client.get("/patients/1001/summary", headers=headers)
    assert summary_response.status_code == 200
    mission_control = summary_response.json()["mission_control"]
    assert mission_control["workflow"]["completed_tasks"] >= 1
    assert mission_control["workflow"]["last_handoff_summary"] == "Night shift handoff"


def test_admin_user_directory_and_invite_management() -> None:
    headers = auth_headers("admin", "AdminPass123!")

    users_response = client.get("/admin/users", headers=headers)
    assert users_response.status_code == 200
    usernames = {user["username"] for user in users_response.json()}
    assert {"admin", "clinician", "analyst"}.issubset(usernames)

    invite_response = client.post(
        "/admin/invites",
        headers=headers,
        json={"role": "analyst", "email": "invitee@example.com", "expires_in_days": 7},
    )
    assert invite_response.status_code == 200
    payload = invite_response.json()
    assert payload["role"] == "analyst"
    assert payload["invite_code"]

    role_update = client.patch(
        "/admin/users/analyst/role",
        headers=headers,
        json={"role": "clinician"},
    )
    assert role_update.status_code == 200
    assert role_update.json()["role"] == "clinician"

    status_update = client.patch(
        "/admin/users/analyst/status",
        headers=headers,
        json={"is_active": False},
    )
    assert status_update.status_code == 200
    assert status_update.json()["is_active"] is False
