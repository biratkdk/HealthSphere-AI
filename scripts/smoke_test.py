from __future__ import annotations

import argparse

import httpx


def login(base_url: str, username: str, password: str) -> str:
    response = httpx.post(
        f"{base_url.rstrip('/')}/auth/token",
        data={"username": username, "password": password},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def run(base_url: str, username: str | None = None, password: str | None = None) -> int:
    endpoints = [
        "/auth/providers",
        "/health/live",
        "/health/ready",
        "/metrics",
    ]

    for endpoint in endpoints:
        response = httpx.get(f"{base_url.rstrip('/')}{endpoint}", timeout=5)
        print(f"{endpoint}: {response.status_code}")
        if response.status_code >= 400:
            return 1

    headers = {}
    if username and password:
        token = login(base_url, username, password)
        headers["Authorization"] = f"Bearer {token}"

    protected_endpoints = [
        "/events/stream-token",
        "/patients",
        "/patients/1001/summary",
        "/alerts",
        "/analytics/overview",
        "/notifications",
        "/reports/jobs",
    ]

    for endpoint in protected_endpoints:
        response = httpx.get(f"{base_url.rstrip('/')}{endpoint}", timeout=5, headers=headers)
        print(f"{endpoint}: {response.status_code}")
        if response.status_code >= 400:
            return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a lightweight API smoke test.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--username", default="clinician")
    parser.add_argument("--password", default="ClinicianPass123!")
    args = parser.parse_args()
    raise SystemExit(run(args.base_url, args.username, args.password))
