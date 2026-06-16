from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Integer, String, Float, DateTime, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailAnalysis(Base):
    __tablename__ = "email_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    history_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Sender / subject
    sender: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    sender_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    body_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extracted URLs (JSON list)
    urls_found: Mapped[Optional[List[Any]]] = mapped_column(JSON, nullable=True)

    # Model scores (0.0 ~ 1.0)
    nlp_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    url_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rule_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Risk classification: normal | suspicious | dangerous
    risk_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Triage status: normal | needs_review | quarantined
    status: Mapped[str] = mapped_column(String(32), default="pending")

    # Action taken on Gmail
    action_taken: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Owner — Gmail account that received this email
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Processing time in milliseconds
    analysis_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # SHAP / feature importance details (JSON)
    model_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now(), nullable=True)


class ProcessedMessage(Base):
    """Deduplication table — tracks already-processed Gmail message IDs."""

    __tablename__ = "processed_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WatchStatus(Base):
    """Stores the current Gmail watch registration state."""

    __tablename__ = "watch_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_address: Mapped[str] = mapped_column(String(255))
    history_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    expiration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
