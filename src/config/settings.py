import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

class Settings:
    def __init__(self):
        self.LITELLM_TOKEN = os.getenv("LITELLM_TOKEN", "")
        self.LITELLM_BASE_URL = os.getenv(
            "LITELLM_BASE_URL",
            "https://litellm.oit.duke.edu/v1",
        )
        self.LITELLM_MODEL = os.getenv("LITELLM_MODEL", "GPT 4.1 Mini")

        self.LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
        self.LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        self.HISTORY_DB_PATH = os.getenv(
            "HISTORY_DB_PATH",
            str(Path(__file__).resolve().parents[2] / "project_history.db"),
        )


settings = Settings()
