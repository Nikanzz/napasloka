"""Script untuk mengunduh data mentah (cuaca dan polutan) dari Open-Meteo API ke data/raw/."""

import argparse
import logging
import sys
from pathlib import Path
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from typing import Any, cast

from src.utils.config import DATA_DIR, load_yaml_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _extract_hourly_data(
    response: Any,
    variable_indices: list[int],
    timezone: str,
) -> tuple[pd.DatetimeIndex, list[np.ndarray]]:
    """Safely unpack hourly time range and numpy variables from Open-Meteo response."""
    hourly = response.Hourly()
    if hourly is None:
        raise ValueError("Open-Meteo API response does not contain hourly observations.")

    time_index = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    ).tz_convert(timezone)

    arrays = []
    for idx in variable_indices:
        var = hourly.Variables(idx)
        if var is None:
            raise ValueError(f"Open-Meteo response missing hourly variable at index {idx}.")
        arrays.append(var.ValuesAsNumpy())

    return time_index, arrays


def fetch_raw_data() -> None:
    """Mengunduh data mentah dari Open-Meteo dan menyimpannya ke data/raw/."""
    config = load_yaml_config("locations.yaml")
    locations = config.get("locations", [])
    if not locations:
        raise ValueError("locations.yaml kosong. Pastikan lokasi telah disahkan.")

    logging.info(f"Ditemukan {len(locations)} lokasi dari konfigurasi.")

    START_DATE = "2024-10-26"
    END_DATE = "2026-10-26"
    TIMEZONE = "Asia/Bangkok"

    weather_url = "https://archive-api.open-meteo.com/v1/archive"
    air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=cast(Any, retry_session))

    weather_list = []
    co_list = []
    co2_list = []

    for loc in locations:
        name = loc["name"]
        lat = loc["latitude"]
        lon = loc["longitude"]
        location_id = f"{lat}_{lon}"

        logging.info(f"Mengunduh data mentah untuk {name} ({lat}, {lon})...")

        # 1. Weather data
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "hourly": [
                "temperature_2m",
                "relative_humidity_2m",
                "rain",
                "wind_speed_100m",
            ],
            "timezone": TIMEZONE,
        }

        weather_response = openmeteo.weather_api(weather_url, params=weather_params)[0]
        w_dt_index, (w_temp, w_rh, w_rain, w_wind) = _extract_hourly_data(
            weather_response, [0, 1, 2, 3], TIMEZONE
        )
        w_df = pd.DataFrame({
            "location": location_id,
            "latitude": lat,
            "longitude": lon,
            "datetime": w_dt_index,
            "temperature_2m": w_temp,
            "relative_humidity_2m": w_rh,
            "rain": w_rain,
            "wind_speed_100m": w_wind,
        })

        # 2. Air quality (CO)
        co_params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ["carbon_monoxide"],
            "domains": "cams_global",
            "start_date": START_DATE,
            "end_date": END_DATE,
            "timezone": TIMEZONE,
        }

        co_response = openmeteo.weather_api(air_url, params=co_params)[0]
        co_dt_index, (co_vals,) = _extract_hourly_data(co_response, [0], TIMEZONE)
        co_df = pd.DataFrame({
            "location": location_id,
            "latitude": lat,
            "longitude": lon,
            "datetime": co_dt_index,
            "carbon_monoxide": co_vals,
        })

        # 3. Air quality (CO2)
        co2_params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ["carbon_dioxide"],
            "domains": "cams_global",
            "start_date": START_DATE,
            "end_date": END_DATE,
            "timezone": TIMEZONE,
        }

        co2_response = openmeteo.weather_api(air_url, params=co2_params)[0]
        co2_dt_index, (co2_vals,) = _extract_hourly_data(co2_response, [0], TIMEZONE)
        co2_df = pd.DataFrame({
            "location": location_id,
            "latitude": lat,
            "longitude": lon,
            "datetime": co2_dt_index,
            "carbon_dioxide": co2_vals,
        })

        weather_list.append(w_df)
        co_list.append(co_df)
        co2_list.append(co2_df)

    # Gabungkan seluruh lokasi per kategori mentah
    all_weather_df = pd.concat(weather_list, ignore_index=True)
    all_co_df = pd.concat(co_list, ignore_index=True)
    all_co2_df = pd.concat(co2_list, ignore_index=True)

    # Filter rentang waktu riset
    start_datetime = pd.Timestamp("2024-10-26 07:00:00", tz=TIMEZONE)
    now_datetime = pd.Timestamp.now(tz=TIMEZONE)
    all_weather_df = all_weather_df[
        (all_weather_df["datetime"] >= start_datetime) & (all_weather_df['datetime'] <= now_datetime)].reset_index(drop=True)
    all_co_df = all_co_df[
        (all_co_df["datetime"] >= start_datetime) & (all_co_df["datetime"] <= now_datetime)].reset_index(drop=True)
    all_co2_df = all_co2_df[
        (all_co2_df["datetime"] >= start_datetime) & (all_co2_df["datetime"] <= now_datetime)].reset_index(drop=True)

    # Direktori target penyimpanan data mentah
    raw_weather_dir = DATA_DIR / "raw" / "weather"
    raw_air_dir = DATA_DIR / "raw" / "air_quality"
    raw_weather_dir.mkdir(parents=True, exist_ok=True)
    raw_air_dir.mkdir(parents=True, exist_ok=True)

    raw_weather_path = raw_weather_dir / "weather_raw.csv"
    raw_co_path = raw_air_dir / "co_raw.csv"
    raw_co2_path = raw_air_dir / "co2_raw.csv"

    all_weather_df.to_csv(raw_weather_path, index=False)
    all_co_df.to_csv(raw_co_path, index=False)
    all_co2_df.to_csv(raw_co2_path, index=False)

    logging.info(f"Selesai! Data cuaca mentah tersimpan di: {raw_weather_path} (Ukuran: {all_weather_df.shape})")
    logging.info(f"Selesai! Data CO mentah tersimpan di: {raw_co_path} (Ukuran: {all_co_df.shape})")
    logging.info(f"Selesai! Data CO2 mentah tersimpan di: {raw_co2_path} (Ukuran: {all_co2_df.shape})")
    logging.info("Gunakan modul 'python -m src.data.clean_data' untuk memproses dan mengintegrasikan dataset.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Unduh data mentah cuaca dan kualitas udara dari Open-Meteo.")
    parser.add_argument(
        "--clean",
        "--preprocess",
        dest="clean",
        action="store_true",
        help="Jalankan otomatis pembersihan, validasi & integrasi data setelah selesai mengunduh.",
    )
    args = parser.parse_args()

    fetch_raw_data()

    if args.clean:
        logging.info("Menjalankan pipeline pembersihan & integrasi otomatis...")
        from src.data.clean_data import clean_and_integrate_data
        clean_and_integrate_data()


if __name__ == "__main__":
    main()
