"""Preprocess and integrate raw meteorology and air quality datasets into canonical modeling data."""

import argparse
import csv
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml_pipeline.utils.paths import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def preprocess_and_integrate() -> None:
    """Read raw files, perform inner join, validate and save to processed directory."""
    raw_weather_path = DATA_DIR / "raw" / "weather" / "weather_raw.csv"
    raw_co_path = DATA_DIR / "raw" / "air_quality" / "co_raw.csv"
    raw_co2_path = DATA_DIR / "raw" / "air_quality" / "co2_raw.csv"

    for path, desc in [
        (raw_weather_path, "Raw weather"),
        (raw_co_path, "Raw CO"),
        (raw_co2_path, "Raw CO2"),
    ]:
        if not path.exists():
            raise FileNotFoundError(f"{desc} file not found: {path}. Run scripts/fetch_data.py first.")

    processed_dir = DATA_DIR / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_co_path = processed_dir / "jabodetabek_co_dataset.csv"
    out_co2_path = processed_dir / "jabodetabek_co2_dataset.csv"

    logging.info("Memulai pra-pemrosesan dan integrasi data...")
    logging.info(f"Membaca data cuaca mentah dari: {raw_weather_path}")

    # Read weather data into memory map: key = (location, datetime) -> (lat, lon, temp, rh, rain, wind)
    weather_data: dict[tuple[str, str], list[str]] = {}
    with raw_weather_path.open("r", encoding="utf-8") as f_w:
        reader = csv.reader(f_w)
        w_header = next(reader)
        for row in reader:
            if not row:
                continue
            loc, lat, lon, dt = row[0], row[1], row[2], row[3]
            weather_data[(loc, dt)] = row[1:]

    logging.info(f"Total observasi cuaca termuat: {len(weather_data)}")

    # Integrasi CO
    logging.info(f"Mengintegrasikan data CO mentah dari: {raw_co_path}...")
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
            loc, lat, lon, dt, co_val = row[0], row[1], row[2], row[3], row[4]
            key = (loc, dt)
            if key in weather_data:
                w_vals = weather_data[key]  # lat, lon, dt, temp, rh, rain, wind
                # Construct canonical row: location, lat, lon, dt, temp, rh, rain, wind, pollutant
                out_row = [loc, w_vals[0], w_vals[1], dt, w_vals[3], w_vals[4], w_vals[5], w_vals[6], co_val]
                co_writer.writerow(out_row)
                co_rows_written += 1

    logging.info(f"Dataset CO berhasil disimpan di: {out_co_path} ({co_rows_written} baris)")

    # Integrasi CO2
    logging.info(f"Mengintegrasikan data CO2 mentah dari: {raw_co2_path}...")
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
            loc, lat, lon, dt, co2_val = row[0], row[1], row[2], row[3], row[4]
            key = (loc, dt)
            if key in weather_data:
                w_vals = weather_data[key]
                out_row = [loc, w_vals[0], w_vals[1], dt, w_vals[3], w_vals[4], w_vals[5], w_vals[6], co2_val]
                co2_writer.writerow(out_row)
                co2_rows_written += 1

    logging.info(f"Dataset CO2 berhasil disimpan di: {out_co2_path} ({co2_rows_written} baris)")
    logging.info("Pra-pemrosesan & integrasi selesai dengan sukses!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pra-pemrosesan dan integrasi data mentah ke data terproses.")
    args = parser.parse_args()
    preprocess_and_integrate()


if __name__ == "__main__":
    main()
