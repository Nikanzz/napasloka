import re
import unicodedata


def slugify_component(value):
    normalized = unicodedata.normalize("NFKD", str(value).strip().lower())
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9_]+", "-", ascii_value).strip("-")
    if not slug:
        raise ValueError("Experiment identifier components cannot be empty")
    return slug


def build_experiment_id(location, pollutant, scenario, algorithm):
    return "__".join(
        slugify_component(value)
        for value in (location, pollutant, scenario, algorithm)
    )
