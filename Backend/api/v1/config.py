import os
from pathlib import Path

from dotenv import load_dotenv

# Load Backend/.env (works even when uvicorn is started from another cwd)
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND_ROOT / ".env")


def is_mock_mode() -> bool:
    return os.getenv("API_V1_MOCK_MODE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
