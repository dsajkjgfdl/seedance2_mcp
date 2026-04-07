import pytest

from seedance_mcp.errors import InputValidationError
from seedance_mcp.schemas import ImageInput
from seedance_mcp.validators import (
    FRAME_MAX,
    FRAME_MIN,
    get_capabilities,
    validate_create_request,
    validate_draft_request,
)


def test_get_capabilities_for_default_model() -> None:
    capabilities = get_capabilities("doubao-seedance-2-0-260128")
    assert capabilities.duration_range == (4, 15)
    assert capabilities.supported_service_tiers == frozenset({"default"})


def test_2_0_model_rejects_flex() -> None:
    with pytest.raises(InputValidationError):
        validate_create_request(
            model="doubao-seedance-2-0-260128",
            prompt="hello",
            images=[],
            videos=[],
            audios=[],
            resolution="720p",
            ratio="16:9",
            duration=5,
            frames=None,
            seed=None,
            camera_fixed=None,
            watermark=False,
            generate_audio=False,
            return_last_frame=False,
            service_tier="flex",
        )


def test_1_0_pro_accepts_valid_frames() -> None:
    validate_create_request(
        model="doubao-seedance-1-0-pro-250528",
        prompt="hello",
        images=[],
        videos=[],
        audios=[],
        resolution="720p",
        ratio="16:9",
        duration=None,
        frames=FRAME_MIN,
        seed=None,
        camera_fixed=True,
        watermark=False,
        generate_audio=False,
        return_last_frame=True,
        service_tier="default",
    )


def test_1_0_pro_rejects_invalid_frames() -> None:
    with pytest.raises(InputValidationError):
        validate_create_request(
            model="doubao-seedance-1-0-pro-250528",
            prompt="hello",
            images=[],
            videos=[],
            audios=[],
            resolution="720p",
            ratio="16:9",
            duration=None,
            frames=FRAME_MAX - 1,
            seed=None,
            camera_fixed=True,
            watermark=False,
            generate_audio=False,
            return_last_frame=True,
            service_tier="default",
        )


def test_draft_request_requires_supported_model() -> None:
    with pytest.raises(InputValidationError):
        validate_draft_request(
            model="doubao-seedance-2-0-260128",
            prompt="hello",
            images=[],
            duration=6,
            seed=None,
        )


def test_draft_request_accepts_1_5_model() -> None:
    validate_draft_request(
        model="doubao-seedance-1-5-pro-251215",
        prompt="hello",
        images=[ImageInput(url="https://example.com/1.png")],
        duration=6,
        seed=10,
    )
