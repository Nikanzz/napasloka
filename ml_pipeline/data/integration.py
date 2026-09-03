"""Integrate pollutant and meteorological records by location and datetime."""

import pandas as pd


def integrate_pollutant_and_weather(
    pollutant_frame: pd.DataFrame,
    weather_frame: pd.DataFrame,
) -> pd.DataFrame:
    """Perform a validated inner join without silently reconciling coordinates."""

    keys = ["location", "datetime"]
    for label, frame in (("pollutant", pollutant_frame), ("weather", weather_frame)):
        missing = sorted(set(keys).difference(frame.columns))
        if missing:
            raise ValueError(f"{label} data is missing integration keys: {missing}")

    merged = pollutant_frame.merge(
        weather_frame,
        on=keys,
        how="inner",
        validate="one_to_one",
        suffixes=("", "_weather"),
    )
    for coordinate in ("latitude", "longitude"):
        weather_coordinate = f"{coordinate}_weather"
        if coordinate in merged and weather_coordinate in merged:
            mismatch = ~merged[coordinate].eq(merged[weather_coordinate])
            if mismatch.any():
                raise ValueError(f"Coordinate mismatch detected for {coordinate}")
            merged = merged.drop(columns=weather_coordinate)
    return merged
