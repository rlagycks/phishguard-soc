"""Train NLP phishing email classification model (TF-IDF baseline).

Loads NLP_MASTER_DATA.csv (cleaned_text, label), trains a TF-IDF + SVM
pipeline, evaluates it, and saves the model for the backend.

Output structure (backend/models/nlp/):
    model.pkl   — sklearn Pipeline (TfidfVectorizer + LinearSVC)

Usage (from project root):
    cd backend
    python ../scripts/train_nlp_model.py \
        --data "../데이터셋 분석/데이터셋 분석, 데이터 전처리, 성능 분석/NLP_MASTER_DATA.csv" \
        --output models/nlp

    # Quick smoke test with a sample:
    python ../scripts/train_nlp_model.py \
        --data "../데이터셋 분석/데이터셋 분석, 데이터 전처리, 성능 분석/NLP_MASTER_DATA.csv" \
        --output models/nlp \
        --sample 20000

Note: For BERT fine-tuning, download the model from the Google Drive link
in 이메일 NLP 모델 코드.md and place it in models/bert/.
Then set NLP_MODEL_PATH=models/bert in .env to switch to BERT inference.
"""

import argparse
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


# ── Training ──────────────────────────────────────────────────────────────────

def train(data_path: str, output_dir: str, sample: int | None) -> None:
    print(f"\n[1/5] Loading data from: {data_path}")
    df = pd.read_csv(data_path, usecols=["cleaned_text", "label"]).dropna()
    df["label"] = pd.to_numeric(df["label"], errors="coerce").fillna(0).astype(int)
    df = df[df["cleaned_text"].str.strip().astype(bool)]  # drop empty texts

    if sample:
        df = df.sample(n=min(sample, len(df)), random_state=42)
        print(f"  Sampled {len(df):,} rows (--sample {sample})")
    else:
        print(f"  Total rows: {len(df):,}")

    print(f"  Class distribution: {df['label'].value_counts().to_dict()}")

    X = df["cleaned_text"].tolist()
    y = df["label"].to_numpy()

    print("\n[2/5] Train/test split (80/20, stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    print("\n[3/5] Training TF-IDF + SVM pipeline (baseline)...")
    # CalibratedClassifierCV wraps LinearSVC to produce probability estimates
    # required by predict_proba() in the backend.
    svm_pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=50_000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=2,
        )),
        ("clf", CalibratedClassifierCV(LinearSVC(max_iter=2000), cv=3)),
    ])
    svm_pipe.fit(X_train, y_train)

    print("  Training Logistic Regression (comparison)...")
    lr_pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=50_000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=2,
        )),
        ("clf", LogisticRegression(max_iter=1000, C=1.0, solver="lbfgs", n_jobs=-1)),
    ])
    lr_pipe.fit(X_train, y_train)

    print("\n[4/5] Evaluation on test set...")
    for name, pipe in [("TF-IDF + SVM (Calibrated)", svm_pipe), ("TF-IDF + LogReg", lr_pipe)]:
        y_pred = pipe.predict(X_test)
        y_prob = pipe.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        print(f"\n  -- {name} --")
        print(f"  Accuracy: {acc:.4f}  |  ROC-AUC: {auc:.4f}")
        print(classification_report(y_test, y_pred, target_names=["normal", "phishing"]))

    # 5-fold CV on SVM pipeline (main model)
    print("  5-Fold CV (SVM, F1-macro)...")
    cv_scores = cross_val_score(
        Pipeline([
            ("tfidf", TfidfVectorizer(max_features=50_000, ngram_range=(1, 2), sublinear_tf=True, min_df=2)),
            ("clf", CalibratedClassifierCV(LinearSVC(max_iter=2000), cv=3)),
        ]),
        X, y,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        scoring="f1_macro",
        n_jobs=1,
    )
    print(f"  CV F1-macro: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    print(f"\n[5/5] Saving SVM model to: {output_dir}/model.pkl")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model_path = out / "model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(svm_pipe, f)
    print(f"  Saved ({model_path.stat().st_size / 1024:.1f} KB)")
    print(f"\nSet NLP_MODEL_PATH={output_dir} in backend/.env to use this model.")
    print("Done.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Train NLP phishing email classifier (TF-IDF baseline)")
    parser.add_argument("--data", required=True, help="Path to NLP_MASTER_DATA.csv")
    parser.add_argument(
        "--output", default="models/nlp", help="Output directory (will contain model.pkl)"
    )
    parser.add_argument(
        "--sample", type=int, default=None,
        help="Randomly sample N rows (useful for quick testing)"
    )
    args = parser.parse_args()
    train(args.data, args.output, args.sample)


if __name__ == "__main__":
    main()
