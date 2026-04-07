from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    ark_api_key: str | None
    ark_base_url: str
    default_model: str
    default_draft_model: str
    output_dir: Path
    poll_interval_seconds: int
    timeout_seconds: int
    flex_timeout_seconds: int

    def timeout_for(self, service_tier: str | None) -> int:
        if service_tier == "flex":
            return self.flex_timeout_seconds
        return self.timeout_seconds


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        ark_api_key=os.getenv("ARK_API_KEY"),
        ark_base_url=os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        default_model=os.getenv("SEEDANCE_DEFAULT_MODEL", "doubao-seedance-2-0-260128"),
        default_draft_model=os.getenv(
            "SEEDANCE_DEFAULT_DRAFT_MODEL", "doubao-seedance-1-5-pro-251215"
        ),
        output_dir=Path(os.getenv("SEEDANCE_OUTPUT_DIR", "outputs/seedance")),
        poll_interval_seconds=int(os.getenv("SEEDANCE_POLL_INTERVAL_SECONDS", "10")),
        timeout_seconds=int(os.getenv("SEEDANCE_TIMEOUT_SECONDS", "1800")),
        flex_timeout_seconds=int(os.getenv("SEEDANCE_FLEX_TIMEOUT_SECONDS", "21600")),
    )
