"""Exploratory Data Analysis (EDA) module for Road Failure Prediction dataset.

Performs systematic inspection of:
- Dataset geometry, missing values, duplicates, and column data types
- Target class balance and failure proportions
- Distribution and summary statistics of numerical road attributes
- Correlation and relationship analysis between features and failure outcome
- Generates focused, high-value diagnostic plots.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ml.common.config import settings
from ml.common.logging_config import get_logger
from ml.failure_prediction.config import failure_config

logger = get_logger("failure_prediction.eda")


def perform_eda(
    data_path: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """Execute reproducible EDA workflow and output statistical summaries and plots.

    Args:
        data_path: Filepath to CSV dataset.
        output_dir: Destination folder for generated plots and summary reports.

    Returns:
        Dictionary of computed summary statistics.
    """
    logger.info("Executing EDA on dataset: %s", data_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)

    # 1. Dataset Shape & Integrity
    n_rows, n_cols = df.shape
    missing_counts = df.isnull().sum().to_dict()
    total_missing = sum(missing_counts.values())
    n_duplicates = df.duplicated().sum()

    # 2. Target Analysis
    target_col = failure_config.target_column
    class_counts = df[target_col].value_counts().to_dict()
    failure_pct = float(df[target_col].mean() * 100.0)

    # 3. Key Feature Correlations with Target
    numerical_cols = [c for c in failure_config.raw_feature_columns if c in df.columns]
    correlations = df[numerical_cols].apply(lambda col: col.corr(df[target_col])).sort_values(ascending=False).to_dict()

    summary_stats = {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "total_missing": total_missing,
        "n_duplicates": int(n_duplicates),
        "class_distribution": class_counts,
        "failure_percentage": round(failure_pct, 2),
        "feature_correlations": {k: round(v, 4) for k, v in correlations.items()},
    }

    # 4. Generate Core Diagnostic Plots
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Target Class Distribution
    ax1 = axes[0, 0]
    bars = ax1.bar(["No Failure (0)", "Failure Next 30d (1)"], [class_counts.get(0, 0), class_counts.get(1, 0)], color=["#2b5c8f", "#d9534f"])
    ax1.set_title("Target Class Distribution (30-day Horizon)", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Observation Count")
    for bar in bars:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, yval + 50, f"{yval} ({yval/n_rows*100:.1f}%)", ha="center", va="bottom", fontweight="bold")

    # Plot 2: Road Quality vs Potholes by Failure Target
    ax2 = axes[0, 1]
    scatter = ax2.scatter(
        df["road_quality_score"],
        df["pothole_count"],
        c=df[target_col],
        cmap="coolwarm",
        alpha=0.45,
        edgecolors="none",
        s=20,
    )
    ax2.set_title("Road Quality Score vs Pothole Count", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Road Quality Score (0.0=Poor, 1.0=Pristine)")
    ax2.set_ylabel("Pothole Count")
    fig.colorbar(scatter, ax=ax2, label="Failure Next 30d")

    # Plot 3: 30-Day Rainfall by Failure Status
    ax3 = axes[1, 0]
    df.boxplot(column="rainfall_30d_mm", by=target_col, ax=ax3)
    ax3.set_title("30-Day Cumulative Rainfall Distribution by Failure", fontsize=12, fontweight="bold")
    ax3.set_xlabel("Failure in Next 30d (0=No, 1=Yes)")
    ax3.set_ylabel("Precipitation (mm)")
    plt.suptitle("")  # Clear default boxplot title

    # Plot 4: Top Feature Correlations with Failure
    ax4 = axes[1, 1]
    top_corrs = pd.Series(correlations).head(8)
    top_corrs.plot(kind="barh", ax=ax4, color="#337ab7")
    ax4.set_title("Top Correlated Features with Road Failure", fontsize=12, fontweight="bold")
    ax4.set_xlabel("Pearson Correlation Coefficient")
    ax4.invert_yaxis()

    plt.tight_layout()
    plot_path = output_dir / "eda_diagnostic_summary.png"
    plt.savefig(plot_path, dpi=200)
    plt.close()
    logger.info("Saved EDA diagnostic plot to: %s", plot_path)

    # Print summary to console
    print("\n" + "=" * 60)
    print("ROADX FAILURE PREDICTION — EDA SUMMARY")
    print("=" * 60)
    print(f"Dataset: {data_path}")
    print(f"Dimensions: {n_rows} rows x {n_cols} columns")
    print(f"Missing Values: {total_missing} | Duplicates: {n_duplicates}")
    print(f"Target Distribution: Class 0: {class_counts.get(0, 0)} | Class 1: {class_counts.get(1, 0)} ({failure_pct:.2f}%)")
    print("\nTop Correlations with Failure Next 30 Days:")
    for feat, corr in list(correlations.items())[:6]:
        print(f"  - {feat:25s}: {corr:+.4f}")
    print(f"\nDiagnostic visualizations saved to: {plot_path}")
    print("=" * 60 + "\n")

    return summary_stats


def main() -> None:
    """CLI script entrypoint for running EDA."""
    parser = argparse.ArgumentParser(description="Run EDA on road failure dataset.")
    parser.add_argument("--data", type=str, default=str(failure_config.raw_data_path))
    parser.add_argument("--out", type=str, default=str(settings.project_root / "reports" / "eda"))
    args = parser.parse_args()

    perform_eda(data_path=Path(args.data), output_dir=Path(args.out))


if __name__ == "__main__":
    main()
