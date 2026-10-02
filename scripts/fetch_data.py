"""Script untuk mengunduh data mentah (cuaca dan polutan) dari Open-Meteo API ke data/raw/."""

import argparse
import logging
import sys
from pathlib import Path
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml_pipeline.utils.config import load_yaml_config
from ml_pipeline.utils.paths import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def fetch_raw_data() -> None:
    """Mengunduh data mentah dari Open-Meteo dan menyimpannya ke data/raw/."""
    config = load_yaml_config("locations.yaml")
    locations = config.get("locations", [])
    if not locations:
        raise ValueError("locations.yaml kosong. Pastikan lokasi telah disahkan.")

    logging.info(f"Ditemukan {len(locations)} lokasi dari konfigurasi.")

    START_DATE = "2024-10-26"
    END_DATE = "2026-08-04"
    TIMEZONE = "Asia/Bangkok"

    weather_url = "https://archive-api.open-meteo.com/v1/archive"
    air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

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
                "wind_speed_100m"
            ],
            "timezone": TIMEZONE
        }

        weather_response = openmeteo.weather_api(weather_url, params=weather_params)[0]
        weather_hourly = weather_response.Hourly()

        w_df = pd.DataFrame({
            "location": location_id,
            "latitude": lat,
            "longitude": lon,
            "datetime": pd.date_range(
                start=pd.to_datetime(weather_hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(weather_hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=weather_hourly.Interval()),
                inclusive="left"
            ).tz_convert(TIMEZONE),
            "temperature_2m": weather_hourly.Variables(0).ValuesAsNumpy(),
            "relative_humidity_2m": weather_hourly.Variables(1).ValuesAsNumpy(),
            "rain": weather_hourly.Variables(2).ValuesAsNumpy(),
            "wind_speed_100m": weather_hourly.Variables(3).ValuesAsNumpy(),
        })

        # 2. Air quality (CO)
        co_params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ["carbon_monoxide"],
            "domains": "cams_global",
            "start_date": START_DATE,
            "end_date": END_DATE,
            "timezone": TIMEZONE
        }

        co_response = openmeteo.weather_api(air_url, params=co_params)[0]
        co_hourly = co_response.Hourly()

        co_df = pd.DataFrame({
            "location": location_id,
            "latitude": lat,
            "longitude": lon,
            "datetime": pd.date_range(
                start=pd.to_datetime(co_hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(co_hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=co_hourly.Interval()),
                inclusive="left"
            ).tz_convert(TIMEZONE),
            "carbon_monoxide": co_hourly.Variables(0).ValuesAsNumpy(),
        })

        # 3. Air quality (CO2)
        co2_params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ["carbon_dioxide"],
            "domains": "cams_global",
            "start_date": START_DATE,
            "end_date": END_DATE,
            "timezone": TIMEZONE
        }

        co2_response = openmeteo.weather_api(air_url, params=co2_params)[0]
        co2_hourly = co2_response.Hourly()

        co2_df = pd.DataFrame({
            "location": location_id,
            "latitude": lat,
            "longitude": lon,
            "datetime": pd.date_range(
                start=pd.to_datetime(co2_hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(co2_hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=co2_hourly.Interval()),
                inclusive="left"
            ).tz_convert(TIMEZONE),
            "carbon_dioxide": co2_hourly.Variables(0).ValuesAsNumpy(),
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
    all_weather_df = all_weather_df[all_weather_df["datetime"] >= start_datetime].reset_index(drop=True)
    all_co_df = all_co_df[all_co_df["datetime"] >= start_datetime].reset_index(drop=True)
    all_co2_df = all_co2_df[all_co2_df["datetime"] >= start_datetime].reset_index(drop=True)

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
    logging.info("Gunakan skrip 'python scripts/preprocess_data.py' untuk memproses dan mengintegrasikan dataset.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Unduh data mentah cuaca dan kualitas udara dari Open-Meteo.")
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Jalankan otomatis tahap preprocessing & integrasi setelah selesai mengunduh data mentah.",
    )
    args = parser.parse_args()

    fetch_raw_data()

    if args.preprocess:
        logging.info("Menjalankan pipeline preprocessing otomatis...")
        from scripts.preprocess_data import preprocess_and_integrate
        preprocess_and_integrate()


if __name__ == "__main__":
    main()
