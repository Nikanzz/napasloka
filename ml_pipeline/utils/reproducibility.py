"""Reproducibility helpers shared by experiment entry points."""

import os
import random

import numpy as np


def set_random_seed(seed: int) -> None:
    """Seed Python and NumPy; estimator-specific seeds remain model parameters."""

    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
