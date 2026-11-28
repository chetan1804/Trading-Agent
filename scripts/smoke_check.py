from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _get_json(url: str) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return int(response.status), payload
    except urllib.error.HTTPError as error:
        payload = json.loads(error.read().decode("utf-8"))
        return int(error.code), payload


def _get_text(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return int(response.status), response.read().decode("utf-8").strip()
    except urllib.error.HTTPError as error:
        return int(error.code), error.read().decode("utf-8").strip()


def main() -> int:
    api_base = os.getenv("SMOKE_API_URL", "http://localhost:8001").rstrip("/")
    frontend_base = os.getenv("SMOKE_FRONTEND_URL", "http://localhost:5173").rstrip("/")

    checks = [
        ("backend-liveness", f"{api_base}/health", "json"),
        ("backend-readiness", f"{api_base}/health/ready", "json"),
        ("deployment-status", f"{api_base}/api/deployment/status", "json"),
        ("frontend-health", f"{frontend_base}/health", "text"),
    ]
    failures: list[str] = []

    for name, url, response_type in checks:
        try:
            if response_type == "json":
                status_code, payload = _get_json(url)
                if status_code != 200:
                    failures.append(f"{name}: HTTP {status_code}")
                    continue
                if name == "backend-liveness" and payload.get("status") != "ok":
                    failures.append(f"{name}: unexpected response")
                elif name == "backend-readiness" and payload.get("status") != "ok":
                    failures.append(f"{name}: {payload.get('checks', {})}")
                elif name == "deployment-status":
                    if payload.get("status") not in {"ok", "degraded"}:
                        failures.append(f"{name}: unexpected response")
                    elif payload.get("status") != "ok":
                        failures.append(f"{name}: deployment is degraded")
            else:
                status_code, payload = _get_text(url)
                if status_code != 200 or payload != "ok":
                    failures.append(f"{name}: HTTP {status_code}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            failures.append(f"{name}: {type(error).__name__}")

    if failures:
        print("Smoke check failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1

    print("Smoke check passed: backend and frontend are ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
