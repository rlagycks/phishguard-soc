# 이메일 NLP 모델 코드

담당자: 오형준
마지막 수정일: 2026년 5월 21일 오후 9:00 (GMT+9)
유형: 🔒 코드

<aside>
💡

 `predict()` 입력은 **3번 담당의 cleaned_text 함수 결과**여야 함.

raw 메일 본문을 그대로 넣으면 학습 분포와 안 맞아 정확도 떨어짐.

</aside>

```python
"""Unified inference interface for phishing email classification.

Contract for the backend team (role 4):

    from infer import PhishingClassifier
    clf = PhishingClassifier("models/bert/final", backend="bert")
    result = clf.predict(cleaned_text)
    # -> {"phishing_prob": 0.87, "label": "phishing", "backend": "bert"}

IMPORTANT — preprocessing contract:
    The model was trained on `cleaned_text` produced by role 3's cleaning
    pipeline. `predict()` therefore expects text that has already been run
    through the SAME cleaning function. Distribution mismatch (= passing
    raw email body straight in) silently degrades accuracy.

    Three ways to use this from the backend:
      (A) Recommended — role 3 exposes their cleaner; backend calls it
          first, then passes the result to `predict(cleaned_text)`.
      (B) Pass a `clean_fn` callable to `predict_raw(subject, body, clean_fn)`
          and we'll wire it together for you.
      (C) Last resort — `predict_raw(subject, body)` with no clean_fn falls
          back to a *naive* concatenation. This is only meant for smoke
          tests; numbers will not match the reported metrics.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Literal

import joblib
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(Path(__file__).parent))

Backend = Literal["tfidf", "bert"]
CleanFn = Callable[[str, str], str]

def _naive_concat(subject: str, body: str) -> str:
    """Last-resort fallback when no role-3 cleaner is provided.

    Lowercases and concatenates subject + body. Does NOT match the
    training-time preprocessing — use only for smoke tests.
    """
    return f"{(subject or '').lower()} {(body or '').lower()}".strip()

class PhishingClassifier:
    def __init__(
        self,
        model_dir: str | Path,
        backend: Backend,
        max_length: int = 256,
    ):
        self.backend = backend
        self.max_length = max_length
        model_dir = Path(model_dir)

        if backend == "tfidf":
            self.pipe = joblib.load(model_dir / "model.joblib")
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

    # ---------- primary entry point ----------

    @torch.no_grad()
    def predict(self, cleaned_text: str, threshold: float = 0.5) -> dict:
        """Classify pre-cleaned email text.

        `cleaned_text` MUST be produced by the same cleaning function used
        at training time (role 3's pipeline). Bypassing this contract will
        degrade accuracy silently.
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

    # ---------- convenience for raw email input ----------

    def predict_raw(
        self,
        subject: str,
        body: str,
        clean_fn: CleanFn | None = None,
        threshold: float = 0.5,
    ) -> dict:
        """Classify a raw (subject, body) pair.

        If `clean_fn` is provided (recommended: role 3's cleaner), it is
        applied first. Otherwise a naive lowercased concatenation is used
        — this WILL NOT match training distribution and is for smoke
        testing only. A warning is printed in that case.
        """
        if clean_fn is None:
            import warnings
            warnings.warn(
                "predict_raw called without clean_fn; using naive fallback "
                "that does NOT match training preprocessing. Pass role 3's "
                "cleaning function as clean_fn for correct results.",
                stacklevel=2,
            )
            text = _naive_concat(subject, body)
        else:
            text = clean_fn(subject, body)
        return self.predict(text, threshold=threshold)

    # ---------- internals ----------

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

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--model_dir", required=True)
    parser.add_argument("--backend", choices=["tfidf", "bert"], required=True)
    parser.add_argument("--text", default=None,
                        help="pre-cleaned email text (matches training)")
    parser.add_argument("--subject", default=None,
                        help="raw subject (used with --body, smoke-test fallback)")
    parser.add_argument("--body", default=None,
                        help="raw body (used with --subject, smoke-test fallback)")
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    clf = PhishingClassifier(args.model_dir, args.backend)
    if args.text is not None:
        print(clf.predict(args.text, threshold=args.threshold))
    elif args.body is not None:
        print(clf.predict_raw(args.subject or "", args.body,
                              threshold=args.threshold))
    else:
        parser.error("provide either --text (pre-cleaned) or --body (raw)")

if __name__ == "__main__":
    main()
```

모델 파일 (별도 다운로드):

- BERT: [https://drive.google.com/file/d/1BLxlZdiP9AdgdYz3GfGhaLEfM_oZgwn9/view?usp=drive_link](https://drive.google.com/file/d/1BLxlZdiP9AdgdYz3GfGhaLEfM_oZgwn9/view?usp=drive_link)
- TF-IDF: [https://drive.google.com/drive/folders/1ieYcipqkyLnJSumF3fs4LOo7mk2bkFLt?usp=sharing](https://drive.google.com/drive/folders/1ieYcipqkyLnJSumF3fs4LOo7mk2bkFLt?usp=sharing)