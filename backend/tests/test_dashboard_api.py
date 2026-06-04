"""Integration tests for SOC Dashboard API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import orm


# ── In-memory SQLite for tests ────────────────────────────────────────────────
# StaticPool ensures all sessions share the same in-memory connection so tables
# created in setup_db are visible to the app's dependency-overridden sessions.

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


def _seed_email(db, *, risk_level: str = "dangerous", status: str = "quarantined") -> orm.EmailAnalysis:
    record = orm.EmailAnalysis(
        message_id=f"msg-{risk_level}-{id(risk_level)}",
        sender="attacker@evil.com",
        subject="Urgent verify",
        body_preview="Click here now",
        nlp_score=0.9,
        url_score=0.85,
        rule_score=0.2,
        final_score=0.88,
        risk_level=risk_level,
        status=status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestStats:
    def test_empty_stats(self, client):
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_stats_reflect_seeded_data(self, client):
        db = TestSession()
        _seed_email(db, risk_level="dangerous", status="quarantined")
        _seed_email(db, risk_level="normal", status="normal")
        db.close()

        resp = client.get("/api/dashboard/stats")
        data = resp.json()
        assert data["total"] == 2
        assert data["dangerous"] == 1
        assert data["normal"] == 1
        assert data["quarantined"] == 1


class TestEmailList:
    def test_empty_list(self, client):
        resp = client.get("/api/dashboard/emails")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_seeded(self, client):
        db = TestSession()
        _seed_email(db)
        db.close()

        resp = client.get("/api/dashboard/emails")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_filter_by_risk_level(self, client):
        db = TestSession()
        _seed_email(db, risk_level="dangerous")
        _seed_email(db, risk_level="normal")
        db.close()

        resp = client.get("/api/dashboard/emails?risk_level=dangerous")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["risk_level"] == "dangerous"


class TestEmailDetail:
    def test_get_existing_email(self, client):
        db = TestSession()
        record = _seed_email(db)
        email_id = record.id
        db.close()

        resp = client.get(f"/api/dashboard/emails/{email_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == email_id

    def test_get_nonexistent_email(self, client):
        resp = client.get("/api/dashboard/emails/99999")
        assert resp.status_code == 404


class TestStatusUpdate:
    def test_update_status_to_normal(self, client):
        db = TestSession()
        record = _seed_email(db, status="quarantined")
        email_id = record.id
        db.close()

        resp = client.patch(
            f"/api/dashboard/emails/{email_id}/status",
            json={"status": "normal"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "normal"

    def test_invalid_status_rejected(self, client):
        db = TestSession()
        record = _seed_email(db)
        email_id = record.id
        db.close()

        resp = client.patch(
            f"/api/dashboard/emails/{email_id}/status",
            json={"status": "invalid_value"},
        )
        assert resp.status_code == 422


class TestReactDashboardSupport:
    def test_action_logs_are_derived_from_email_analyses(self, client):
        db = TestSession()
        record = _seed_email(db, risk_level="dangerous", status="quarantined")
        email_id = record.id
        db.close()

        resp = client.get("/api/dashboard/action-logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["id"] == email_id
        assert data[0]["tone"] == "danger"
        assert "Quarantine" in data[0]["action"]

    def test_hourly_counts_returns_24_buckets(self, client):
        db = TestSession()
        _seed_email(db, risk_level="normal", status="normal")
        db.close()

        resp = client.get("/api/dashboard/hourly")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 24
        assert sum(row["total"] for row in data) == 1

    def test_system_health_contract(self, client):
        resp = client.get("/api/dashboard/system-health")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert {item["label"] for item in data["items"]} >= {"Gmail watch", "BERT NLP", "URL 모델"}

    def test_model_performance_contract(self, client):
        resp = client.get("/api/dashboard/model-performance")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["models"]) >= 3
        assert {"name", "accuracy", "f1"} <= set(data["models"][0])
