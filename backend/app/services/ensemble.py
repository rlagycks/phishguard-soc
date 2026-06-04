"""Ensemble Risk Scoring Engine.

Final Risk Score = w_email × nlp_score + w_url × url_score + w_rule × rule_score

Thresholds (from config):
  0.00 – 0.39  →  normal
  0.40 – 0.69  →  suspicious
  0.70 – 1.00  →  dangerous
"""

from dataclasses import dataclass
from app.config import get_settings
from app.services.email_parser import ParsedEmail
from app.services.nlp_model import score as nlp_score, NLPResult
from app.services.url_model import score_urls, URLModelResult

settings = get_settings()


@dataclass
class EnsembleResult:
    nlp_score: float
    url_score: float
    rule_score: float
    final_score: float
    risk_level: str     # normal | suspicious | dangerous
    nlp_details: NLPResult
    url_details: URLModelResult
    rule_details: dict


def _rule_based_score(parsed: ParsedEmail) -> tuple[float, dict]:
    """Header and sender heuristics."""
    score = 0.0
    details: dict = {}

    # Sender domain mismatch heuristic (basic: free mail on "urgent" subject)
    subject_lower = parsed.subject.lower()
    urgent_words = ["urgent", "긴급", "즉시", "immediately", "important"]
    if any(w in subject_lower for w in urgent_words):
        score += 0.2
        details["urgent_subject"] = True

    # No-reply or spoofed looking senders
    if "noreply" in parsed.sender.lower() or "no-reply" in parsed.sender.lower():
        score += 0.05
        details["noreply_sender"] = True

    # Many URLs in body is suspicious
    url_count = len(parsed.urls)
    if url_count > 5:
        score += 0.15
        details["high_url_count"] = url_count

    return min(1.0, score), details


def _classify(score: float) -> str:
    if score >= settings.DANGEROUS_THRESHOLD:
        return "dangerous"
    if score >= settings.SUSPICIOUS_THRESHOLD:
        return "suspicious"
    return "normal"


def run(parsed: ParsedEmail) -> EnsembleResult:
    nlp_result = nlp_score(parsed.subject, parsed.body_text)
    url_result = score_urls(parsed.urls)
    rule_s, rule_details = _rule_based_score(parsed)

    # Use max URL score (most dangerous URL drives the risk)
    url_s = url_result.max_score

    final = (
        settings.EMAIL_WEIGHT * nlp_result.score
        + settings.URL_WEIGHT * url_s
        + settings.RULE_WEIGHT * rule_s
    )
    final = round(min(1.0, final), 4)

    return EnsembleResult(
        nlp_score=round(nlp_result.score, 4),
        url_score=round(url_s, 4),
        rule_score=round(rule_s, 4),
        final_score=final,
        risk_level=_classify(final),
        nlp_details=nlp_result,
        url_details=url_result,
        rule_details=rule_details,
    )
