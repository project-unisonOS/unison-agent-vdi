from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Dict, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .browser import BrowserRunner, FakeBrowserRunner, PlaywrightBrowserRunner
from .models import BrowseRequest, DownloadRequest, FormSubmitRequest, TaskResult
from .storage_client import StorageClient
from .vpn import vpn_ip, vpn_ready

VDI_PORT = int(os.environ.get("VDI_SERVICE_PORT", "8083"))
EXPERIENCE_RENDERER_URL = os.environ.get("EXPERIENCE_RENDERER_URL")
INTENT_GRAPH_URL = os.environ.get("INTENT_GRAPH_URL")
VPN_IP_ECHO_URL = os.environ.get("VPN_IP_ECHO_URL")
VDI_SERVICE_TOKEN = os.environ.get("VDI_SERVICE_TOKEN")
VDI_REQUIRE_AUTH = os.environ.get("VDI_REQUIRE_AUTH", "true").lower() == "true"
VDI_WORKSPACE_PATH = Path(os.environ.get("VDI_WORKSPACE_PATH", "/workspace"))
STORAGE_URL = os.environ.get("STORAGE_URL")
STORAGE_TOKEN = os.environ.get("STORAGE_TOKEN")
USE_FAKE_BROWSER = os.environ.get("VDI_FAKE_BROWSER", "false").lower() == "true"

app = FastAPI(title="unison-agent-vdi", version="0.2.0")


def _resolve_workspace_path() -> Path:
    candidate = Path(os.environ.get("VDI_WORKSPACE_PATH", str(VDI_WORKSPACE_PATH)))
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except PermissionError:
        fallback = Path("/tmp/vdi-workspace")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _workspace_base() -> Path:
    return getattr(app.state, "workspace_path", VDI_WORKSPACE_PATH)


def _ensure_workspace(base: Path, person_id: str, session_id: Optional[str]) -> Path:
    sid = session_id or str(uuid.uuid4())
    path = base / person_id / sid
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_browser_runner() -> BrowserRunner:
    return app.state.browser_runner


def get_storage_client() -> StorageClient:
    return app.state.storage_client


async def _ping(url: Optional[str]) -> bool:
    if not url:
        return True
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        return True
    except Exception:
        return False


async def _require_auth(request: Request) -> None:
    if not VDI_REQUIRE_AUTH or not VDI_SERVICE_TOKEN:
        return
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if token != VDI_SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


async def _require_vpn() -> None:
    ready = await vpn_ready()
    if not ready:
        raise HTTPException(status_code=503, detail="vpn_unavailable")


@app.on_event("startup")
async def startup_event() -> None:
    use_fake = os.environ.get("VDI_FAKE_BROWSER", "false").lower() == "true"
    globals()["USE_FAKE_BROWSER"] = use_fake
    if use_fake:
        runner: BrowserRunner = FakeBrowserRunner()
    else:
        try:
            runner = PlaywrightBrowserRunner()
        except Exception:
            runner = FakeBrowserRunner()
    app.state.browser_runner = runner
    app.state.storage_client = StorageClient(STORAGE_URL, STORAGE_TOKEN)
    resolved = _resolve_workspace_path()
    app.state.workspace_path = resolved
    globals()["VDI_WORKSPACE_PATH"] = resolved


@app.on_event("shutdown")
async def shutdown_event() -> None:
    runner: BrowserRunner = app.state.browser_runner
    if runner:
        await runner.close()


@app.get("/healthz")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def ready() -> Dict[str, object]:
    renderer_ok = await _ping(f"{EXPERIENCE_RENDERER_URL}/readyz" if EXPERIENCE_RENDERER_URL else None)
    intent_ok = await _ping(f"{INTENT_GRAPH_URL}/health" if INTENT_GRAPH_URL else None)
    vpn_ok = await vpn_ready()
    return {
        "status": "ok" if renderer_ok and intent_ok and vpn_ok else "degraded",
        "renderer": renderer_ok,
        "intent_graph": intent_ok,
        "vpn": vpn_ok,
    }


@app.post("/tasks/browse", response_model=TaskResult)
async def browse_task(
    request: BrowseRequest,
    browser: BrowserRunner = Depends(get_browser_runner),
    storage: StorageClient = Depends(get_storage_client),
    _: None = Depends(_require_auth),
    __: None = Depends(_require_vpn),
) -> TaskResult:
    workspace = _ensure_workspace(VDI_WORKSPACE_PATH, request.person_id, request.session_id)
    result = await browser.browse(request, workspace)
    exit_ip = await vpn_ip(VPN_IP_ECHO_URL)
    await _audit(storage, request.person_id, "browse", request.url, result.status)
    result.exit_ip = exit_ip
    return result


@app.post("/tasks/form-submit", response_model=TaskResult)
async def form_submit_task(
    request: FormSubmitRequest,
    browser: BrowserRunner = Depends(get_browser_runner),
    storage: StorageClient = Depends(get_storage_client),
    _: None = Depends(_require_auth),
    __: None = Depends(_require_vpn),
) -> TaskResult:
    workspace = _ensure_workspace(VDI_WORKSPACE_PATH, request.person_id, request.session_id)
    result = await browser.submit_form(request, workspace)
    exit_ip = await vpn_ip(VPN_IP_ECHO_URL)
    await _audit(storage, request.person_id, "form_submit", request.url, result.status)
    result.exit_ip = exit_ip
    return result


@app.post("/tasks/download", response_model=TaskResult)
async def download_task(
    request: DownloadRequest,
    browser: BrowserRunner = Depends(get_browser_runner),
    storage: StorageClient = Depends(get_storage_client),
    _: None = Depends(_require_auth),
    __: None = Depends(_require_vpn),
) -> TaskResult:
    workspace = _ensure_workspace(VDI_WORKSPACE_PATH, request.person_id, request.session_id)
    result = await browser.download(request, workspace)
    stored_ids = []
    for artifact in result.artifacts:
        stored = await storage.upload_file(
            Path(artifact),
            metadata={
                "person_id": request.person_id,
                "session_id": request.session_id or "",
                "source_url": str(request.url),
                "artifact_id": Path(artifact).name,
            },
        )
        if stored:
            stored_ids.append(stored)
    result.file_ids = stored_ids
    exit_ip = await vpn_ip(VPN_IP_ECHO_URL)
    await _audit(storage, request.person_id, "download", request.url, result.status, stored_ids)
    result.exit_ip = exit_ip
    return result


@app.get("/")
async def root() -> Dict[str, str]:
    return {"service": "unison-agent-vdi", "port": str(VDI_PORT)}


async def _audit(
    storage: StorageClient,
    person_id: str,
    action: str,
    target: str,
    status: str,
    files: Optional[list[str]] = None,
) -> None:
    event = {
        "action_id": str(uuid.uuid4()),
        "person_id": person_id,
        "action": action,
        "target": str(target),
        "status": status,
        "files": files or [],
    }
    await storage.audit(event)
