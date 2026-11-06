import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.fetch_data import fetch_raw_data
from src.data.clean_data import clean_and_integrate_data
from src.models.train_model import train_experiments, retrain_final_models
from src.models.evaluate_model import generate_summary_report
from src.utils.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pipeline")

FETCH_RAW_DATA = False
FORCE_RETRAIN = False


def check_raw_data_exists():
    """Verify if raw data files are already present on disk."""
    raw_weather = DATA_DIR / "raw" / "weather" / "weather_raw.csv"
    raw_co = DATA_DIR / "raw" / "air_quality" / "co_raw.csv"
    raw_co2 = DATA_DIR / "raw" / "air_quality" / "co2_raw.csv"
    return raw_weather.is_file() and raw_co.is_file() and raw_co2.is_file()


def run_pipeline():
    """Execute complete end-to-end machine learning pipeline sequentially."""

    if FETCH_RAW_DATA or not check_raw_data_exists():
        logger.info("Mengunduh data mentah cuaca dan polutan dari API...")
        fetch_raw_data()
    else:
        logger.info("Data mentah sudah ada di data/raw/ (Ubah FETCH_RAW_DATA=True untuk unduh ulang).")

    clean_and_integrate_data()

    train_experiments(force=FORCE_RETRAIN)

    generate_summary_report()

    retrain_final_models(force=FORCE_RETRAIN)


if __name__ == "__main__":
    run_pipeline()
