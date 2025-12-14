import os

os.environ.setdefault("VDI_FAKE_BROWSER", "true")
os.environ.setdefault("VDI_REQUIRE_AUTH", "false")
os.environ.setdefault("VDI_REQUIRE_VPN", "false")
os.environ.setdefault("VDI_WORKSPACE_PATH", "/tmp/vdi-workspace")

from pathlib import Path

from fastapi.testclient import TestClient  # noqa: E402

from src.main import app  # noqa: E402


def test_browse_fake_runner():
    with TestClient(app) as client:
        resp = client.post(
            "/tasks/browse",
            json={
                "person_id": "person-1",
                "url": "https://example.com",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["telemetry"]["url"] == "https://example.com"


def test_download_fake_runner_creates_artifact():
    with TestClient(app) as client:
        resp = client.post(
            "/tasks/download",
            json={
                "person_id": "person-2",
                "url": "https://example.com/file",
                "filename": "file.txt",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["artifacts"], "expected artifact path"


def test_domain_allowlist_blocks_request():
    os.environ["VDI_DOMAIN_ALLOWLIST"] = "example.com"
    os.environ.pop("VDI_DOMAIN_DENYLIST", None)
    with TestClient(app) as client:
        resp = client.post(
            "/tasks/browse",
            json={
                "person_id": "person-3",
                "url": "https://not-example.com",
            },
        )
        assert resp.status_code == 403


def test_domain_denylist_blocks_request():
    os.environ.pop("VDI_DOMAIN_ALLOWLIST", None)
    os.environ["VDI_DOMAIN_DENYLIST"] = "example.com"
    with TestClient(app) as client:
        resp = client.post(
            "/tasks/browse",
            json={
                "person_id": "person-4",
                "url": "https://example.com",
            },
        )
        assert resp.status_code == 403


def test_domain_wildcard_allows_subdomain():
    os.environ["VDI_DOMAIN_ALLOWLIST"] = "*.example.com"
    os.environ.pop("VDI_DOMAIN_DENYLIST", None)
    with TestClient(app) as client:
        resp = client.post(
            "/tasks/browse",
            json={
                "person_id": "person-5",
                "url": "https://sub.example.com",
            },
        )
        assert resp.status_code == 200


def test_workspace_cleanup_removes_session_workspace_and_clears_artifacts():
    os.environ.pop("VDI_DOMAIN_ALLOWLIST", None)
    os.environ.pop("VDI_DOMAIN_DENYLIST", None)
    os.environ["VDI_CLEAN_WORKSPACE"] = "true"
    session_id = "session-clean-1"
    workspace = Path(os.environ["VDI_WORKSPACE_PATH"]) / "person-6" / session_id
    if workspace.exists():
        # Best-effort cleanup from prior runs.
        for _ in range(2):
            try:
                import shutil

                shutil.rmtree(workspace, ignore_errors=True)
            except Exception:
                pass
    with TestClient(app) as client:
        resp = client.post(
            "/tasks/download",
            json={
                "person_id": "person-6",
                "session_id": session_id,
                "url": "https://example.com/file",
                "filename": "file.txt",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["artifacts"] == []
        assert body["telemetry"]["workspace_cleaned"] == "true"
    assert not workspace.exists()
