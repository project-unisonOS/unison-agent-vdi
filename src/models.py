from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class BrowseAction(BaseModel):
    click_selector: Optional[str] = Field(None, description="CSS selector to click")
    wait_for: Optional[str] = Field(None, description="CSS selector to wait for after action")


class BrowseRequest(BaseModel):
    person_id: str
    url: HttpUrl | str
    session_id: Optional[str] = Field(default=None, description="Session/workflow identifier")
    wait_for: Optional[str] = Field(default=None, description="Selector to wait for after navigation")
    actions: List[BrowseAction] = Field(default_factory=list)
    headers: Optional[Dict[str, str]] = None
    telemetry_channel: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.low


class FormField(BaseModel):
    selector: str
    value: str
    type: str = Field(default="text", description="text|password|checkbox|select")


class FormSubmitRequest(BrowseRequest):
    form: List[FormField] = Field(default_factory=list)
    submit_selector: Optional[str] = None


class DownloadRequest(BrowseRequest):
    target_path: Optional[str] = Field(default=None, description="Path relative to workspace/person/session")
    filename: Optional[str] = None


class TaskResult(BaseModel):
    status: str
    detail: Optional[str] = None
    file_ids: List[str] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list, description="Local artifact paths")
    exit_ip: Optional[str] = None
    telemetry: Dict[str, str] = Field(default_factory=dict)
