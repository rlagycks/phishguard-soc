"""Gmail Pub/Sub webhook receiver.

POST /webhook/gmail
  - Verifies the push token in the query parameter.
  - Decodes the base64 Pub/Sub message envelope.
  - Looks up new messages via Gmail history API using per-account credentials.
  - Runs the full analysis pipeline on each new message.
  - Persists results to the database.
"""

import base64
import json
import time
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import orm
from app.models.schemas import PubSubMessage
from app.services import gmail_client, email_parser, ensemble, action_engine

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/webhook", tags=["webhook"])


def _is_duplicate(db: Session, message_id: str) -> bool:
    return db.query(orm.ProcessedMessage).filter_by(message_id=message_id).first() is not None


def _mark_processed(db: Session, message_id: str) -> None:
    db.add(orm.ProcessedMessage(message_id=message_id))
    db.commit()


async def _process_message(
    message_id: str, history_id: str, email_address: str, db: Session
) -> None:
    if _is_duplicate(db, message_id):
        logger.debug("Skipping duplicate message %s", message_id)
        return

    start_ms = int(time.time() * 1000)

    try:
        raw = gmail_client.get_message(message_id, email=email_address)
    except Exception as e:
        logger.error("Failed to fetch Gmail message %s: %s", message_id, e)
        return

    parsed = email_parser.parse_gmail_message(raw)

    result = ensemble.run(parsed)

    end_ms = int(time.time() * 1000)

    action = "skipped"
    try:
        action = action_engine.execute(message_id, result, email=email_address)
    except Exception as e:
        logger.warning("Action engine failed for %s: %s", message_id, e)

    record = orm.EmailAnalysis(
        message_id=message_id,
        history_id=history_id,
        owner_email=email_address,
        received_at=parsed.received_at,
        sender=parsed.sender,
        sender_domain=parsed.sender_domain,
        subject=parsed.subject,
        body_preview=parsed.body_preview,
        urls_found=parsed.urls,
        nlp_score=result.nlp_score,
        url_score=result.url_score,
        rule_score=result.rule_score,
        final_score=result.final_score,
        risk_level=result.risk_level,
        status=action,
        action_taken=action,
        analysis_time_ms=end_ms - start_ms,
        model_details={
            "nlp_top_features": result.nlp_details.top_features,
            "url_details": result.url_details.per_url[:10],
            "rule_details": result.rule_details,
        },
    )
    db.add(record)
    _mark_processed(db, message_id)
    db.commit()

    logger.info(
        "Processed message %s | owner=%s | risk=%s | score=%.3f | action=%s | %dms",
        message_id, email_address, result.risk_level, result.final_score, action, end_ms - start_ms,
    )


@router.post("/gmail")
async def gmail_webhook(
    request: Request,
    token: str = Query(default=""),
    db: Session = Depends(get_db),
):
    if token != settings.WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    body = await request.json()

    message = body.get("message", {})
    data_b64 = message.get("data", "")

    if not data_b64:
        return {"status": "ok"}

    try:
        payload = json.loads(base64.b64decode(data_b64 + "==").decode("utf-8"))
    except Exception as e:
        logger.warning("Failed to decode Pub/Sub payload: %s", e)
        raise HTTPException(status_code=400, detail="Invalid base64 payload")

    email_address = payload.get("emailAddress", "")
    history_id = str(payload.get("historyId", ""))

    if not history_id:
        return {"status": "ok", "reason": "no historyId"}

    # Look up per-account WatchStatus; fall back to any record if no match
    watch = None
    if email_address:
        watch = db.query(orm.WatchStatus).filter_by(email_address=email_address).first()
    if watch is None:
        watch = db.query(orm.WatchStatus).first()

    start_history_id = watch.history_id if watch else history_id

    try:
        new_messages = gmail_client.list_history(start_history_id, email=email_address)
    except Exception as e:
        logger.error("history.list failed for %s: %s", email_address, e)
        new_messages = []

    for msg in new_messages:
        try:
            await _process_message(msg["id"], history_id, email_address, db)
        except Exception as e:
            logger.error("Pipeline error for message %s: %s", msg.get("id"), e)

    # Persist latest historyId for this specific account
    if watch and watch.email_address == email_address:
        watch.history_id = history_id
        db.commit()
    elif email_address:
        account_watch = db.query(orm.WatchStatus).filter_by(email_address=email_address).first()
        if account_watch:
            account_watch.history_id = history_id
        else:
            db.add(orm.WatchStatus(email_address=email_address, history_id=history_id))
        db.commit()
    elif watch:
        watch.history_id = history_id
        db.commit()

    return {"status": "ok", "processed": len(new_messages)}
