import json
import logging
from datetime import datetime, timezone

import joblib
import pandas as pd

from src.features.lag_features import create_lag_features
from src.features.scenarios import resolve_scenario
from src.models.estimators import create_estimator, predict, tune_on_training_set
from src.models.interpretation import calculate_tree_shap, gain_feature_importance, mean_absolute_shap
from src.utils.config import DATA_DIR, EXPERIMENTS_DIR, load_yaml_config
from src.utils.identifiers import build_experiment_id, slugify_component
from src.utils.metrics import PerformanceTimer, calculate_regression_metrics

logger = logging.getLogger("experiments")

SUPPORTED_POLLUTANTS = {"co", "co2"}
SUPPORTED_SCENARIOS = {"scenario_1", "scenario_2"}
SUPPORTED_ALGORITHMS = {"xgboost", "lightgbm"}


def build_experiment_matrix():
    locations = load_yaml_config("locations.yaml").get("locations", [])
    pollutants = load_yaml_config("project.yaml").get("pollutants", {})
    scenarios = load_yaml_config("features.yaml").get("scenarios", {})
    algorithms = load_yaml_config("project.yaml").get("algorithms", [])

    experiments = []
    for location in locations:
        loc_id = slugify_component(location.get("id", ""))
        if not loc_id:
            continue
        for pollutant in pollutants:
            pol = pollutant.lower()
            for scenario in scenarios:
                scen = scenario.lower()
                for algorithm in algorithms:
                    algo = algorithm.lower()
                    exp_id = build_experiment_id(loc_id, pol, scen, algo)
                    artifact_dir = EXPERIMENTS_DIR / loc_id / pol / scen / algo
                    experiments.append({
                        "location": loc_id,
                        "pollutant": pol,
                        "scenario": scen,
                        "algorithm": algo,
                        "experiment_id": exp_id,
                        "artifact_dir": artifact_dir,
                        "artifact_directory": artifact_dir,
                    })
    return experiments


def _get_coordinate_id(location_id):
    locations = load_yaml_config("locations.yaml").get("locations", [])
    for loc in locations:
        if loc.get("id") == location_id:
            return f"{loc['latitude']}_{loc['longitude']}"
    return location_id


DATASET_CACHE = {}
def get_dataset(pollutant_or_file):
    """ Getting data with idempotency """
    if str(pollutant_or_file).endswith(".csv"):
        filename = str(pollutant_or_file)
    else:
        filename = "jabodetabek_co_dataset.csv" if pollutant_or_file == "co" else "jabodetabek_co2_dataset.csv"

    if filename not in DATASET_CACHE:
        path = DATA_DIR / "processed" / filename
        if not path.exists():
            raise FileNotFoundError(f"Processed dataset not found: {path}")
        df = pd.read_csv(path)
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert("Asia/Jakarta")
        DATASET_CACHE[filename] = df

    return DATASET_CACHE[filename]


def chronological_train_test_split(frame, test_fraction=0.2):
    """Split the data based on chronological order without shuffling"""
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    split_index = int(len(frame) * (1 - test_fraction))
    if split_index == 0 or split_index == len(frame):
        raise ValueError("Dataset is too small for the requested split")
    return frame.iloc[:split_index].copy(), frame.iloc[split_index:].copy()

def execute_single_experiment(location, pollutant, scenario, algorithm):
    """Executing a single experiment end-to-end (from getting data until generating artifacts for summary)"""
    if isinstance(location, dict):
        item = location
        location = item["location"]
        pollutant = item["pollutant"]
        scenario = item["scenario"]
        algorithm = item["algorithm"]

    if not all([location, pollutant, scenario, algorithm]):
        raise ValueError("location, pollutant, scenario, and algorithm must all be provided.")

    loc_slug = slugify_component(location)
    pollutant = pollutant.lower()
    scenario = scenario.lower()
    algorithm = algorithm.lower()

    experiment_id = build_experiment_id(loc_slug, pollutant, scenario, algorithm)
    artifact_dir = EXPERIMENTS_DIR / loc_slug / pollutant / scenario / algorithm

    # 1. Load data
    df = get_dataset(pollutant)

    # 2. Filter location using coordinate string or slug
    coord_id = _get_coordinate_id(loc_slug)
    df = df[(df["location"] == coord_id) | (df["location"] == loc_slug)].copy()
    if df.empty:
        raise ValueError(f"No observation data found for location: {loc_slug}")

    df = df.sort_values("datetime").reset_index(drop=True)

    # 3. Create lag features for the specified scenario
    scenario_def = resolve_scenario(pollutant, scenario)
    df = create_lag_features(
        df,
        pollutant=pollutant,
        scenario=scenario,
        drop_incomplete_rows=True,
    )

    features = list(scenario_def.feature_names)
    target = scenario_def.pollutant_column

    # 4. Chronological train-test split without shuffling
    train_df, test_df = chronological_train_test_split(df, test_fraction=0.2)
    x_train, y_train = train_df[features], train_df[target]
    x_test, y_test = test_df[features], test_df[target]

    # 5. Create and tune model on training set
    model = create_estimator(algorithm, parameters={"random_state": 42})
    with PerformanceTimer() as timer:
        search = tune_on_training_set(model, algorithm, x_train, y_train)

    best_model = search.best_estimator_
    training_time = timer.elapsed_seconds or 0.0

    # 6. Predict and evaluate
    result = predict(best_model, x_test)
    metrics = calculate_regression_metrics(y_test, result.values)
    metrics["training_time_seconds"] = training_time
    metrics["prediction_time_seconds"] = result.prediction_time_seconds

    # 7. Calculate TreeSHAP and gain importance
    shap_values = calculate_tree_shap(best_model, x_test)
    shap_df = mean_absolute_shap(shap_values, features)
    gain_df = gain_feature_importance(best_model, features, normalize=True)

    # 8. Save experiment artifacts directly
    artifact_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, artifact_dir / "model.joblib")
    with open(artifact_dir / "best_params.json", "w", encoding="utf-8") as f:
        json.dump(search.best_params_, f, indent=2)
    with open(artifact_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    pd.DataFrame({
        "datetime": test_df["datetime"].astype(str),
        "actual": y_test.values,
        "predicted": result.values,
        "residual": y_test.values - result.values,
    }).to_csv(artifact_dir / "predictions.csv", index=False)
    shap_df.to_csv(artifact_dir / "shap_global.csv", index=False)
    gain_df.to_csv(artifact_dir / "feature_importance.csv", index=False)
    metadata = {
        "experiment_id": experiment_id,
        "location": loc_slug,
        "pollutant": pollutant,
        "scenario": scenario,
        "algorithm": algorithm,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "best_params": search.best_params_,
        "features": features,
        "n_train_samples": len(train_df),
        "n_test_samples": len(test_df),
    }

    with open(artifact_dir / "experiment_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metrics

def run_experiments(specs=None, force=False):
    """For orchestrating the execution of multiple experiments in batch"""
    if specs is None:
        specs = build_experiment_matrix()

    total = len(specs)
    logger.info(f"Starting execution of {total} research experiments...")

    for index, item in enumerate(specs, start=1):
        artifact_dir = item["artifact_dir"]
        exp_id = item["experiment_id"]
        metrics_file = artifact_dir / "metrics.json"

        if metrics_file.exists() and not force:
            logger.info(f"[{index}/{total}] SKIPPED: {exp_id}")
            continue

        logger.info(f"[{index}/{total}] RUNNING: {exp_id}")
        execute_single_experiment(
            location=item["location"],
            pollutant=item["pollutant"],
            scenario=item["scenario"],
            algorithm=item["algorithm"],
        )
        logger.info(f"[{index}/{total}] FINISHED: {exp_id}")

    logger.info("Batch execution finished!")


