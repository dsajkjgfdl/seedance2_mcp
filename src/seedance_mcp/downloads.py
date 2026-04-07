from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx

from .config import get_settings


def build_output_path(task_id: str, output_dir: str | None = None) -> Path:
    base_dir = Path(output_dir) if output_dir else get_settings().output_dir
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"{task_id}.mp4"
    if not path.exists():
        return path
    suffix = datetime.now().strftime("%Y%m%d%H%M%S")
    return base_dir / f"{task_id}-{suffix}.mp4"


async def download_video_file(url: str, task_id: str, output_dir: str | None = None) -> str:
    path = build_output_path(task_id=task_id, output_dir=output_dir)
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=30.0)) as client:
        async with client.stream("GET", url, follow_redirects=True) as response:
            response.raise_for_status()
            with path.open("wb") as file_handle:
                async for chunk in response.aiter_bytes():
                    file_handle.write(chunk)
    return str(path)
