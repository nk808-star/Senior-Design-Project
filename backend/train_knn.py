"""
Trains a KNN classifier per disease using scaled-Euclidean (seuclidean)
distance, sweeping K = 1 .. 15 and picking the K that maximises the
DICE score on a held-out test set.

This directly mirrors the MATLAB prototype:
    Mdl = createns(factorsTrain, 'NSMethod','exhaustive','Distance','seuclidean')
    for k = 1:15
        goutPred = mean(goutTrain(Idx),2) >= 0.5;
        dice(k)  = 2*TP / (2*TP + FN + FP);
    end

Usage:
    cd backend
    python build_dataset.py   # only needed once
    python train_knn.py
"""

import os
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")           # headless — saves PNGs without a display
import matplotlib.pyplot as plt

from sklearn.neighbors import NearestNeighbors, KNeighborsClassifier
from sklearn.model_selection import train_test_split

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


# ------------------------------------------------------------------ #
# Metrics (matching the MATLAB implementations)                       #
# ------------------------------------------------------------------ #

def _confusion(y_true: np.ndarray, y_pred: np.ndarray):
    TP = int(np.sum((y_pred == 1) & (y_true == 1)))
    TN = int(np.sum((y_pred == 0) & (y_true == 0)))
    FP = int(np.sum((y_pred == 1) & (y_true == 0)))
    FN = int(np.sum((y_pred == 0) & (y_true == 1)))
    return TP, TN, FP, FN


def _dice(TP, FP, FN) -> float:
    denom = 2 * TP + FP + FN
    return (2 * TP / denom) if denom > 0 else 0.0


def _iou(TP, FP, FN) -> float:
    denom = TP + FP + FN
    return (TP / denom) if denom > 0 else 0.0


def _acc(TP, TN, FP, FN) -> float:
    total = TP + TN + FP + FN
    return ((TP + TN) / total) if total > 0 else 0.0


# ------------------------------------------------------------------ #
# Per-disease training                                                 #
# ------------------------------------------------------------------ #

def train_disease(
    disease: str,
    X_train: np.ndarray, y_train: np.ndarray,
    X_test:  np.ndarray, y_test:  np.ndarray,
) -> dict:
    print(f"\n--- {disease.upper()} ---")
    print(f"  Train: {len(y_train)} samples ({y_train.sum()} positive)")
    print(f"  Test : {len(y_test)}  samples ({y_test.sum()} positive)")

    # Variance vector for seuclidean (computed on training set only,
    # exactly as MATLAB's createns does internally)
    V = np.var(X_train, axis=0, dtype=float)
    V[V == 0] = 1e-10   # avoid div-by-zero on constant features

    # --- K sweep (MATLAB: knnsearch → mean ≥ 0.5 → DICE) ---
    nn = NearestNeighbors(
        algorithm="ball_tree",
        metric="seuclidean",
        metric_params={"V": V},
    )
    nn.fit(X_train)

    # Fetch 15 neighbours in one call; slice for each k
    _, idx = nn.kneighbors(X_test, n_neighbors=15)

    dice_arr = np.zeros(15)
    iou_arr  = np.zeros(15)
    acc_arr  = np.zeros(15)

    for k in range(1, 16):
        neighbor_labels = y_train[idx[:, :k]]          # (n_test, k)
        y_pred = (neighbor_labels.mean(axis=1) >= 0.5).astype(int)
        TP, TN, FP, FN = _confusion(y_test, y_pred)
        dice_arr[k - 1] = _dice(TP, FP, FN)
        iou_arr[k - 1]  = _iou(TP, FP, FN)
        acc_arr[k - 1]  = _acc(TP, TN, FP, FN)

    best_k = int(np.argmax(dice_arr)) + 1
    print(f"  Best K = {best_k}  |  DICE = {dice_arr[best_k-1]:.4f}"
          f"  IoU = {iou_arr[best_k-1]:.4f}  Acc = {acc_arr[best_k-1]:.4f}")

    # --- DICE optimisation plot (mirrors the MATLAB figure) ---
    fig, ax = plt.subplots()
    ax.plot(range(1, 16), dice_arr, marker="o")
    ax.axvline(x=best_k, color="red", linestyle="--", alpha=0.6, label=f"Best K={best_k}")
    ax.set_title(f"KNN Optimisation — {disease}")
    ax.set_xlabel("K")
    ax.set_ylabel("DICE")
    ax.set_ylim([0, 1])
    ax.set_xticks(range(1, 16))
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(MODELS_DIR, f"{disease}_dice_curve.png"), dpi=100)
    plt.close(fig)

    # --- Train final classifier with best K ---
    clf = KNeighborsClassifier(
        n_neighbors=best_k,
        algorithm="ball_tree",
        metric="seuclidean",
        metric_params={"V": V},
        weights="uniform",
    )
    clf.fit(X_train, y_train)

    y_pred_final = clf.predict(X_test)
    TP, TN, FP, FN = _confusion(y_test, y_pred_final)
    print(f"  Final → TP={TP}  TN={TN}  FP={FP}  FN={FN}")

    # --- Persist model + variance vector ---
    os.makedirs(MODELS_DIR, exist_ok=True)
    payload = {"model": clf, "V": V, "best_k": best_k}
    path = os.path.join(MODELS_DIR, f"{disease}_knn.pkl")
    joblib.dump(payload, path)
    print(f"  Saved  → {path}")

    return {
        "best_k":   best_k,
        "dice":     dice_arr[best_k - 1],
        "iou":      iou_arr[best_k - 1],
        "accuracy": acc_arr[best_k - 1],
    }


# ------------------------------------------------------------------ #
# Entry point                                                          #
# ------------------------------------------------------------------ #

def train_all():
    feat_path  = os.path.join(DATA_DIR, "nhanes_features.csv")
    label_path = os.path.join(DATA_DIR, "nhanes_labels.csv")

    if not os.path.exists(feat_path):
        raise FileNotFoundError(
            "nhanes_features.csv not found — run build_dataset.py first."
        )

    X_df = pd.read_csv(feat_path)
    # Impute any remaining NaNs with column median before training
    for col in X_df.columns:
        median = X_df[col].median()
        X_df[col] = X_df[col].fillna(median)
    X = X_df.values.astype(float)
    L = pd.read_csv(label_path)

    os.makedirs(MODELS_DIR, exist_ok=True)

    summary = {}
    for disease in DISEASES:
        col = f"label_{disease}"
        if col not in L.columns:
            print(f"\nSkipping {disease} — no label column found")
            continue

        y_all = L[col].values.astype(float)

        # Drop rows where the label is NaN
        valid   = ~np.isnan(y_all)
        X_valid = X[valid].copy()
        y_valid = y_all[valid].astype(int)

        # Impute any remaining NaNs per-column using median; fall back to 0
        # if the entire column is NaN (feature not collected for these rows)
        for ci in range(X_valid.shape[1]):
            nan_mask = np.isnan(X_valid[:, ci])
            if nan_mask.any():
                median = np.nanmedian(X_valid[:, ci])
                fill = median if not np.isnan(median) else 0.0
                X_valid[nan_mask, ci] = fill

        if y_valid.sum() < 10:
            print(f"\nSkipping {disease} — too few positive examples ({y_valid.sum()})")
            continue

        # 75 / 25 stratified split (matches MATLAB 1500 / 500 ratio)
        X_train, X_test, y_train, y_test = train_test_split(
            X_valid, y_valid,
            test_size=0.25,
            random_state=42,
            stratify=y_valid,
        )

        result = train_disease(disease, X_train, y_train, X_test, y_test)
        summary[disease] = result

    # --- Print summary table ---
    print("\n" + "=" * 60)
    print(f"{'Disease':<25}  {'K':>3}  {'DICE':>6}  {'IoU':>6}  {'Acc':>6}")
    print("-" * 60)
    for disease, r in summary.items():
        print(
            f"  {disease:<23}  {r['best_k']:>3}  "
            f"{r['dice']:>6.4f}  {r['iou']:>6.4f}  {r['accuracy']:>6.4f}"
        )
    print("=" * 60)
    print(f"\nDICE curves saved to {MODELS_DIR}/")


if __name__ == "__main__":
    train_all()
