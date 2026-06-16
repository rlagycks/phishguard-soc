from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class EmailAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: str
    history_id: str | None
    received_at: datetime | None
    sender: str | None
    sender_domain: str | None
    subject: str | None
    body_preview: str | None
    urls_found: list[Any] | None
    nlp_score: float | None
    url_score: float | None
    rule_score: float | None
    final_score: float | None
    risk_level: str | None
    status: str
    action_taken: str | None
    analysis_time_ms: int | None
    model_details: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime | None


class EmailAnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: str
    received_at: datetime | None
    sender: str | None
    subject: str | None
    final_score: float | None
    risk_level: str | None
    status: str
    created_at: datetime


class DashboardStats(BaseModel):
    total: int
    normal: int
    suspicious: int
    dangerous: int
    quarantined: int
    avg_analysis_ms: float | None
    last_updated: datetime


class StatusUpdate(BaseModel):
    status: str  # normal | needs_review | quarantined


class PubSubMessage(BaseModel):
    """Incoming Pub/Sub push message envelope."""

    message: dict[str, Any]
    subscription: str
