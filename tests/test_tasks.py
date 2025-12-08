import os

os.environ.setdefault("VDI_FAKE_BROWSER", "true")
os.environ.setdefault("VDI_REQUIRE_AUTH", "false")
os.environ.setdefault("VDI_REQUIRE_VPN", "false")
os.environ.setdefault("VDI_WORKSPACE_PATH", "/tmp/vdi-workspace")

from fastapi.testclient import TestClient  # noqa: E402

from src.main import app  # noqa: E402


client = TestClient(app)


def test_browse_fake_runner():
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
