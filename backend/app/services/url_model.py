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
# Well-known legitimate domains — training data contains no bare-domain (url_len=domain_len,
# path=0, subdomain=0) legitimate examples, so XGBoost incorrectly scores these as phishing.
# Checked on the registrable domain (last two labels) so subdomain attacks aren't bypassed.
_KNOWN_LEGIT_DOMAINS = {
    # Major tech / search
    "google.com", "amazon.com", "microsoft.com", "apple.com",
    "meta.com", "facebook.com", "twitter.com", "x.com",
    "youtube.com", "netflix.com", "spotify.com", "twitch.tv",
    "instagram.com", "linkedin.com", "reddit.com", "tiktok.com",
    "snapchat.com", "pinterest.com", "tumblr.com", "discord.com",
    "whatsapp.com", "telegram.org", "signal.org", "zoom.us",
    "bing.com", "yahoo.com", "duckduckgo.com", "baidu.com",
    "naver.com", "daum.net", "kakao.com",
    # Dev / cloud / infra
    "github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com",
    "npmjs.com", "pypi.org", "crates.io", "rubygems.org",
    "docker.com", "kubernetes.io", "terraform.io",
    "cloudflare.com", "fastly.com", "akamai.com",
    "digitalocean.com", "linode.com", "vultr.com",
    "heroku.com", "vercel.com", "netlify.com", "railway.app",
    "replit.com", "codepen.io", "jsfiddle.net",
    "aws.amazon.com",  # registrable = amazon.com (already covered)
    # Google properties (registrable = google.com)
    "mail.google.com", "drive.google.com", "docs.google.com",
    "cloud.google.com", "console.cloud.google.com",
    # Microsoft properties (registrable = microsoft.com or live.com)
    "outlook.com", "live.com", "hotmail.com", "office.com",
    "azure.com", "onedrive.live.com",
    # News / media
    "nytimes.com", "bbc.com", "bbc.co.uk", "cnn.com",
    "theguardian.com", "washingtonpost.com", "reuters.com",
    "bloomberg.com", "wsj.com", "forbes.com", "techcrunch.com",
    "wired.com", "theverge.com", "arstechnica.com", "engadget.com",
    "medium.com", "substack.com",
    # Finance / payments
    "paypal.com", "stripe.com", "squareup.com", "square.com",
    "chase.com", "bankofamerica.com", "wellsfargo.com", "citibank.com",
    "citi.com", "americanexpress.com", "amex.com",
    "visa.com", "mastercard.com", "discover.com",
    "coinbase.com", "kraken.com", "binance.com",
    "fidelity.com", "schwab.com", "vanguard.com", "etrade.com",
    # E-commerce / retail
    "ebay.com", "etsy.com", "shopify.com", "shopify.dev",
    "walmart.com", "target.com", "bestbuy.com", "costco.com",
    "ikea.com", "aliexpress.com", "alibaba.com",
    # Productivity / SaaS
    "notion.so", "trello.com", "asana.com", "jira.atlassian.com",
    "atlassian.com", "confluence.atlassian.com", "slack.com",
    "figma.com", "canva.com", "adobe.com", "dropbox.com",
    "box.com", "salesforce.com", "hubspot.com", "zendesk.com",
    # Education / reference
    "wikipedia.org", "wikimedia.org",
    "coursera.org", "udemy.com", "edx.org", "khanacademy.org",
    "mit.edu", "stanford.edu", "harvard.edu",
    # Hosting / domain registrars
    "godaddy.com", "namecheap.com", "cloudflare.com",
    "wordpress.com", "wordpress.org", "wix.com", "squarespace.com",
    # Security / antivirus
    "virustotal.com", "shodan.io", "haveibeenpwned.com",
    # Korean major services
    "naver.com", "kakao.com", "daum.net", "tistory.com",
    "coupang.com", "11st.co.kr", "gmarket.co.kr", "auction.co.kr",
    "samsung.com", "lg.com", "sk.com", "kt.com",
    # Other well-known
    "twilio.com", "sendgrid.com", "mailgun.com",
    "openai.com", "anthropic.com", "huggingface.co",
    "yelp.com", "tripadvisor.com", "booking.com", "airbnb.com",
    "uber.com", "lyft.com", "doordash.com", "grubhub.com",
    "weather.com", "accuweather.com",
    "imdb.com", "rottentomatoes.com",
    "espn.com", "nba.com", "nfl.com", "mlb.com",
}


def _is_known_legit(url: str) -> bool:
    """Return True if the URL belongs to a well-known legitimate domain.

    Checks the registrable domain (last two labels of hostname) so that
    mail.google.com matches google.com, but secure.paypal.com-verify.tk does not.
    """
    try:
        from urllib.parse import urlparse as _parse
        raw = url if "://" in url else "http://" + url
        hostname = _parse(raw).hostname or ""
        parts = hostname.lower().split(".")
        if len(parts) >= 2:
            registrable = ".".join(parts[-2:])
            # Direct match on registrable domain
            if registrable in _KNOWN_LEGIT_DOMAINS:
                return True
            # Also allow fqdn match (e.g. "mail.google.com" stored as-is)
            if hostname in _KNOWN_LEGIT_DOMAINS:
                return True
    except Exception:
        pass
    return False


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

        if _is_known_legit(url):
            return {
                "url": url,
                "score": 0.10,
                "is_https": "https://" in url or "://" not in url,
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

        # Guard against false negatives: when the URL has hard phishing indicators
        # (suspicious TLD + multiple keywords, IP address, or URL shortener) but the
        # ML model gives an unexpectedly low score due to training-data artifacts,
        # use the higher of the ML score and the heuristic floor.
        if _has_hard_phishing_indicators(features):
            score = max(score, _heuristic_score(features))

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


def _has_hard_phishing_indicators(f: URLFeatures) -> bool:
    """Return True when the URL has unambiguous phishing signals.

    XGBoost can underweight hard indicators when specific length/query-param
    combinations dominate certain tree splits (training-data artifact). When
    these hard indicators are present the heuristic score is used as a floor
    so the ML output cannot produce a false negative.

    Conditions (any one is sufficient):
    - IP-literal host  (classic phishing)
    - URL shortener    (hiding destination)
    - suspicious TLD + phishing keywords >= 2  (e.g. verify-paypal.xyz/login)
    """
    if f.is_ip_address:
        return True
    if f.shortener:
        return True
    if f.suspicious_tld and f.phishing_keyword_count >= 2:
        return True
    return False


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
