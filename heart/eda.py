import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

from heart.config import CATEGORICAL, FIGURES_DIR, NUMERIC, TARGET  # noqa: E402
from heart.data import load_clean  # noqa: E402

sns.set_theme(style="whitegrid", palette="Set2")


# Bar chart of how many patients fall in each target class.
def plot_class_balance(df):
    fig, ax = plt.subplots(figsize=(5, 4))
    counts = df[TARGET].map({0: "No disease", 1: "Disease"}).value_counts()
    sns.barplot(x=counts.index, y=counts.values, ax=ax)
    for i, v in enumerate(counts.values):
        ax.text(i, v + 2, f"{v} ({v / len(df):.0%})", ha="center")
    ax.set_title("Class balance")
    ax.set_ylabel("Patients")
    return fig


# Histograms of every numeric feature split by target class.
def plot_numeric_histograms(df):
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    for ax, col in zip(axes.flat, NUMERIC):
        sns.histplot(data=df, x=col, hue=TARGET, kde=True, element="step", ax=ax)
        ax.set_title(col)
    fig.suptitle("Numeric feature distributions by diagnosis")
    return fig


# Disease rate for each level of the categorical and binary features.
def plot_categorical_rates(df):
    cols = CATEGORICAL + ["sex", "exang", "fbs"]
    fig, axes = plt.subplots(2, 4, figsize=(16, 7))
    for ax, col in zip(axes.flat, cols):
        sns.barplot(data=df, x=col, y=TARGET, errorbar=None, ax=ax)
        ax.set_ylabel("Disease rate")
        ax.set_ylim(0, 1)
        ax.set_title(col)
    for ax in axes.flat[len(cols):]:
        ax.set_visible(False)
    fig.suptitle("Disease rate per category")
    return fig


# Pearson correlation heatmap across all features and the target.
def plot_correlation(df):
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(df.corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Correlation heatmap")
    return fig


# Box plots to spot outliers in the numeric features.
def plot_outliers(df):
    fig, ax = plt.subplots(figsize=(12, 4))
    scaled = (df[NUMERIC] - df[NUMERIC].mean()) / df[NUMERIC].std()
    sns.boxplot(data=scaled, ax=ax)
    ax.set_title("Standardised numeric features (outlier check)")
    return fig


# Generate every EDA figure and save them under reports/figures.
def run_eda():
    df = load_clean()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plots = {
        "eda_class_balance.png": plot_class_balance,
        "eda_numeric_histograms.png": plot_numeric_histograms,
        "eda_categorical_rates.png": plot_categorical_rates,
        "eda_correlation_heatmap.png": plot_correlation,
        "eda_outliers.png": plot_outliers,
    }
    for name, fn in plots.items():
        fig = fn(df)
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / name, dpi=110)
        plt.close(fig)
    print(f"Saved {len(plots)} figures to {FIGURES_DIR}")


if __name__ == "__main__":
    run_eda()
