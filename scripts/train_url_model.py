"""Train URL phishing detection model.

Loads URL_MASTER_DATA.csv, extracts 16 features via url_extractor,
trains XGBoost (main) + RandomForest (comparison), evaluates both,
saves the best model as url_model.pkl with SHAP feature importance.

Usage (from project root):
    cd backend
    python ../scripts/train_url_model.py \
        --data "../데이터셋 분석/데이터셋 분석, 데이터 전처리, 성능 분석/URL_MASTER_DATA.csv" \
        --output models/url_model.pkl

    # Quick smoke test with a sample:
    python ../scripts/train_url_model.py \
        --data "../데이터셋 분석/데이터셋 분석, 데이터 전처리, 성능 분석/URL_MASTER_DATA.csv" \
        --output models/url_model.pkl \
        --sample 50000
"""

import argparse
import pickle
import sys
from pathlib import Path

# Allow importing from backend/app
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from xgboost import XGBClassifier

from app.services.url_extractor import extract_features


# ── Feature extraction ────────────────────────────────────────────────────────

FEATURE_NAMES = [
    "url_length", "domain_length", "path_length",
    "num_digits", "num_special_chars",
    "at_symbol", "double_slash", "prefix_suffix_dash",
    "subdomain_count", "is_ip_address", "is_https",
    "suspicious_tld", "shortener", "phishing_keyword_count",
    "query_param_count", "has_port",
]


def extract_batch(urls: list[str], chunk_size: int = 10_000) -> np.ndarray:
    """Extract feature vectors for all URLs in memory-friendly chunks."""
    rows: list[list[float]] = []
    total = len(urls)
    for start in range(0, total, chunk_size):
        chunk = urls[start : start + chunk_size]
        for url in chunk:
            try:
                rows.append(extract_features(str(url)).to_list())
            except Exception:
                rows.append([0.0] * 16)
        pct = min(start + chunk_size, total)
        print(f"  feature extraction: {pct}/{total} ({pct/total*100:.1f}%)", end="\r")
    print()
    return np.array(rows, dtype=np.float32)


# ── Training ──────────────────────────────────────────────────────────────────

def train(data_path: str, output_path: str, sample: int | None) -> None:
    print(f"\n[1/6] Loading data from: {data_path}")
    df = pd.read_csv(data_path, usecols=["url", "label"]).dropna()
    df["label"] = pd.to_numeric(df["label"], errors="coerce").fillna(0).astype(int)

    if sample:
        df = df.sample(n=min(sample, len(df)), random_state=42)
        print(f"  Sampled {len(df):,} rows (--sample {sample})")
    else:
        print(f"  Total rows: {len(df):,}")

    print(f"  Class distribution: {df['label'].value_counts().to_dict()}")

    print("\n[2/6] Extracting URL features (16 per URL)...")
    X = extract_batch(df["url"].tolist())
    y = df["label"].to_numpy()
    print(f"  Feature matrix shape: {X.shape}")

    print("\n[3/6] Train/test split (80/20, stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    print("\n[4/6] Training models...")

    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    print("  XGBoost training...")
    xgb.fit(X_train, y_train)

    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=42,
        n_jobs=-1,
    )
    print("  RandomForest training...")
    rf.fit(X_train, y_train)

    print("\n[5/6] Evaluation on test set...")
    for name, model in [("XGBoost", xgb), ("RandomForest", rf)]:
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        print(f"\n  -- {name} --")
        print(f"  Accuracy: {acc:.4f}  |  ROC-AUC: {auc:.4f}")
        print(classification_report(y_test, y_pred, target_names=["normal", "phishing"]))

    # Cross-validation on XGBoost (main model)
    print("  5-Fold CV (XGBoost, F1-macro)...")
    cv_scores = cross_val_score(
        XGBClassifier(
            n_estimators=300, max_depth=6, use_label_encoder=False,
            eval_metric="logloss", random_state=42, n_jobs=-1
        ),
        X, y, cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        scoring="f1_macro", n_jobs=-1,
    )
    print(f"  CV F1-macro: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    print("\n  Feature importance (XGBoost):")
    importances = xgb.feature_importances_
    for fname, imp in sorted(zip(FEATURE_NAMES, importances), key=lambda x: -x[1]):
        bar = "█" * int(imp * 40)
        print(f"  {fname:<30} {bar} {imp:.4f}")

    # Optional SHAP summary
    try:
        import shap
        explainer = shap.TreeExplainer(xgb)
        shap_values = explainer.shap_values(X_test[:500])
        print("\n  SHAP mean |value| (top 5):")
        mean_shap = np.abs(shap_values).mean(axis=0)
        for i in np.argsort(mean_shap)[::-1][:5]:
            print(f"    {FEATURE_NAMES[i]}: {mean_shap[i]:.4f}")
    except ImportError:
        print("  (shap not available — skipping SHAP summary)")

    print(f"\n[6/6] Saving XGBoost model to: {output_path}")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        pickle.dump(xgb, f)
    print(f"  Saved ({out.stat().st_size / 1024:.1f} KB)")
    print("\nDone.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Train URL phishing detection model")
    parser.add_argument("--data", required=True, help="Path to URL_MASTER_DATA.csv")
    parser.add_argument(
        "--output", default="models/url_model.pkl", help="Output model path"
    )
    parser.add_argument(
        "--sample", type=int, default=None,
        help="Randomly sample N rows (useful for quick testing)"
    )
    args = parser.parse_args()
    train(args.data, args.output, args.sample)


if __name__ == "__main__":
    main()
