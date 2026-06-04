"""NLP-based phishing risk scorer for email body text.

Architecture:
  - Baseline: TF-IDF + SVM loaded from nlp_model.pkl (directory with model.pkl)
  - Main model: BERT/RoBERTa fine-tuned (loaded when NLP_MODEL_PATH is a directory
    that contains tokenizer config → detected as BERT model dir)
  - Fallback: rule-based heuristic when no model is present

Preprocessing contract (기획서 8.3 준수):
    clean_email_text() matches the training-time preprocessor from
    전처리 소스 코드.md (담당자: 오준혁). Pass this as clean_fn when calling
    PhishingClassifier.predict_raw() to avoid distribution mismatch.

Public API:
    score(subject, body) → NLPResult
"""

from __future__ import annotations

import pickle
import re
import warnings
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

settings = get_settings()


# ── Preprocessing (mirrors 전처리 소스 코드.md) ──────────────────────────────

def clean_email_text(text: str) -> str:
    """Clean raw email text for NLP model input.

    Matches the training-time preprocessing pipeline (전처리 소스 코드.md):
      1. Remove HTML tags
      2. Mask URLs with [URL] token (prevents overfitting to specific URLs)
      3. Filter to alphanumeric + Korean + basic punctuation
      4. Normalize whitespace
    """
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", "[URL]", text)
    text = re.sub(r"[^a-zA-Z0-9가-힣.,!?\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_fn(subject: str, body: str) -> str:
    """Two-arg wrapper for use with PhishingClassifier.predict_raw()."""
    return clean_email_text(f"{subject}\n\n{body}")


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class NLPResult:
    score: float           # 0.0 = safe, 1.0 = definitely phishing
    top_features: list[str]  # top contributing tokens / keywords


# ── Rule-based fallback (no model needed for demo) ───────────────────────────

_PHISHING_PATTERNS = [
    # Korean
    "즉시 확인", "24시간", "계정 정지", "비밀번호 재설정", "로그인 인증",
    "계정 확인", "송금", "결제 오류", "환불", "청구서", "보안 페이지",
    "아래 링크", "미조치 시", "서비스 중단", "법적 조치",
    # English
    "verify your account", "click here", "suspended", "urgent",
    "confirm your", "update your", "your account has been",
    "limited time", "act now", "login immediately", "validate",
    "reset your password",
]


def _rule_based_score(text: str) -> tuple[float, list[str]]:
    text_lower = text.lower()
    hits = [p for p in _PHISHING_PATTERNS if p.lower() in text_lower]
    score = min(1.0, len(hits) * 0.15)
    return score, hits


# ── Model loading ─────────────────────────────────────────────────────────────

def _is_bert_dir(path: Path) -> bool:
    """True when path is a directory containing a HuggingFace model."""
    return path.is_dir() and (
        (path / "config.json").exists() or (path / "tokenizer_config.json").exists()
    )


def _is_tfidf_dir(path: Path) -> bool:
    """True when path is a directory containing a pickled sklearn pipeline."""
    return path.is_dir() and (path / "model.pkl").exists()


@lru_cache(maxsize=1)
def _load_model():
    """Load whichever model is configured.

    Detection order:
      1. NLP_MODEL_PATH is a directory with HuggingFace files → BERT via PhishingClassifier
      2. NLP_MODEL_PATH is a directory with model.pkl → TF-IDF via PhishingClassifier
      3. NLP_MODEL_PATH is a .pkl file → legacy sklearn pipeline
      4. Nothing found → return None (rule-based fallback)
    """
    path = Path(settings.NLP_MODEL_PATH)

    if _is_bert_dir(path):
        try:
            from app.services.infer import PhishingClassifier
            return ("bert_clf", PhishingClassifier(path, backend="bert"))
        except Exception as exc:
            warnings.warn(f"Failed to load BERT model from {path}: {exc}")

    if _is_tfidf_dir(path):
        try:
            from app.services.infer import PhishingClassifier
            return ("tfidf_clf", PhishingClassifier(path, backend="tfidf"))
        except Exception as exc:
            warnings.warn(f"Failed to load TF-IDF dir model from {path}: {exc}")

    if path.is_file() and path.exists():
        try:
            with open(path, "rb") as f:
                return ("sklearn", pickle.load(f))
        except Exception as exc:
            warnings.warn(f"Failed to load sklearn model from {path}: {exc}")

    return None


# ── Inference helpers ─────────────────────────────────────────────────────────

def _infer_with_classifier(model_entry, subject: str, body: str) -> float:
    """Infer using PhishingClassifier (BERT or TF-IDF backend)."""
    _, clf = model_entry
    result = clf.predict_raw(subject, body, clean_fn=_clean_fn)
    return result["phishing_prob"]


def _infer_sklearn(text: str, pipe) -> float:
    proba = pipe.predict_proba([text])
    return float(proba[0][1])


# ── Public API ────────────────────────────────────────────────────────────────

def score(subject: str, body: str) -> NLPResult:
    """Score an email for phishing probability.

    Falls back gracefully: BERT → TF-IDF PhishingClassifier → sklearn pickle
    → rule-based heuristic.
    """
    model_entry = _load_model()
    combined = clean_email_text(f"{subject}\n\n{body}")
    _, rule_features = _rule_based_score(combined)

    if model_entry is not None:
        kind = model_entry[0]
        try:
            if kind in ("bert_clf", "tfidf_clf"):
                s = _infer_with_classifier(model_entry, subject, body)
            else:
                s = _infer_sklearn(combined, model_entry[1])
            return NLPResult(score=s, top_features=rule_features[:5])
        except Exception:
            pass

    s, features = _rule_based_score(combined)
    return NLPResult(score=s, top_features=features[:5])
