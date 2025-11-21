from __future__ import annotations

import os
from typing import Dict, Optional

import httpx
from fastapi import FastAPI

VDI_PORT = int(os.environ.get("VDI_SERVICE_PORT", "8083"))
EXPERIENCE_RENDERER_URL = os.environ.get("EXPERIENCE_RENDERER_URL")
INTENT_GRAPH_URL = os.environ.get("INTENT_GRAPH_URL")

app = FastAPI(title="unison-agent-vdi", version="0.1.0")


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


@app.get("/healthz")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def ready() -> Dict[str, object]:
    renderer_ok = await _ping(f"{EXPERIENCE_RENDERER_URL}/readyz" if EXPERIENCE_RENDERER_URL else None)
    intent_ok = await _ping(f"{INTENT_GRAPH_URL}/health" if INTENT_GRAPH_URL else None)
    return {
        "status": "ok" if renderer_ok and intent_ok else "degraded",
        "renderer": renderer_ok,
        "intent_graph": intent_ok,
    }


@app.get("/")
async def root() -> Dict[str, str]:
    return {"service": "unison-agent-vdi", "port": str(VDI_PORT)}
