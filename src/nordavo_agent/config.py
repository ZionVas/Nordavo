from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_API_URL = "https://nakywgkztvzkihdjnwbc.supabase.co/functions/v1/helpdesk"


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key and key.replace("_", "").isalnum() and key not in os.environ:
            os.environ[key] = value.strip("'\"")


@dataclass(frozen=True)
class Settings:
    api_key: str
    candidate_email: str
    candidate_name: str | None
    api_url: str

    @classmethod
    def from_environment(cls) -> Settings:
        load_dotenv()
        api_key = os.getenv("HELPDESK_API_KEY", "").strip()
        candidate_email = os.getenv("CANDIDATE_EMAIL", "").strip()
        missing = [
            name
            for name, value in (
                ("HELPDESK_API_KEY", api_key),
                ("CANDIDATE_EMAIL", candidate_email),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        return cls(
            api_key=api_key,
            candidate_email=candidate_email,
            candidate_name=os.getenv("CANDIDATE_NAME", "").strip() or None,
            api_url=os.getenv("HELPDESK_API_URL", DEFAULT_API_URL).rstrip("/"),
        )
