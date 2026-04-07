from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import Context

from ..client import ArkVideoGenerationClient, _to_plain_data, get_ark_client
from ..config import Settings, get_settings
from ..downloads import download_video_file
from ..errors import InputValidationError, TaskTimeoutError
from ..schemas import (
    AudioInput,
    DeleteVideoTaskResult,
    ImageInput,
    ListVideoTasksResult,
    TaskErrorInfo,
    TaskReference,
    UsageInfo,
    VideoInput,
    VideoSequenceResult,
    VideoSequenceSegment,
    VideoSequenceSegmentResult,
    VideoTaskResult,
    WaitVideoTaskResult,
)
from ..validators import (
    validate_create_request,
    validate_draft_request,
    validate_final_from_draft_request,
    validate_prompt,
    validate_sequence_request,
)


def _image_to_content(image: ImageInput) -> dict[str, Any]:
    if image.url:
        return {"type": "image_url", "image_url": {"url": image.url}}
    assert image.base64 is not None
    payload = image.base64.strip()
    if payload.startswith("data:image/"):
        url = payload
    else:
        url = f"data:image/png;base64,{payload}"
    return {"type": "image_url", "image_url": {"url": url}}


def _video_to_content(video: VideoInput) -> dict[str, Any]:
    return {"type": "video_url", "video_url": {"url": video.url}}


def _audio_to_content(audio: AudioInput) -> dict[str, Any]:
    return {"type": "audio_url", "audio_url": {"url": audio.url}}


def _normalize_task(raw: Any) -> VideoTaskResult:
    data = _to_plain_data(raw)
    content = data.get("content") or {}
    usage = data.get("usage") or {}
    error = data.get("error") or {}
    return VideoTaskResult(
        task_id=str(data.get("id") or data.get("task_id")),
        model=data.get("model"),
        status=data.get("status", "queued"),
        video_url=content.get("video_url"),
        last_frame_url=content.get("last_frame_url"),
        usage=UsageInfo(**usage) if usage else None,
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        seed=data.get("seed"),
        resolution=data.get("resolution"),
        ratio=data.get("ratio"),
        duration=data.get("duration"),
        fps=data.get("framespersecond") or data.get("fps"),
        service_tier=data.get("service_tier"),
        execution_expires_after=data.get("execution_expires_after"),
        error=TaskErrorInfo(**error) if error else None,
    )


def _extract_task_id(raw: Any) -> str:
    data = _to_plain_data(raw)
    task_id = data.get("id") or data.get("task_id")
    if not task_id:
        raise InputValidationError("Ark response did not include a task ID.")
    return str(task_id)


class SeedanceVideoService:
    def __init__(self, client: ArkVideoGenerationClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    def _build_create_payload(
        self,
        *,
        model: str,
        prompt: str,
        images: list[ImageInput],
        videos: list[VideoInput],
        audios: list[AudioInput],
        resolution: str | None,
        ratio: str | None,
        duration: int | None,
        frames: int | None,
        seed: int | None,
        camera_fixed: bool | None,
        watermark: bool,
        generate_audio: bool,
        return_last_frame: bool,
        service_tier: str,
        callback_url: str | None,
        draft: bool = False,
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": validate_prompt(prompt)}]
        content.extend(_image_to_content(item) for item in images)
        content.extend(_video_to_content(item) for item in videos)
        content.extend(_audio_to_content(item) for item in audios)

        payload: dict[str, Any] = {
            "model": model,
            "content": content,
            "watermark": watermark,
            "service_tier": service_tier,
        }
        if resolution is not None:
            payload["resolution"] = resolution
        if ratio is not None:
            payload["ratio"] = ratio
        if duration is not None:
            payload["duration"] = duration
        if frames is not None:
            payload["frames"] = frames
        if seed is not None:
            payload["seed"] = seed
        if camera_fixed is not None:
            payload["camera_fixed"] = camera_fixed
        if generate_audio:
            payload["generate_audio"] = generate_audio
        if return_last_frame:
            payload["return_last_frame"] = return_last_frame
        if callback_url:
            payload["callback_url"] = callback_url
        if draft:
            payload["draft"] = True
        return payload

    async def create_video_task(
        self,
        *,
        prompt: str,
        images: list[ImageInput],
        videos: list[VideoInput],
        audios: list[AudioInput],
        model: str,
        resolution: str | None,
        ratio: str | None,
        duration: int | None,
        frames: int | None,
        seed: int | None,
        camera_fixed: bool | None,
        watermark: bool,
        generate_audio: bool,
        return_last_frame: bool,
        service_tier: str,
        callback_url: str | None,
    ) -> TaskReference:
        validate_create_request(
            model=model,
            prompt=prompt,
            images=images,
            videos=videos,
            audios=audios,
            resolution=resolution,
            ratio=ratio,
            duration=duration,
            frames=frames,
            seed=seed,
            camera_fixed=camera_fixed,
            watermark=watermark,
            generate_audio=generate_audio,
            return_last_frame=return_last_frame,
            service_tier=service_tier,
        )
        payload = self._build_create_payload(
            model=model,
            prompt=prompt,
            images=images,
            videos=videos,
            audios=audios,
            resolution=resolution,
            ratio=ratio,
            duration=duration,
            frames=frames,
            seed=seed,
            camera_fixed=camera_fixed,
            watermark=watermark,
            generate_audio=generate_audio,
            return_last_frame=return_last_frame,
            service_tier=service_tier,
            callback_url=callback_url,
        )
        raw = await asyncio.to_thread(self.client.create_task, payload)
        return TaskReference(task_id=_extract_task_id(raw), model=model, service_tier=service_tier)

    async def create_draft_video_task(
        self,
        *,
        prompt: str,
        images: list[ImageInput],
        model: str,
        duration: int,
        seed: int | None,
    ) -> TaskReference:
        validate_draft_request(
            model=model,
            prompt=prompt,
            images=images,
            duration=duration,
            seed=seed,
        )
        payload = self._build_create_payload(
            model=model,
            prompt=prompt,
            images=images,
            videos=[],
            audios=[],
            resolution=None,
            ratio=None,
            duration=duration,
            frames=None,
            seed=seed,
            camera_fixed=None,
            watermark=False,
            generate_audio=False,
            return_last_frame=False,
            service_tier="default",
            callback_url=None,
            draft=True,
        )
        raw = await asyncio.to_thread(self.client.create_task, payload)
        return TaskReference(task_id=_extract_task_id(raw), model=model, service_tier="default")

    async def create_final_video_from_draft(
        self,
        *,
        draft_task_id: str,
        model: str,
        resolution: str | None,
        watermark: bool,
        return_last_frame: bool,
        service_tier: str,
    ) -> TaskReference:
        validate_final_from_draft_request(
            model=model,
            draft_task_id=draft_task_id,
            resolution=resolution,
            watermark=watermark,
            return_last_frame=return_last_frame,
            service_tier=service_tier,
        )
        payload: dict[str, Any] = {
            "model": model,
            "content": [{"type": "draft_task", "draft_task": {"id": draft_task_id}}],
            "watermark": watermark,
            "service_tier": service_tier,
        }
        if resolution is not None:
            payload["resolution"] = resolution
        if return_last_frame:
            payload["return_last_frame"] = True
        raw = await asyncio.to_thread(self.client.create_task, payload)
        return TaskReference(task_id=_extract_task_id(raw), model=model, service_tier=service_tier)

    async def get_video_task(self, *, task_id: str) -> VideoTaskResult:
        raw = await asyncio.to_thread(self.client.get_task, task_id)
        return _normalize_task(raw)

    async def wait_video_task(
        self,
        *,
        task_id: str,
        poll_interval_seconds: int | None,
        timeout_seconds: int | None,
        download: bool,
        output_dir: str | None,
        ctx: Context | None = None,
    ) -> WaitVideoTaskResult:
        interval = poll_interval_seconds or self.settings.poll_interval_seconds
        started = asyncio.get_running_loop().time()
        first_result = await self.get_video_task(task_id=task_id)
        effective_timeout = timeout_seconds or self.settings.timeout_for(first_result.service_tier)
        current_result = first_result

        while current_result.status not in {"succeeded", "failed", "expired"}:
            elapsed = asyncio.get_running_loop().time() - started
            if elapsed > effective_timeout:
                raise TaskTimeoutError(
                    f"Timed out waiting for task {task_id} after {effective_timeout} seconds."
                )
            if ctx is not None:
                await ctx.info(f"Task {task_id} status: {current_result.status}")
                await ctx.report_progress(
                    progress=min(int(elapsed), effective_timeout),
                    total=effective_timeout,
                )
            await asyncio.sleep(interval)
            current_result = await self.get_video_task(task_id=task_id)

        saved_path: str | None = None
        if current_result.status == "succeeded" and download:
            if not current_result.video_url:
                raise InputValidationError(f"Task {task_id} succeeded but video_url is missing.")
            if ctx is not None:
                await ctx.info(f"Downloading video for task {task_id}")
            saved_path = await download_video_file(
                current_result.video_url,
                task_id=task_id,
                output_dir=output_dir,
            )
        return WaitVideoTaskResult(**current_result.model_dump(), saved_path=saved_path)

    async def list_video_tasks(
        self,
        *,
        status: str | None,
        page_size: int,
        page_token: str | None,
    ) -> ListVideoTasksResult:
        if page_size <= 0:
            raise InputValidationError("page_size must be greater than 0.")
        raw = await asyncio.to_thread(
            self.client.list_tasks,
            page_size=page_size,
            status=status,
            page_token=page_token,
        )
        data = _to_plain_data(raw)
        items = data.get("data") or data.get("tasks") or data.get("items") or []
        return ListVideoTasksResult(
            tasks=[_normalize_task(item) for item in items],
            next_page_token=data.get("next_page_token") or data.get("page_token"),
            has_more=data.get("has_more"),
            raw_page=data,
        )

    async def delete_video_task(self, *, task_id: str) -> DeleteVideoTaskResult:
        await asyncio.to_thread(self.client.delete_task, task_id)
        return DeleteVideoTaskResult(task_id=task_id)

    async def generate_video_sequence(
        self,
        *,
        segments: list[VideoSequenceSegment],
        initial_images: list[ImageInput],
        model: str,
        resolution: str | None,
        ratio: str | None,
        duration: int,
        watermark: bool,
        ctx: Context | None = None,
    ) -> VideoSequenceResult:
        validate_sequence_request(
            model=model,
            segments_count=len(segments),
            initial_images=initial_images,
            resolution=resolution,
            ratio=ratio,
            duration=duration,
            watermark=watermark,
        )

        chained_images = list(initial_images)
        results: list[VideoSequenceSegmentResult] = []

        for index, segment in enumerate(segments, start=1):
            if ctx is not None:
                await ctx.info(f"Generating sequence segment {index}/{len(segments)}")
                await ctx.report_progress(progress=index - 1, total=len(segments))

            create_result = await self.create_video_task(
                prompt=segment.prompt,
                images=[*chained_images, *segment.images],
                videos=segment.videos,
                audios=segment.audios,
                model=model,
                resolution=resolution,
                ratio=ratio,
                duration=duration,
                frames=None,
                seed=None,
                camera_fixed=None,
                watermark=watermark,
                generate_audio=False,
                return_last_frame=True,
                service_tier="default",
                callback_url=None,
            )
            final_result = await self.wait_video_task(
                task_id=create_result.task_id,
                poll_interval_seconds=self.settings.poll_interval_seconds,
                timeout_seconds=None,
                download=False,
                output_dir=None,
                ctx=ctx,
            )
            results.append(
                VideoSequenceSegmentResult(
                    index=index,
                    prompt=segment.prompt,
                    task=final_result,
                )
            )
            if index < len(segments):
                if not final_result.last_frame_url:
                    raise InputValidationError(
                        "Sequence chaining requires last_frame_url, "
                        "but the completed segment did not return one."
                    )
                chained_images = [ImageInput(url=final_result.last_frame_url)]

        if ctx is not None:
            await ctx.report_progress(progress=len(segments), total=len(segments))

        return VideoSequenceResult(
            model=model,
            segment_count=len(results),
            results=results,
        )


def get_service() -> SeedanceVideoService:
    return SeedanceVideoService(client=get_ark_client(), settings=get_settings())


def register_video_tools(mcp: Any) -> None:
    @mcp.tool
    async def create_video_task(
        prompt: str,
        images: list[ImageInput] | None = None,
        videos: list[VideoInput] | None = None,
        audios: list[AudioInput] | None = None,
        model: str = get_settings().default_model,
        resolution: str | None = None,
        ratio: str | None = None,
        duration: int | None = None,
        frames: int | None = None,
        seed: int | None = None,
        camera_fixed: bool | None = None,
        watermark: bool = False,
        generate_audio: bool = False,
        return_last_frame: bool = False,
        service_tier: str = "default",
        callback_url: str | None = None,
    ) -> TaskReference:
        """Create a Seedance video generation task."""
        service = get_service()
        return await service.create_video_task(
            prompt=prompt,
            images=images or [],
            videos=videos or [],
            audios=audios or [],
            model=model,
            resolution=resolution,
            ratio=ratio,
            duration=duration,
            frames=frames,
            seed=seed,
            camera_fixed=camera_fixed,
            watermark=watermark,
            generate_audio=generate_audio,
            return_last_frame=return_last_frame,
            service_tier=service_tier,
            callback_url=callback_url,
        )

    @mcp.tool
    async def create_draft_video_task(
        prompt: str,
        duration: int,
        images: list[ImageInput] | None = None,
        model: str = get_settings().default_draft_model,
        seed: int | None = None,
    ) -> TaskReference:
        """Create a Seedance draft video task for Seedance 1.5 Pro."""
        service = get_service()
        return await service.create_draft_video_task(
            prompt=prompt,
            images=images or [],
            model=model,
            duration=duration,
            seed=seed,
        )

    @mcp.tool
    async def create_final_video_from_draft(
        draft_task_id: str,
        model: str = get_settings().default_draft_model,
        resolution: str | None = "720p",
        watermark: bool = False,
        return_last_frame: bool = False,
        service_tier: str = "default",
    ) -> TaskReference:
        """Create a final video task from a Seedance draft task."""
        service = get_service()
        return await service.create_final_video_from_draft(
            draft_task_id=draft_task_id,
            model=model,
            resolution=resolution,
            watermark=watermark,
            return_last_frame=return_last_frame,
            service_tier=service_tier,
        )

    @mcp.tool
    async def get_video_task(task_id: str) -> VideoTaskResult:
        """Get the current status and result of a Seedance video task."""
        return await get_service().get_video_task(task_id=task_id)

    @mcp.tool
    async def wait_video_task(
        task_id: str,
        poll_interval_seconds: int = get_settings().poll_interval_seconds,
        timeout_seconds: int | None = None,
        download: bool = False,
        output_dir: str | None = None,
        ctx: Context | None = None,
    ) -> WaitVideoTaskResult:
        """Poll a Seedance task until it reaches a terminal state."""
        return await get_service().wait_video_task(
            task_id=task_id,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
            download=download,
            output_dir=output_dir,
            ctx=ctx,
        )

    @mcp.tool
    async def list_video_tasks(
        status: str | None = None,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> ListVideoTasksResult:
        """List Seedance video generation tasks."""
        return await get_service().list_video_tasks(
            status=status,
            page_size=page_size,
            page_token=page_token,
        )

    @mcp.tool
    async def delete_video_task(task_id: str) -> DeleteVideoTaskResult:
        """Delete or cancel a Seedance video generation task."""
        return await get_service().delete_video_task(task_id=task_id)

    @mcp.tool
    async def generate_video_sequence(
        segments: list[VideoSequenceSegment],
        initial_images: list[ImageInput] | None = None,
        model: str = get_settings().default_model,
        resolution: str | None = None,
        ratio: str | None = "adaptive",
        duration: int = 5,
        watermark: bool = False,
        ctx: Context | None = None,
    ) -> VideoSequenceResult:
        """Generate connected clips using the previous segment's last frame."""
        return await get_service().generate_video_sequence(
            segments=segments,
            initial_images=initial_images or [],
            model=model,
            resolution=resolution,
            ratio=ratio,
            duration=duration,
            watermark=watermark,
            ctx=ctx,
        )
