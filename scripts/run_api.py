"""Run the local FastAPI development server."""

import os
import sys
from pathlib import Path

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host=os.getenv("NAPASLOKA_API_HOST", "127.0.0.1"),
        port=int(os.getenv("NAPASLOKA_API_PORT", "8000")),
        reload=True,
    )
