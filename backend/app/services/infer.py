"""Unified inference interface for phishing email classification.

Adapted from 이메일 NLP 모델 코드.md (담당자: 오형준).

Contract for the backend (nlp_model.py):

    from app.services.infer import PhishingClassifier
    clf = PhishingClassifier("models/bert/final", backend="bert")
    result = clf.predict(cleaned_text)
    # → {"phishing_prob": 0.87, "label": "phishing", "backend": "bert"}

IMPORTANT — preprocessing contract:
    The model was trained on `cleaned_text` produced by the preprocessing
    pipeline (clean_email_text in nlp_model.py).  predict() therefore expects
    text that has already been cleaned.  Distribution mismatch (passing raw
    email body directly) silently degrades accuracy.

    Use predict_raw(subject, body, clean_fn) to have the cleaner applied
    automatically, where clean_fn matches the training-time preprocessor.
"""

from __future__ import annotations

import pickle
import sys
import warnings
from pathlib import Path
from typing import Callable, Literal

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

Backend = Literal["tfidf", "bert"]
CleanFn = Callable[[str, str], str]


def _naive_concat(subject: str, body: str) -> str:
    """Last-resort fallback when no cleaner is provided.

    Lowercases and concatenates subject + body.  Does NOT match training-time
    preprocessing — use only for smoke tests.
    """
    return f"{(subject or '').lower()} {(body or '').lower()}".strip()


class PhishingClassifier:
    """Unified inference wrapper for TF-IDF and BERT phishing classifiers."""

    def __init__(
        self,
        model_dir: str | Path,
        backend: Backend,
        max_length: int = 256,
    ) -> None:
        self.backend = backend
        self.max_length = max_length
        model_dir = Path(model_dir)

        if backend == "tfidf":
            with open(model_dir / "model.pkl", "rb") as f:
                self.pipe = pickle.load(f)
            self.device = None
        elif backend == "bert":
            self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(model_dir)
            )
            self.model.eval()
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(self.device)
        else:
            raise ValueError(f"unknown backend: {backend!r}")

    # ── Primary entry point ──────────────────────────────────────────────────

    @torch.no_grad()
    def predict(self, cleaned_text: str, threshold: float = 0.5) -> dict:
        """Classify pre-cleaned email text.

        cleaned_text MUST be the output of the training-time cleaning function.
        """
        prob = self._prob_one(cleaned_text)
        return self._format(prob, threshold)

    @torch.no_grad()
    def predict_batch(
        self,
        cleaned_texts: list[str],
        threshold: float = 0.5,
        batch_size: int = 32,
    ) -> list[dict]:
        probs = self._prob_many(cleaned_texts, batch_size=batch_size)
        return [self._format(float(p), threshold) for p in probs]

    # ── Convenience for raw email input ─────────────────────────────────────

    def predict_raw(
        self,
        subject: str,
        body: str,
        clean_fn: CleanFn | None = None,
        threshold: float = 0.5,
    ) -> dict:
        """Classify a raw (subject, body) pair.

        If clean_fn is provided (recommended: the same cleaner used at training
        time), it is applied first.  Otherwise a naive lowercased concatenation
        is used — this will NOT match training distribution and is for smoke
        testing only.
        """
        if clean_fn is None:
            warnings.warn(
                "predict_raw called without clean_fn; using naive fallback "
                "that does NOT match training preprocessing. Pass the "
                "clean_email_text wrapper as clean_fn for correct results.",
                stacklevel=2,
            )
            text = _naive_concat(subject, body)
        else:
            text = clean_fn(subject, body)
        return self.predict(text, threshold=threshold)

    # ── Internals ────────────────────────────────────────────────────────────

    @torch.no_grad()
    def _prob_one(self, text: str) -> float:
        if self.backend == "tfidf":
            return float(self.pipe.predict_proba([text])[0, 1])
        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        ).to(self.device)
        logits = self.model(**inputs).logits
        return float(torch.softmax(logits, dim=-1)[0, 1].item())

    @torch.no_grad()
    def _prob_many(self, texts: list[str], batch_size: int = 32) -> list[float]:
        if self.backend == "tfidf":
            return self.pipe.predict_proba(texts)[:, 1].tolist()
        out: list[float] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            inputs = self.tokenizer(
                chunk,
                truncation=True,
                max_length=self.max_length,
                padding=True,
                return_tensors="pt",
            ).to(self.device)
            logits = self.model(**inputs).logits
            out.extend(torch.softmax(logits, dim=-1)[:, 1].cpu().tolist())
        return out

    def _format(self, prob: float, threshold: float) -> dict:
        return {
            "phishing_prob": prob,
            "label": "phishing" if prob >= threshold else "legit",
            "backend": self.backend,
        }
