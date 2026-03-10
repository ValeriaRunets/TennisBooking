import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
AUTHORIZED_CHAT_ID: int = int(os.environ.get("AUTHORIZED_CHAT_ID", "0"))
POLL_INTERVAL_MINUTES: int = int(os.environ.get("POLL_INTERVAL_MINUTES", "15"))
STATE_FILE_PATH: Path = Path(os.environ.get("STATE_FILE_PATH", "data/state.json"))
BROWSER_DATA_DIR: Path = Path(os.environ.get("BROWSER_DATA_DIR", "browser_data/"))
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

LOCATIONS_FILE: Path = Path(__file__).parent / "locations.json"
