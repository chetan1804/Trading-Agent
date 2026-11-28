import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "smoke_check.py"
SPEC = importlib.util.spec_from_file_location("smoke_check", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
smoke_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke_check)


def test_smoke_check_accepts_ready_services(monkeypatch) -> None:
    def get_json(url: str) -> tuple[int, dict[str, object]]:
        if url.endswith("/health"):
            return 200, {"status": "ok"}
        if url.endswith("/health/ready"):
            return 200, {"status": "ok", "checks": {}}
        return 200, {"status": "ok", "services": {}}

    def get_text(url: str) -> tuple[int, str]:
        return 200, "ok"

    monkeypatch.setattr(smoke_check, "_get_json", get_json)
    monkeypatch.setattr(smoke_check, "_get_text", get_text)

    assert smoke_check.main() == 0


def test_smoke_check_rejects_unready_backend(monkeypatch) -> None:
    def get_json(url: str) -> tuple[int, dict[str, object]]:
        if url.endswith("/health/ready"):
            return 503, {"status": "unavailable", "checks": {"redis": "unavailable"}}
        if url.endswith("/health"):
            return 200, {"status": "ok"}
        return 200, {"status": "ok"}

    def get_text(url: str) -> tuple[int, str]:
        return 200, "ok"

    monkeypatch.setattr(smoke_check, "_get_json", get_json)
    monkeypatch.setattr(smoke_check, "_get_text", get_text)

    assert smoke_check.main() == 1
