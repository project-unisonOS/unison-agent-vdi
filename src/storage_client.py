from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path
from typing import Dict, Optional

import httpx


class StorageClient:
    def __init__(self, base_url: Optional[str], token: Optional[str]) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.token = token

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def upload_file(self, file_path: Path, metadata: Dict[str, str]) -> Optional[str]:
        """Uploads a file via the storage KV API as a stopgap until a dedicated files endpoint exists."""
        if not self.base_url or not file_path.exists():
            return None
        artifact_id = metadata.get("artifact_id") or str(uuid.uuid4())
        payload = {
            "value": {
                "artifact_id": artifact_id,
                "metadata": metadata,
                "filename": file_path.name,
                "content_b64": base64.b64encode(file_path.read_bytes()).decode(),
            }
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{self.base_url}/kv/vdi_artifacts/{artifact_id}", json=payload, headers=self._headers()
            )
            resp.raise_for_status()
        return artifact_id

    async def audit(self, event: Dict[str, str]) -> None:
        if not self.base_url:
            return
        payload = {"value": event}
        audit_key = event.get("action_id") or str(uuid.uuid4())
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.put(f"{self.base_url}/kv/vdi_audit/{audit_key}", json=payload, headers=self._headers())
            except Exception:
                return
