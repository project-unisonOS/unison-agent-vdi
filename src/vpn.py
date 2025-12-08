from __future__ import annotations

import os
from typing import Optional

import httpx

VPN_HEALTH_URL = os.getenv("VPN_HEALTH_URL")
VPN_REQUIRE = os.getenv("VDI_REQUIRE_VPN", "true").lower() == "true"


async def vpn_ready() -> bool:
    if not VPN_REQUIRE:
        return True
    if not VPN_HEALTH_URL:
        return True
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(VPN_HEALTH_URL)
            if resp.status_code >= 500:
                return False
            data = resp.json()
            ready = data.get("ready")
            if isinstance(ready, bool):
                return ready
            return data.get("status") == "ok"
    except Exception:
        return False


async def vpn_ip(ip_endpoint: Optional[str]) -> Optional[str]:
    if not ip_endpoint:
        return None
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(ip_endpoint)
            resp.raise_for_status()
            return resp.text.strip()
    except Exception:
        return None
