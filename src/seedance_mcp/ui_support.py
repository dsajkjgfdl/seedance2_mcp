from __future__ import annotations

import base64
from typing import Any

from .schemas import AudioInput, ImageInput, VideoInput, VideoSequenceSegment


def split_non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def build_image_inputs(url_text: str, uploaded_files: list[Any] | None = None) -> list[ImageInput]:
    image_inputs = [ImageInput(url=url) for url in split_non_empty_lines(url_text)]
    for uploaded_file in uploaded_files or []:
        payload = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
        image_inputs.append(ImageInput(base64=payload))
    return image_inputs


def build_video_inputs(url_text: str) -> list[VideoInput]:
    return [VideoInput(url=url) for url in split_non_empty_lines(url_text)]


def build_audio_inputs(url_text: str) -> list[AudioInput]:
    return [AudioInput(url=url) for url in split_non_empty_lines(url_text)]


def build_sequence_segments(prompts_text: str) -> list[VideoSequenceSegment]:
    return [VideoSequenceSegment(prompt=prompt) for prompt in split_non_empty_lines(prompts_text)]
