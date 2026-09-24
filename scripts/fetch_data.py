import logging
import sys
from pathlib import Path
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry

# Tambahkan root directory ke sys.path agar bisa mengimpor module lokal
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml_pipeline.utils.config import load_yaml_config
from ml_pipeline.utils.paths import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> None:
    # 1. Baca konfigurasi lokasi
    config = load_yaml_config("locations.yaml")
    locations = config.get("locations", [])
    if not locations:
        raise ValueError("locations.yaml kosong. Pastikan lokasi telah disahkan.")

    logging.info(f"Ditemukan {len(locations)} lokasi dari konfigurasi.")

    # 2. Parameter waktu
    START_DATE = "2024-10-26"
    END_DATE = "2026-08-04"
    TIMEZONE = "Asia/Bangkok"  

    weather_url = "https://archive-api.open-meteo.com/v1/archive"
    air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    # 3. Setup Open-Meteo Client
    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    co_data_list = []
    co2_data_list = []

    for loc in locations:
        name = loc["name"]
        lat = loc["latitude"]
        lon = loc["longitude"]

        logging.info(f"Mengunduh data untuk {name} ({lat}, {lon})...")

        # ===========================
        # WEATHER
        # ===========================
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

        weather_df = pd.DataFrame({
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

        # ===========================
        # AIR QUALITY (CO)
        # ===========================
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
            "datetime": pd.date_range(
                start=pd.to_datetime(co_hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(co_hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=co_hourly.Interval()),
                inclusive="left"
            ).tz_convert(TIMEZONE),
            "carbon_monoxide": co_hourly.Variables(0).ValuesAsNumpy(),
        })

        # ===========================
        # AIR QUALITY (CO2)
        # ===========================
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
            "datetime": pd.date_range(
                start=pd.to_datetime(co2_hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(co2_hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=co2_hourly.Interval()),
                inclusive="left"
            ).tz_convert(TIMEZONE),
            "carbon_dioxide": co2_hourly.Variables(0).ValuesAsNumpy(),
        })

        # ===========================
        # MERGE
        # ===========================
        df_co = pd.merge(weather_df, co_df, on="datetime", how="inner")
        df_co2 = pd.merge(weather_df, co2_df, on="datetime", how="inner")

        df_co["location"] = name
        df_co["latitude"] = lat
        df_co["longitude"] = lon

        df_co2["location"] = name
        df_co2["latitude"] = lat
        df_co2["longitude"] = lon

        co_data_list.append(df_co)
        co2_data_list.append(df_co2)

    # 4. Finalisasi Dataset
    co_final_df = pd.concat(co_data_list, ignore_index=True)
    co2_final_df = pd.concat(co2_data_list, ignore_index=True)

    cols_co = [
        "location", "latitude", "longitude", "datetime",
        "temperature_2m", "relative_humidity_2m", "rain", "wind_speed_100m",
        "carbon_monoxide"
    ]
    cols_co2 = [
        "location", "latitude", "longitude", "datetime",
        "temperature_2m", "relative_humidity_2m", "rain", "wind_speed_100m",
        "carbon_dioxide"
    ]

    co_final_df = co_final_df[cols_co]
    co2_final_df = co2_final_df[cols_co2]

    # Pastikan data dimulai dari 26 Oktober 2024 pukul 07.00
    start_datetime = pd.Timestamp("2024-10-26 07:00:00", tz=TIMEZONE)
    co_final_df = co_final_df[co_final_df["datetime"] >= start_datetime].reset_index(drop=True)
    co2_final_df = co2_final_df[co2_final_df["datetime"] >= start_datetime].reset_index(drop=True)

    # 5. Simpan ke data/processed/
    processed_dir = DATA_DIR / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    co_path = processed_dir / "jabodetabek_co_dataset.csv"
    co2_path = processed_dir / "jabodetabek_co2_dataset.csv"

    co_final_df.to_csv(co_path, index=False)
    co2_final_df.to_csv(co2_path, index=False)

    logging.info(f"Selesai! Data CO tersimpan di: {co_path} (Ukuran: {co_final_df.shape})")
    logging.info(f"Selesai! Data CO2 tersimpan di: {co2_path} (Ukuran: {co2_final_df.shape})")


if __name__ == "__main__":
    main()
