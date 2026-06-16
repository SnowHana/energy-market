import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error

from config import CLEAN_PARQUET, OUTPUTS_DIR, TEST_WEEKS, RANDOM_SEED
from src.features import build_features, FEATURE_COLS
from src.models import base_predict, train_lgbm, predict_lgbm


def compute_metrics(y_true: pd.Series, y_pred: pd.Series, label: str) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    actual_direction = y_true.diff().dropna()
    pred_direction = y_pred.diff().dropna()
    dir_acc = (np.sign(actual_direction) == np.sign(pred_direction)).mean()
    return {
        "model": label,
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "directional_accuracy": round(float(dir_acc), 4),
    }


def walk_forward(df: pd.DataFrame) -> dict:
    """Expanding-window walk-forward: train up to week w, predict week w, retrain, repeat."""
    week_hours = 7 * 24

    all_lgbm_preds = []
    all_base_preds = []
    all_y_test = []
    last_model = None

    for week in range(TEST_WEEKS, 0, -1):
        cutoff = len(df) - week * week_hours
        train_df = df.iloc[:cutoff]
        test_df = df.iloc[cutoff: cutoff + week_hours]

        X_train = train_df[FEATURE_COLS]
        y_train = train_df["prices"]
        X_test = test_df[FEATURE_COLS]
        y_test = test_df["prices"]

        model = train_lgbm(X_train, y_train)
        lgbm_preds = predict_lgbm(model, X_test)
        base_preds = base_predict(test_df)

        all_lgbm_preds.append(lgbm_preds)
        all_base_preds.append(base_preds)
        all_y_test.append(y_test)
        last_model = model
        print(f"  Week {TEST_WEEKS - week + 1}/{TEST_WEEKS} done")

    y_test_all = pd.concat(all_y_test)
    lgbm_preds_all = pd.concat(all_lgbm_preds)
    base_preds_all = pd.concat(all_base_preds)

    base_metrics = compute_metrics(y_test_all, base_preds_all, "base")
    lgbm_metrics = compute_metrics(y_test_all, lgbm_preds_all, "lgbm")
    skill = round(1 - lgbm_metrics["mae"] / base_metrics["mae"], 4)
    lgbm_metrics["skill"] = skill

    return {
        "base": base_metrics,
        "lgbm": lgbm_metrics,
        "y_test": y_test_all,
        "lgbm_preds": lgbm_preds_all,
        "base_preds": base_preds_all,
        "model": last_model,
    }


def save_metrics(results: dict) -> None:
    metrics = {
        "base": results["base"],
        "lgbm": results["lgbm"],
    }
    Path(OUTPUTS_DIR).mkdir(exist_ok=True)
    with open(f"{OUTPUTS_DIR}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved {OUTPUTS_DIR}/metrics.json")


def save_submission(y_test: pd.Series, lgbm_preds: pd.Series) -> None:
    submission = pd.DataFrame({"id": range(len(y_test)), "y_pred": lgbm_preds.values})
    submission.to_csv(f"{OUTPUTS_DIR}/submission.csv", index=False)
    print(f"Saved {OUTPUTS_DIR}/submission.csv")


def _plot_predicted_vs_actual(y_test, lgbm_preds, base_preds, path):
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(y_test.index, y_test.values, label="Actual", alpha=0.8)
    ax.plot(y_test.index, lgbm_preds.values, label="LightGBM", alpha=0.7)
    ax.plot(y_test.index, base_preds.values, label="Base", alpha=0.5, linestyle="--")
    ax.set_title("Predicted vs Actual — Test Period")
    ax.set_ylabel("€/MWh")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close()


def _plot_error_distribution(y_test, lgbm_preds, path):
    errors = lgbm_preds.values - y_test.values
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(errors, bins=50, edgecolor="black")
    ax.set_title("LightGBM Error Distribution")
    ax.set_xlabel("Prediction Error (€/MWh)")
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close()


def _plot_feature_importance(model, path):
    importance = pd.Series(
        model.feature_importances_, index=FEATURE_COLS
    ).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    importance.plot(kind="barh", ax=ax)
    ax.set_title("LightGBM Feature Importance")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close()


def _plot_mae_by_hour(y_test, lgbm_preds, path):
    hourly_mae = (
        pd.DataFrame({"actual": y_test, "pred": lgbm_preds})
        .assign(error=lambda x: (x["pred"] - x["actual"]).abs())
        .groupby(y_test.index.hour)["error"]
        .mean()
    )
    fig, ax = plt.subplots(figsize=(10, 4))
    hourly_mae.plot(kind="bar", ax=ax)
    ax.set_title("LightGBM MAE by Hour of Day")
    ax.set_xlabel("Hour")
    ax.set_ylabel("MAE (€/MWh)")
    ax.axvspan(7.5, 19.5, alpha=0.1, color="orange", label="Peak hours")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close()


def save_figures(results: dict) -> None:
    figures_dir = Path(f"{OUTPUTS_DIR}/figures")
    figures_dir.mkdir(parents=True, exist_ok=True)

    y_test = results["y_test"]
    lgbm_preds = results["lgbm_preds"]

    _plot_predicted_vs_actual(y_test, lgbm_preds, results["base_preds"], f"{figures_dir}/predicted_vs_actual.png")
    _plot_error_distribution(y_test, lgbm_preds, f"{figures_dir}/error_distribution.png")
    _plot_feature_importance(results["model"], f"{figures_dir}/feature_importance.png")
    _plot_mae_by_hour(y_test, lgbm_preds, f"{figures_dir}/mae_by_hour.png")

    print(f"Saved figures to {figures_dir}/")


def run():
    df = pd.read_parquet(CLEAN_PARQUET)
    df = build_features(df)

    print(f"Running {TEST_WEEKS}-week expanding walk-forward validation...")
    results = walk_forward(df)

    print("\n--- Results ---")
    print(f"Base     MAE: {results['base']['mae']} €/MWh  RMSE: {results['base']['rmse']}")
    print(f"LightGBM MAE: {results['lgbm']['mae']} €/MWh  RMSE: {results['lgbm']['rmse']}")
    print(f"Skill score:  {results['lgbm']['skill']} (positive = beats naive)")
    print(f"Directional accuracy: {results['lgbm']['directional_accuracy']}")

    save_metrics(results)
    save_submission(results["y_test"], results["lgbm_preds"])
    save_figures(results)

    return results


if __name__ == "__main__":
    run()
