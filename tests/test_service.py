from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

import pytest

from seedance_mcp.config import Settings
from seedance_mcp.schemas import ImageInput, VideoSequenceSegment
from seedance_mcp.tools.video import SeedanceVideoService


@dataclass
class FakeClient:
    create_responses: deque
    get_responses: deque
    list_response: dict | None = None
    deleted_task_ids: list[str] | None = None
    create_payloads: list[dict] | None = None

    def __post_init__(self) -> None:
        self.deleted_task_ids = self.deleted_task_ids or []
        self.create_payloads = self.create_payloads or []

    def create_task(self, payload: dict) -> dict:
        self.create_payloads.append(payload)
        return self.create_responses.popleft()

    def get_task(self, task_id: str) -> dict:
        return self.get_responses.popleft()

    def list_tasks(
        self,
        *,
        page_size: int,
        status: str | None = None,
        page_token: str | None = None,
    ) -> dict:
        assert page_size > 0
        return self.list_response or {"data": []}

    def delete_task(self, task_id: str) -> None:
        self.deleted_task_ids.append(task_id)


def build_settings(tmp_path: Path) -> Settings:
    return Settings(
        ark_api_key="test-key",
        ark_base_url="https://ark.cn-beijing.volces.com/api/v3",
        default_model="doubao-seedance-2-0-260128",
        default_draft_model="doubao-seedance-1-5-pro-251215",
        output_dir=tmp_path / "outputs",
        poll_interval_seconds=0,
        timeout_seconds=10,
        flex_timeout_seconds=20,
    )


@pytest.mark.asyncio
async def test_create_video_task_maps_inputs_to_ark_payload(tmp_path: Path) -> None:
    client = FakeClient(create_responses=deque([{"id": "cgt-1"}]), get_responses=deque())
    service = SeedanceVideoService(client=client, settings=build_settings(tmp_path))

    result = await service.create_video_task(
        prompt="hello world",
        images=[ImageInput(url="https://example.com/image.png")],
        videos=[],
        audios=[],
        model="doubao-seedance-2-0-260128",
        resolution="720p",
        ratio="adaptive",
        duration=5,
        frames=None,
        seed=7,
        camera_fixed=None,
        watermark=False,
        generate_audio=True,
        return_last_frame=True,
        service_tier="default",
        callback_url="https://callback.example.com",
    )

    assert result.task_id == "cgt-1"
    assert client.create_payloads[0]["content"][0] == {"type": "text", "text": "hello world"}
    assert client.create_payloads[0]["content"][1]["type"] == "image_url"
    assert client.create_payloads[0]["generate_audio"] is True
    assert client.create_payloads[0]["return_last_frame"] is True
    assert client.create_payloads[0]["callback_url"] == "https://callback.example.com"


@pytest.mark.asyncio
async def test_wait_video_task_returns_terminal_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeClient(
        create_responses=deque(),
        get_responses=deque(
            [
                {"id": "cgt-1", "status": "queued", "service_tier": "default"},
                {
                    "id": "cgt-1",
                    "status": "succeeded",
                    "content": {"video_url": "https://example.com/video.mp4"},
                    "service_tier": "default",
                },
            ]
        ),
    )
    service = SeedanceVideoService(client=client, settings=build_settings(tmp_path))

    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("seedance_mcp.tools.video.asyncio.sleep", fake_sleep)

    result = await service.wait_video_task(
        task_id="cgt-1",
        poll_interval_seconds=0,
        timeout_seconds=5,
        download=False,
        output_dir=None,
    )

    assert result.status == "succeeded"
    assert result.video_url == "https://example.com/video.mp4"


@pytest.mark.asyncio
async def test_list_video_tasks_normalizes_response(tmp_path: Path) -> None:
    client = FakeClient(
        create_responses=deque(),
        get_responses=deque(),
        list_response={
            "data": [
                {
                    "id": "cgt-1",
                    "model": "doubao-seedance-2-0-260128",
                    "status": "succeeded",
                    "content": {"video_url": "https://example.com/video.mp4"},
                }
            ],
            "next_page_token": "next-token",
            "has_more": True,
        },
    )
    service = SeedanceVideoService(client=client, settings=build_settings(tmp_path))

    result = await service.list_video_tasks(status="succeeded", page_size=10, page_token=None)

    assert len(result.tasks) == 1
    assert result.tasks[0].task_id == "cgt-1"
    assert result.next_page_token == "next-token"
    assert result.has_more is True


@pytest.mark.asyncio
async def test_create_final_video_from_draft_builds_draft_payload(tmp_path: Path) -> None:
    client = FakeClient(create_responses=deque([{"id": "cgt-final"}]), get_responses=deque())
    service = SeedanceVideoService(client=client, settings=build_settings(tmp_path))

    result = await service.create_final_video_from_draft(
        draft_task_id="cgt-draft",
        model="doubao-seedance-1-5-pro-251215",
        resolution="720p",
        watermark=False,
        return_last_frame=True,
        service_tier="default",
    )

    assert result.task_id == "cgt-final"
    assert client.create_payloads[0]["content"][0]["type"] == "draft_task"
    assert client.create_payloads[0]["content"][0]["draft_task"]["id"] == "cgt-draft"


@pytest.mark.asyncio
async def test_generate_video_sequence_chains_last_frame(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeClient(
        create_responses=deque([{"id": "seg-1"}, {"id": "seg-2"}]),
        get_responses=deque(
            [
                {
                    "id": "seg-1",
                    "status": "succeeded",
                    "content": {
                        "video_url": "https://example.com/1.mp4",
                        "last_frame_url": "https://example.com/1-last.png",
                    },
                    "service_tier": "default",
                },
                {
                    "id": "seg-2",
                    "status": "succeeded",
                    "content": {
                        "video_url": "https://example.com/2.mp4",
                        "last_frame_url": "https://example.com/2-last.png",
                    },
                    "service_tier": "default",
                },
            ]
        ),
    )
    service = SeedanceVideoService(client=client, settings=build_settings(tmp_path))

    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("seedance_mcp.tools.video.asyncio.sleep", fake_sleep)

    result = await service.generate_video_sequence(
        segments=[
            VideoSequenceSegment(prompt="segment one"),
            VideoSequenceSegment(prompt="segment two"),
        ],
        initial_images=[ImageInput(url="https://example.com/initial.png")],
        model="doubao-seedance-2-0-260128",
        resolution="720p",
        ratio="adaptive",
        duration=5,
        watermark=False,
    )

    assert result.segment_count == 2
    assert client.create_payloads[0]["content"][1]["image_url"]["url"] == "https://example.com/initial.png"
    assert client.create_payloads[1]["content"][1]["image_url"]["url"] == "https://example.com/1-last.png"


@pytest.mark.asyncio
async def test_delete_video_task_returns_deleted_result(tmp_path: Path) -> None:
    client = FakeClient(create_responses=deque(), get_responses=deque())
    service = SeedanceVideoService(client=client, settings=build_settings(tmp_path))

    result = await service.delete_video_task(task_id="cgt-1")

    assert result.deleted is True
    assert client.deleted_task_ids == ["cgt-1"]
