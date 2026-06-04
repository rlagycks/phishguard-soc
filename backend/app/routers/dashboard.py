"""SOC Dashboard REST API endpoints."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import orm
from app.models.schemas import (
    DashboardStats,
    EmailAnalysisRead,
    EmailAnalysisSummary,
    StatusUpdate,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DbDep = Annotated[Session, Depends(get_db)]
settings = get_settings()


@router.get("/stats", response_model=DashboardStats)
def get_stats(db: DbDep):
    total = db.query(orm.EmailAnalysis).count()
    normal = db.query(orm.EmailAnalysis).filter(orm.EmailAnalysis.risk_level == "normal").count()
    suspicious = db.query(orm.EmailAnalysis).filter(orm.EmailAnalysis.risk_level == "suspicious").count()
    dangerous = db.query(orm.EmailAnalysis).filter(orm.EmailAnalysis.risk_level == "dangerous").count()
    quarantined = db.query(orm.EmailAnalysis).filter(orm.EmailAnalysis.status == "quarantined").count()

    avg_ms = db.query(func.avg(orm.EmailAnalysis.analysis_time_ms)).scalar()

    return DashboardStats(
        total=total,
        normal=normal,
        suspicious=suspicious,
        dangerous=dangerous,
        quarantined=quarantined,
        avg_analysis_ms=round(avg_ms, 1) if avg_ms else None,
        last_updated=datetime.now(timezone.utc),
    )


@router.get("/emails", response_model=list[EmailAnalysisSummary])
def list_emails(
    db: DbDep,
    risk_level: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
):
    q = db.query(orm.EmailAnalysis)
    if risk_level:
        q = q.filter(orm.EmailAnalysis.risk_level == risk_level)
    if status:
        q = q.filter(orm.EmailAnalysis.status == status)
    return q.order_by(orm.EmailAnalysis.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/emails/recent", response_model=list[EmailAnalysisSummary])
def recent_emails(db: DbDep, limit: int = Query(default=20, le=100)):
    return (
        db.query(orm.EmailAnalysis)
        .order_by(orm.EmailAnalysis.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/emails/{email_id}", response_model=EmailAnalysisRead)
def get_email(email_id: int, db: DbDep):
    record = db.get(orm.EmailAnalysis, email_id)
    if not record:
        raise HTTPException(status_code=404, detail="Email analysis not found")
    return record


@router.patch("/emails/{email_id}/status", response_model=EmailAnalysisRead)
def update_status(email_id: int, payload: StatusUpdate, db: DbDep):
    allowed = {"normal", "needs_review", "quarantined"}
    if payload.status not in allowed:
        raise HTTPException(status_code=422, detail=f"status must be one of {allowed}")

    record = db.get(orm.EmailAnalysis, email_id)
    if not record:
        raise HTTPException(status_code=404, detail="Email analysis not found")

    record.status = payload.status
    db.commit()
    db.refresh(record)
    return record


@router.get("/daily", response_model=list[dict])
def daily_counts(db: DbDep, days: int = Query(default=7, le=30)):
    """Returns per-day detection counts for the last N days."""
    rows = (
        db.query(
            func.date(orm.EmailAnalysis.created_at).label("day"),
            func.count().label("total"),
            func.sum(
                cast((orm.EmailAnalysis.risk_level == "dangerous"), Integer)
            ).label("dangerous"),
        )
        .group_by("day")
        .order_by("day")
        .limit(days)
        .all()
    )
    return [{"day": str(r.day), "total": r.total, "dangerous": r.dangerous or 0} for r in rows]


@router.get("/action-logs", response_model=list[dict])
def action_logs(db: DbDep, limit: int = Query(default=80, le=200)):
    rows = (
        db.query(orm.EmailAnalysis)
        .order_by(orm.EmailAnalysis.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "message_id": row.message_id,
            "ts": row.updated_at or row.created_at,
            "subject": row.subject or "(제목 없음)",
            "sender": row.sender or "unknown",
            "status": row.status,
            "tone": _tone_for_status(row.status, row.risk_level),
            "action": _action_label(row.status, row.action_taken),
            "final_score": row.final_score or 0.0,
            "analysis_time_ms": row.analysis_time_ms,
        }
        for row in rows
    ]


@router.get("/hourly", response_model=list[dict])
def hourly_counts(db: DbDep):
    rows = db.query(orm.EmailAnalysis).all()
    buckets = {
        hour: {"hour": hour, "total": 0, "quarantined": 0, "needs_review": 0, "normal": 0}
        for hour in range(24)
    }
    for row in rows:
        dt = row.received_at or row.created_at
        hour = dt.hour
        bucket = buckets[hour]
        bucket["total"] += 1
        if row.status == "quarantined":
            bucket["quarantined"] += 1
        elif row.status in {"needs_review", "review"}:
            bucket["needs_review"] += 1
        else:
            bucket["normal"] += 1
    return list(buckets.values())


@router.get("/system-health", response_model=dict)
def system_health(db: DbDep):
    watch = db.query(orm.WatchStatus).first()
    avg_ms = db.query(func.avg(orm.EmailAnalysis.analysis_time_ms)).scalar()
    return {
        "items": [
            {
                "label": "Gmail watch",
                "value": "활성" if watch else "미설정",
                "detail": _watch_detail(watch),
                "tone": "ok" if watch else "warn",
            },
            {
                "label": "Pub/Sub 구독",
                "value": "연결 대기" if not settings.PUBSUB_TOPIC else "연결됨",
                "detail": settings.PUBSUB_TOPIC.rsplit("/", 1)[-1] if settings.PUBSUB_TOPIC else "topic 없음",
                "tone": "ok" if settings.PUBSUB_TOPIC else "warn",
            },
            {
                "label": "BERT NLP",
                "value": "로드 대상",
                "detail": settings.NLP_MODEL_PATH,
                "tone": "ok",
            },
            {
                "label": "URL 모델",
                "value": "로드 대상",
                "detail": settings.URL_MODEL_PATH,
                "tone": "ok",
            },
            {
                "label": "평균 분석",
                "value": f"{avg_ms / 1000:.1f}s" if avg_ms else "데이터 없음",
                "detail": "E2E",
                "tone": "ok" if avg_ms else "warn",
            },
        ]
    }


@router.get("/model-performance", response_model=dict)
def model_performance():
    """Return presentation metrics used by the dashboard stats screen.

    These values are static until the training scripts persist evaluation
    results in a machine-readable artifact.
    """
    return {
        "models": [
            {"name": "이메일 본문 (BERT)", "accuracy": 97.2, "f1": 0.971},
            {"name": "URL (XGBoost)", "accuracy": 95.8, "f1": 0.956},
            {"name": "가중합 앙상블", "accuracy": 98.4, "f1": 0.982},
            {"name": "Stacking 앙상블", "accuracy": 98.9, "f1": 0.987},
        ]
    }


def _tone_for_status(status: str, risk_level: str | None) -> str:
    if status == "quarantined" or risk_level == "dangerous":
        return "danger"
    if status in {"needs_review", "review"} or risk_level == "suspicious":
        return "warn"
    return "ok"


def _action_label(status: str, action_taken: str | None) -> str:
    action = action_taken or status
    labels = {
        "quarantined": "Quarantine label 적용 + INBOX 제거",
        "needs_review": "Needs-Review label 부여",
        "review": "Needs-Review label 부여",
        "normal": "INBOX 유지 (조치 없음)",
        "pending": "분석 결과 대기",
        "skipped": "Gmail 조치 실패 또는 생략",
    }
    return labels.get(action, action)


def _watch_detail(watch: orm.WatchStatus | None) -> str:
    if not watch:
        return "watch 없음"
    if watch.expiration_ms:
        return f"expires {watch.expiration_ms}"
    return watch.history_id or "history 없음"
