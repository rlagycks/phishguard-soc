"""URL-based phishing risk scorer.

Architecture:
  - Main: URLClassifier wrapping RandomForest/XGBoost loaded from url_model.pkl
  - Fallback: heuristic scoring from feature values when no model is present

Public API (mirrors NLP PhishingClassifier pattern for consistent interfaces):
    clf = URLClassifier(settings.URL_MODEL_PATH)
    result = clf.score_urls(urls)  # → URLModelResult

Module-level convenience (for ensemble.py backward compatibility):
    score_urls(urls)  →  URLModelResult  (delegates to singleton)
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import numpy as np

from app.config import get_settings
from app.services.url_extractor import URLFeatures, extract_features

# Known legitimate email service providers (ESPs) — tracking/click URLs from these
# domains are legitimate by definition and should never score high.
# Match on the registrable domain (last two labels) to cover all subdomains.
_KNOWN_ESP_DOMAINS = {
    # Newsletter / transactional senders
    "stackoverflow.email",
    "sendgrid.net",
    "mailchimp.com",
    "list-manage.com",       # Mailchimp click-tracking
    "hubspot.com",
    "hubspotlinks.com",
    "hs-email.net",
    "constantcontact.com",
    "mandrillapp.com",
    "postmarkapp.com",
    "mailgun.org",
    "amazonses.com",
    "sailthru.com",
    "klaviyo.com",
    "marketo.com",
    "eloqua.com",
    "pardot.com",
    "createsend.com",
    "cmail19.com",           # Campaign Monitor
    "cmail20.com",
    "exacttarget.com",       # Salesforce Marketing Cloud
    "salesforceiq.com",
    "intercom-mail.com",
    "customer.io",
    "drip.com",
    "activecampaign.com",
    # Major transactional
    "mailjet.com",
    "sendinblue.com",
    "brevo.com",
    "sparkpost.com",
}


def _is_known_esp(url: str) -> bool:
    """Return True if the URL belongs to a known legitimate ESP/mailing domain."""
    try:
        hostname = urlparse(url).hostname or ""
        parts = hostname.lower().split(".")
        if len(parts) >= 2:
            registrable = ".".join(parts[-2:])
            return registrable in _KNOWN_ESP_DOMAINS
    except Exception:
        pass
    return False

settings = get_settings()

Backend = Literal["sklearn", "heuristic"]


@dataclass
class URLModelResult:
    max_score: float      # highest risk score across all URLs
    avg_score: float      # average risk across all URLs
    per_url: list[dict]   # [{url, score, is_https, is_ip, suspicious_tld, phishing_keywords}]
    backend: str          # "sklearn" | "heuristic"


class URLClassifier:
    """Class-based URL phishing risk scorer.

    Mirrors PhishingClassifier (NLP) so both AI components share the same
    instantiation pattern and can be extended or swapped uniformly.

    Usage:
        clf = URLClassifier("models/url_model.pkl")
        result = clf.score_urls(["http://evil.xyz/login?verify=1"])
        # → URLModelResult(max_score=0.91, avg_score=0.91, per_url=[...], backend="sklearn")
    """

    def __init__(self, model_path: str | Path) -> None:
        self._model_path = Path(model_path)
        self._model = None
        self._backend: Backend = "heuristic"
        self._try_load()

    def _try_load(self) -> None:
        if self._model_path.exists():
            try:
                with open(self._model_path, "rb") as f:
                    self._model = pickle.load(f)
                self._backend = "sklearn"
            except Exception:
                self._model = None
                self._backend = "heuristic"

    # ── Public API ──────────────────────────────────────────────────────────────

    def score_urls(self, urls: list[str]) -> URLModelResult:
        """Score a list of URLs and return aggregate risk.

        Returns URLModelResult with per-URL breakdown and max/avg scores.
        max_score (not avg) is used by the ensemble to surface the worst URL.
        """
        if not urls:
            return URLModelResult(
                max_score=0.0, avg_score=0.0, per_url=[], backend=self._backend
            )

        results = [self._score_one(url) for url in urls]
        scores = [r["score"] for r in results]
        return URLModelResult(
            max_score=max(scores),
            avg_score=float(np.mean(scores)),
            per_url=results,
            backend=self._backend,
        )

    def score_single(self, url: str) -> dict:
        """Score a single URL. Returns the same dict structure as per_url entries."""
        return self._score_one(url)

    # ── Internals ───────────────────────────────────────────────────────────────

    def _score_one(self, url: str) -> dict:
        if _is_known_esp(url):
            return {
                "url": url,
                "score": 0.05,
                "is_https": True,
                "is_ip": False,
                "suspicious_tld": False,
                "phishing_keywords": 0,
            }

        features = extract_features(url)
        if self._model is not None:
            try:
                vec = np.array(features.to_list()).reshape(1, -1)
                proba = self._model.predict_proba(vec)
                score = float(proba[0][1])
            except Exception:
                score = _heuristic_score(features)
        else:
            score = _heuristic_score(features)

        return {
            "url": url,
            "score": score,
            "is_https": features.is_https,
            "is_ip": features.is_ip_address,
            "suspicious_tld": features.suspicious_tld,
            "phishing_keywords": features.phishing_keyword_count,
        }


def _heuristic_score(f: URLFeatures) -> float:
    """Rule-based fallback score when no trained model is available."""
    score = 0.0
    if f.is_ip_address:
        score += 0.30
    if not f.is_https:
        score += 0.15
    if f.suspicious_tld:
        score += 0.20
    if f.shortener:
        score += 0.15
    if f.at_symbol:
        score += 0.15
    if f.phishing_keyword_count >= 2:
        score += 0.10 * f.phishing_keyword_count
    if f.url_length > 75:
        score += 0.10
    return min(1.0, score)


# ── Module-level singleton + convenience function ────────────────────────────

_classifier: URLClassifier | None = None


def _get_classifier() -> URLClassifier:
    global _classifier
    if _classifier is None:
        _classifier = URLClassifier(settings.URL_MODEL_PATH)
    return _classifier


def score_urls(urls: list[str]) -> URLModelResult:
    """Module-level convenience — compatible with existing ensemble.py calls."""
    return _get_classifier().score_urls(urls)
