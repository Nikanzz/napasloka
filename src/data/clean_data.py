import argparse
import csv
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clean_data")

# 1. Quality Validation Logic

@dataclass(frozen=True)
class ValidationReport:
    """Quality and integrity metrics from inspecting a dataset."""

    duplicate_timestamps: int
    missing_values: dict[str, int]
    invalid_values: dict[str, int]

    @property
    def is_valid(self) -> bool:
        return not (
            self.duplicate_timestamps
            or any(self.missing_values.values())
            or any(self.invalid_values.values())
        )


def validate_frame(frame: pd.DataFrame) -> ValidationReport:
    """Inspect a dataframe for duplicate timestamps, missing values, and physical boundary violations."""
    duplicate_keys = ["datetime"]
    if "location" in frame:
        duplicate_keys.insert(0, "location")
    duplicate_count = int(frame.duplicated(subset=duplicate_keys).sum())
    missing = {str(column): int(count) for column, count in frame.isna().sum().items()}

    invalid: dict[str, int] = {}
    lower_bounded = [
        "carbon_monoxide",
        "carbon_dioxide",
        "rain",
        "wind_speed_100m",
    ]
    for column in lower_bounded:
        if column in frame:
            invalid[column] = int((frame[column] < 0).sum())

    if "relative_humidity_2m" in frame:
        humidity = frame["relative_humidity_2m"]
        invalid["relative_humidity_2m"] = int(((humidity < 0) | (humidity > 100)).sum())

    if "latitude" in frame:
        invalid["latitude"] = int(((frame["latitude"] < -90) | (frame["latitude"] > 90)).sum())

    if "longitude" in frame:
        invalid["longitude"] = int(((frame["longitude"] < -180) | (frame["longitude"] > 180)).sum())

    return ValidationReport(duplicate_count, missing, invalid)


# 2. In-Memory Preprocessing & Chronological Splitting Helpers

def standardize_datetime(
    frame: pd.DataFrame,
    *,
    timezone: str = "Asia/Jakarta",
    datetime_column: str = "datetime",
) -> pd.DataFrame:
    """Parse timestamps and localize/convert to standard research timezone."""
    if datetime_column not in frame:
        raise ValueError(f"Missing datetime column: {datetime_column}")
    result = frame.copy()
    parsed = pd.to_datetime(result[datetime_column], errors="raise")
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(timezone, ambiguous="raise", nonexistent="raise")
    else:
        parsed = parsed.dt.tz_convert(timezone)
    result[datetime_column] = parsed
    return result


def sort_chronologically(
    frame: pd.DataFrame,
    *,
    datetime_column: str = "datetime",
) -> pd.DataFrame:
    """Sort chronologically by location and time without modifying source data in-place."""
    columns = [datetime_column]
    if "location" in frame:
        columns.insert(0, "location")
    return frame.sort_values(columns, kind="stable").reset_index(drop=True)


def preprocess_frame(frame: pd.DataFrame, *, timezone: str = "Asia/Jakarta") -> pd.DataFrame:
    """Apply standard datetime localization and chronological ordering."""
    return sort_chronologically(standardize_datetime(frame, timezone=timezone))


def chronological_train_test_split(
    frame: pd.DataFrame,
    *,
    test_fraction: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split an already chronological frame without shuffling (preserves temporal causality)."""
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    split_index = int(len(frame) * (1 - test_fraction))
    if split_index == 0 or split_index == len(frame):
        raise ValueError("Dataset is too small for the requested split")
    return frame.iloc[:split_index].copy(), frame.iloc[split_index:].copy()


# 3. Main Data Cleaning & Integration Pipeline

def clean_and_integrate_data(run_validation: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read raw files, perform inner join, validate physical bounds, and save to data/processed/."""
    raw_weather_path = DATA_DIR / "raw" / "weather" / "weather_raw.csv"
    raw_co_path = DATA_DIR / "raw" / "air_quality" / "co_raw.csv"
    raw_co2_path = DATA_DIR / "raw" / "air_quality" / "co2_raw.csv"

    for path, desc in [
        (raw_weather_path, "Raw weather"),
        (raw_co_path, "Raw CO"),
        (raw_co2_path, "Raw CO2"),
    ]:
        if not path.exists():
            raise FileNotFoundError(f"{desc} file not found: {path}. Run 'python -m src.data.fetch_data' first.")

    processed_dir = DATA_DIR / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_co_path = processed_dir / "jabodetabek_co_dataset.csv"
    out_co2_path = processed_dir / "jabodetabek_co2_dataset.csv"

    logger.info("Memulai pra-pemrosesan, integrasi, dan validasi data...")
    logger.info(f"Membaca data cuaca mentah dari: {raw_weather_path}")

    # Read weather data into memory map: key = (location, datetime) -> (lat, lon, temp, rh, rain, wind)
    weather_data: dict[tuple[str, str], list[str]] = {}
    with raw_weather_path.open("r", encoding="utf-8") as f_w:
        reader = csv.reader(f_w)
        next(reader)  # skip header
        for row in reader:
            if not row:
                continue
            loc, dt = row[0], row[3]
            weather_data[(loc, dt)] = row[1:]

    logger.info(f"Total observasi cuaca termuat: {len(weather_data)}")

    # 1. Integrasi CO
    logger.info(f"Mengintegrasikan data CO mentah dari: {raw_co_path}...")
    co_rows_written = 0
    with raw_co_path.open("r", encoding="utf-8") as f_co, out_co_path.open("w", newline="", encoding="utf-8") as f_out:
        co_reader = csv.reader(f_co)
        co_writer = csv.writer(f_out)
        next(co_reader)  # skip header
        header_co = [
            "location", "latitude", "longitude", "datetime",
            "temperature_2m", "relative_humidity_2m", "rain", "wind_speed_100m",
            "carbon_monoxide"
        ]
        co_writer.writerow(header_co)

        for row in co_reader:
            if not row:
                continue
            loc, dt, co_val = row[0], row[3], row[4]
            key = (loc, dt)
            if key in weather_data:
                w_vals = weather_data[key]
                out_row = [loc, w_vals[0], w_vals[1], dt, w_vals[3], w_vals[4], w_vals[5], w_vals[6], co_val]
                co_writer.writerow(out_row)
                co_rows_written += 1

    logger.info(f"Dataset CO berhasil disimpan di: {out_co_path} ({co_rows_written} baris)")

    # 2. Integrasi CO2
    logger.info(f"Mengintegrasikan data CO2 mentah dari: {raw_co2_path}...")
    co2_rows_written = 0
    with raw_co2_path.open("r", encoding="utf-8") as f_co2, out_co2_path.open("w", newline="", encoding="utf-8") as f_out:
        co2_reader = csv.reader(f_co2)
        co2_writer = csv.writer(f_out)
        next(co2_reader)  # skip header
        header_co2 = [
            "location", "latitude", "longitude", "datetime",
            "temperature_2m", "relative_humidity_2m", "rain", "wind_speed_100m",
            "carbon_dioxide"
        ]
        co2_writer.writerow(header_co2)

        for row in co2_reader:
            if not row:
                continue
            loc, dt, co2_val = row[0], row[3], row[4]
            key = (loc, dt)
            if key in weather_data:
                w_vals = weather_data[key]
                out_row = [loc, w_vals[0], w_vals[1], dt, w_vals[3], w_vals[4], w_vals[5], w_vals[6], co2_val]
                co2_writer.writerow(out_row)
                co2_rows_written += 1

    logger.info(f"Dataset CO2 berhasil disimpan di: {out_co2_path} ({co2_rows_written} baris)")

    # 3. Validasi Integritas Data
    df_co = pd.read_csv(out_co_path)
    df_co2 = pd.read_csv(out_co2_path)

    if run_validation:
        logger.info("Menjalankan validasi kualitas dan batasan fisik dataset...")
        val_co = validate_frame(df_co)
        val_co2 = validate_frame(df_co2)

        total_invalid_co = sum(val_co.invalid_values.values())
        total_invalid_co2 = sum(val_co2.invalid_values.values())

        logger.info(
            f"Validasi CO : Duplikat={val_co.duplicate_timestamps}, "
            f"Missing={sum(val_co.missing_values.values())}, Anomali Fisik={total_invalid_co} (Valid={val_co.is_valid})"
        )
        logger.info(
            f"Validasi CO2: Duplikat={val_co2.duplicate_timestamps}, "
            f"Missing={sum(val_co2.missing_values.values())}, Anomali Fisik={total_invalid_co2} (Valid={val_co2.is_valid})"
        )

    logger.info("Pembersihan, integrasi, dan validasi data selesai dengan sukses!")
    return df_co, df_co2


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean, validate, and integrate raw meteorological and pollutant data into canonical datasets."
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip dataset physical integrity and missing value assertion checks.",
    )
    args = parser.parse_args()
    clean_and_integrate_data(run_validation=not args.skip_validation)


if __name__ == "__main__":
    main()
