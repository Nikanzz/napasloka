"""Non-destructive checks for duplicate timestamps, missing data, and invalid values."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ValidationReport:
    """Counts from validation; remediation remains an explicit research decision."""

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
    """Inspect a dataframe without changing, imputing, or dropping its values."""

    duplicate_keys = ["datetime"]
    if "location" in frame:
        duplicate_keys.insert(0, "location")
    duplicate_count = int(frame.duplicated(subset=duplicate_keys).sum())
    missing = {column: int(count) for column, count in frame.isna().sum().items()}

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
