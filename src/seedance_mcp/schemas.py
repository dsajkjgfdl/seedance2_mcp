from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ResolutionLiteral = Literal["480p", "720p", "1080p"]
RatioLiteral = Literal["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"]
ServiceTierLiteral = Literal["default", "flex"]
TaskStatusLiteral = Literal["queued", "running", "succeeded", "failed", "expired"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ImageInput(StrictModel):
    url: str | None = Field(default=None, description="Remote image URL.")
    base64: str | None = Field(
        default=None,
        description="Raw Base64 image content or a full data URL.",
    )

    @model_validator(mode="after")
    def validate_exactly_one_source(self) -> ImageInput:
        if bool(self.url) == bool(self.base64):
            raise ValueError("Provide exactly one of 'url' or 'base64'.")
        return self


class VideoInput(StrictModel):
    url: str = Field(description="Remote video URL.")


class AudioInput(StrictModel):
    url: str = Field(description="Remote audio URL.")


class VideoSequenceSegment(StrictModel):
    prompt: str = Field(description="Prompt for the segment.")
    images: list[ImageInput] = Field(default_factory=list)
    videos: list[VideoInput] = Field(default_factory=list)
    audios: list[AudioInput] = Field(default_factory=list)


class TaskReference(StrictModel):
    task_id: str
    model: str
    service_tier: str


class UsageInfo(StrictModel):
    completion_tokens: int | None = None
    total_tokens: int | None = None


class TaskErrorInfo(StrictModel):
    code: str | None = None
    message: str | None = None


class VideoTaskResult(StrictModel):
    task_id: str
    model: str | None = None
    status: TaskStatusLiteral | str
    video_url: str | None = None
    last_frame_url: str | None = None
    usage: UsageInfo | None = None
    created_at: int | None = None
    updated_at: int | None = None
    seed: int | None = None
    resolution: str | None = None
    ratio: str | None = None
    duration: int | None = None
    fps: int | None = None
    service_tier: str | None = None
    execution_expires_after: int | None = None
    error: TaskErrorInfo | None = None


class WaitVideoTaskResult(VideoTaskResult):
    saved_path: str | None = None


class ListVideoTasksResult(StrictModel):
    tasks: list[VideoTaskResult]
    next_page_token: str | None = None
    has_more: bool | None = None
    raw_page: dict[str, Any] | None = None


class DeleteVideoTaskResult(StrictModel):
    task_id: str
    deleted: bool = True
    message: str = "Task deleted or cancellation requested."


class VideoSequenceSegmentResult(StrictModel):
    index: int
    prompt: str
    task: WaitVideoTaskResult


class VideoSequenceResult(StrictModel):
    model: str
    segment_count: int
    results: list[VideoSequenceSegmentResult]
