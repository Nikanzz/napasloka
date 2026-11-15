import csv
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clean_data")

# Validate that all required raw data files exist
def validate_raw_files_exist(raw_weather_path, raw_co_path, raw_co2_path):
    required_files = [
        (raw_weather_path, "Raw weather"),
        (raw_co_path, "Raw CO"),
        (raw_co2_path, "Raw CO2"),
    ]
    for file_path, description in required_files:
        if not file_path.exists():
            raise FileNotFoundError(
                f"{description} file not found: {file_path}. Run 'python -m src.data.fetch_data' first."
            )

def load_and_deduplicate_weather(raw_weather_path):
    weather_lookup = {}
    duplicate_count = 0

    with raw_weather_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if not row:
                continue
            location_id, timestamp = row[0], row[3]
            key = (location_id, timestamp)
            if key in weather_lookup:
                duplicate_count += 1
            weather_lookup[key] = row[1:]

    return weather_lookup


def integrate_pollutant_data(raw_pollutant_path, weather_lookup, pollutant_column_name, output_path):
    rows_written = 0
    seen_keys = set()
    header = [
        "location", "latitude", "longitude", "datetime",
        "temperature_2m", "relative_humidity_2m", "rain", "wind_speed_100m",
        pollutant_column_name
    ]

    with raw_pollutant_path.open("r", encoding="utf-8") as f_in, output_path.open("w", newline="", encoding="utf-8") as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        next(reader)
        writer.writerow(header)

        for row in reader:
            if not row:
                continue
            location_id, timestamp, pollutant_value = row[0], row[3], row[4]
            key = (location_id, timestamp)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            if key in weather_lookup:
                weather_vals = weather_lookup[key]
                output_row = [
                    location_id,
                    weather_vals[0],
                    weather_vals[1],
                    timestamp,
                    weather_vals[3],
                    weather_vals[4],
                    weather_vals[5],
                    weather_vals[6],
                    pollutant_value,
                ]
                writer.writerow(output_row)
                rows_written += 1

    return rows_written


def verify_and_impute_missing_values(dataset_path, pollutant_name):
    frame = pd.read_csv(dataset_path)
    numeric_columns = list(frame.select_dtypes(include="number").columns)
    missing_count = int(frame[numeric_columns].isna().sum().sum())

    if missing_count == 0:
        logger.info(f"Missing value check for {pollutant_name}: Complete (0 missing values), imputation skipped.")
        return frame

    logger.info(f"Found {missing_count} missing values in {pollutant_name}. Applying causal forward fill per location...")
    frame = frame.sort_values(["location", "datetime"]).reset_index(drop=True)
    frame[numeric_columns] = frame.groupby("location")[numeric_columns].ffill()
    frame.to_csv(dataset_path, index=False)
    return frame


def clean_and_integrate_data():
    raw_weather_path = DATA_DIR / "raw" / "weather" / "weather_raw.csv"
    raw_co_path = DATA_DIR / "raw" / "air_quality" / "co_raw.csv"
    raw_co2_path = DATA_DIR / "raw" / "air_quality" / "co2_raw.csv"

    validate_raw_files_exist(raw_weather_path, raw_co_path, raw_co2_path)

    processed_dir = DATA_DIR / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_co_path = processed_dir / "jabodetabek_co_dataset.csv"
    out_co2_path = processed_dir / "jabodetabek_co2_dataset.csv"

    weather_lookup = load_and_deduplicate_weather(raw_weather_path)

    integrate_pollutant_data(raw_co_path, weather_lookup, "carbon_monoxide", out_co_path)
    integrate_pollutant_data(raw_co2_path, weather_lookup, "carbon_dioxide", out_co2_path)

    df_co = verify_and_impute_missing_values(out_co_path, "CO")
    df_co2 = verify_and_impute_missing_values(out_co2_path, "CO2")

    return df_co, df_co2


def main():
    clean_and_integrate_data()


if __name__ == "__main__":
    main()
