"""
K-fold cross validation and performance report for the KNN disease risk models.

Runs 5-fold stratified cross validation per disease and reports:
  - DICE score        (same metric used to pick K during training)
  - ROC-AUC           (overall discrimination ability, 0.5 = random, 1.0 = perfect)
  - Sensitivity       (true positive rate — how often we catch real cases)
  - Specificity       (true negative rate — how often we correctly clear healthy people)
  - PPV               (precision — when we say "high risk", how often are we right)
  - Accuracy

Also generates:
  - backend/models/validation_report.txt   (text summary)
  - backend/models/{disease}_roc_curve.png (ROC curve per disease)

Usage:
    cd backend
    python validate_model.py
"""

import os
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import roc_auc_score, roc_curve

DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

DISEASES = [
    "gout",
    "diabetes",
    "ckd",
    "hypertension",
    "cvd",
    "metabolic_syndrome",
]

N_FOLDS = 5


# ------------------------------------------------------------------ #
# Metrics                                                              #
# ------------------------------------------------------------------ #

def _metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    TP = int(np.sum((y_pred == 1) & (y_true == 1)))
    TN = int(np.sum((y_pred == 0) & (y_true == 0)))
    FP = int(np.sum((y_pred == 1) & (y_true == 0)))
    FN = int(np.sum((y_pred == 0) & (y_true == 1)))

    dice        = (2 * TP) / (2 * TP + FP + FN) if (2 * TP + FP + FN) > 0 else 0.0
    sensitivity = TP / (TP + FN) if (TP + FN) > 0 else 0.0   # recall
    specificity = TN / (TN + FP) if (TN + FP) > 0 else 0.0
    ppv         = TP / (TP + FP) if (TP + FP) > 0 else 0.0   # precision
    accuracy    = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) > 0 else 0.0

    try:
        auc = roc_auc_score(y_true, y_prob)
    except ValueError:
        auc = float("nan")

    return {
        "TP": TP, "TN": TN, "FP": FP, "FN": FN,
        "dice": dice,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "ppv": ppv,
        "accuracy": accuracy,
        "auc": auc,
    }


# ------------------------------------------------------------------ #
# Per-disease validation                                               #
# ------------------------------------------------------------------ #

def validate_disease(
    disease: str,
    X: np.ndarray,
    y: np.ndarray,
    best_k: int,
    V: np.ndarray,
) -> dict:
    print(f"\n--- {disease.upper()} (K={best_k}, {N_FOLDS}-fold CV) ---")
    print(f"  Total samples: {len(y)}  |  Positive: {y.sum()}  ({100*y.mean():.1f}%)")

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)

    fold_metrics = []
    all_y_true, all_y_prob = [], []

    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y), 1):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # Recompute variance on this fold's training set (same as training pipeline)
        V_fold = np.var(X_train, axis=0, dtype=float)
        V_fold[V_fold == 0] = 1e-10

        clf = KNeighborsClassifier(
            n_neighbors=best_k,
            algorithm="ball_tree",
            metric="seuclidean",
            metric_params={"V": V_fold},
            weights="uniform",
        )
        clf.fit(X_train, y_train)

        y_pred = clf.predict(X_test)
        y_prob = clf.predict_proba(X_test)[:, 1]

        m = _metrics(y_test, y_pred, y_prob)
        fold_metrics.append(m)
        all_y_true.extend(y_test)
        all_y_prob.extend(y_prob)

        print(
            f"  Fold {fold}: DICE={m['dice']:.3f}  AUC={m['auc']:.3f}"
            f"  Sens={m['sensitivity']:.3f}  Spec={m['specificity']:.3f}"
            f"  PPV={m['ppv']:.3f}  Acc={m['accuracy']:.3f}"
        )

    # Average across folds
    keys = ["dice", "auc", "sensitivity", "specificity", "ppv", "accuracy"]
    avg  = {k: float(np.mean([m[k] for m in fold_metrics])) for k in keys}
    std  = {k: float(np.std( [m[k] for m in fold_metrics])) for k in keys}

    print(f"\n  {'':6s}  " + "  ".join(f"{k[:4].upper():>6}" for k in keys))
    print(f"  {'Mean':6s}  " + "  ".join(f"{avg[k]:>6.3f}" for k in keys))
    print(f"  {'± Std':6s}  " + "  ".join(f"{std[k]:>6.3f}" for k in keys))

    # ROC curve using all out-of-fold predictions (gives the most data points)
    all_y_true = np.array(all_y_true)
    all_y_prob = np.array(all_y_prob)
    try:
        fpr, tpr, _ = roc_curve(all_y_true, all_y_prob)
        overall_auc = roc_auc_score(all_y_true, all_y_prob)

        fig, ax = plt.subplots()
        ax.plot(fpr, tpr, label=f"AUC = {overall_auc:.3f}")
        ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Random (AUC = 0.5)")
        ax.set_title(f"ROC Curve — {disease.replace('_', ' ').title()}")
        ax.set_xlabel("False Positive Rate (1 - Specificity)")
        ax.set_ylabel("True Positive Rate (Sensitivity)")
        ax.legend()
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1.02])
        fig.tight_layout()
        os.makedirs(MODELS_DIR, exist_ok=True)
        fig.savefig(os.path.join(MODELS_DIR, f"{disease}_roc_curve.png"), dpi=100)
        plt.close(fig)
    except ValueError:
        overall_auc = float("nan")

    return {"disease": disease, "best_k": best_k, "avg": avg, "std": std}


# ------------------------------------------------------------------ #
# Entry point                                                          #
# ------------------------------------------------------------------ #

def validate_all():
    feat_path  = os.path.join(DATA_DIR, "nhanes_features.csv")
    label_path = os.path.join(DATA_DIR, "nhanes_labels.csv")

    if not os.path.exists(feat_path):
        raise FileNotFoundError("nhanes_features.csv not found — run build_dataset.py first.")
    if not os.path.exists(MODELS_DIR):
        raise FileNotFoundError("models/ folder not found — run train_knn.py first.")

    X = pd.read_csv(feat_path).values.astype(float)
    L = pd.read_csv(label_path)

    results = []
    for disease in DISEASES:
        model_path = os.path.join(MODELS_DIR, f"{disease}_knn.pkl")
        if not os.path.exists(model_path):
            print(f"\nSkipping {disease} — no trained model found")
            continue

        payload = joblib.load(model_path)
        best_k  = payload["best_k"]
        V       = payload["V"]

        col = f"label_{disease}"
        if col not in L.columns:
            print(f"\nSkipping {disease} — label column missing")
            continue

        y_all = L[col].values.astype(float)
        valid = ~np.isnan(y_all)
        X_v   = X[valid]
        y_v   = y_all[valid].astype(int)

        if y_v.sum() < 10:
            print(f"\nSkipping {disease} — too few positive examples")
            continue

        result = validate_disease(disease, X_v, y_v, best_k, V)
        results.append(result)

    # ------------------------------------------------------------------ #
    # Summary table + save report                                          #
    # ------------------------------------------------------------------ #
    header = f"\n{'='*72}\n{'VALIDATION SUMMARY — ' + str(N_FOLDS) + '-Fold Stratified Cross Validation':^72}\n{'='*72}"
    col_header = f"  {'Disease':<25}  {'K':>3}  {'DICE':>6}  {'AUC':>6}  {'Sens':>6}  {'Spec':>6}  {'PPV':>6}  {'Acc':>6}"
    divider    = "  " + "-" * 68
    rows = []
    for r in results:
        a = r["avg"]
        rows.append(
            f"  {r['disease']:<25}  {r['best_k']:>3}  "
            f"{a['dice']:>6.3f}  {a['auc']:>6.3f}  "
            f"{a['sensitivity']:>6.3f}  {a['specificity']:>6.3f}  "
            f"{a['ppv']:>6.3f}  {a['accuracy']:>6.3f}"
        )

    legend = """
Metric guide:
  DICE        — harmonic mean of sensitivity and PPV; main training metric
  AUC         — area under ROC curve; 0.5 = random, 1.0 = perfect
  Sensitivity — % of true cases caught (low = missing sick people)
  Specificity — % of true negatives correctly cleared (low = over-diagnosing)
  PPV         — when model says "high risk", how often correct (precision)
  Accuracy    — overall correct predictions

Rules of thumb for AUC:
  0.90–1.00  Excellent
  0.80–0.90  Good
  0.70–0.80  Fair
  0.60–0.70  Poor
  0.50–0.60  No better than random
"""

    report = "\n".join([header, col_header, divider] + rows + [divider, legend])
    print(report)

    report_path = os.path.join(MODELS_DIR, "validation_report.txt")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Report saved to {report_path}")
    print(f"ROC curves saved to {MODELS_DIR}/")


if __name__ == "__main__":
    validate_all()
