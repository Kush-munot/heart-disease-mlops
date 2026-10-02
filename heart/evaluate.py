from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


# Compute the classification metrics reported for every run.
def compute_metrics(y_true, y_pred, y_prob) -> dict:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_prob),
    }


# Save a confusion-matrix plot for the given predictions.
def plot_confusion(y_true, y_pred, title: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ConfusionMatrixDisplay.from_predictions(
        y_true, y_pred, display_labels=["No disease", "Disease"], cmap="Blues", ax=ax
    )
    ax.set_title(title)
    return _save(fig, path)


# Save a ROC curve plot for the given probabilities.
def plot_roc(y_true, y_prob, title: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(4.5, 4))
    RocCurveDisplay.from_predictions(y_true, y_prob, ax=ax)
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8)
    ax.set_title(title)
    return _save(fig, path)


# Save a bar chart of the top feature importances or absolute coefficients.
def plot_importance(pipeline, path: Path, top: int = 15) -> Path | None:
    clf = pipeline.named_steps["clf"]
    names = pipeline.named_steps["prep"].get_feature_names_out()
    if hasattr(clf, "feature_importances_"):
        values = clf.feature_importances_
    elif hasattr(clf, "coef_"):
        values = np.abs(clf.coef_[0])
    else:
        return None
    series = pd.Series(values, index=names).sort_values().tail(top)
    fig, ax = plt.subplots(figsize=(6, 5))
    series.plot.barh(ax=ax, color="#2a6f97")
    ax.set_title("Top feature contributions")
    return _save(fig, path)


# Save a grouped bar chart comparing models on their CV metrics.
def plot_model_comparison(summary: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    summary.plot.bar(ax=ax, rot=0)
    ax.set_ylim(0.5, 1.0)
    ax.set_ylabel("5-fold CV score")
    ax.set_title("Model comparison (cross-validation)")
    ax.legend(loc="lower right", ncol=3, fontsize=8)
    return _save(fig, path)


# Write a figure to disk and release its memory.
def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
