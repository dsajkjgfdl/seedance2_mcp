from __future__ import annotations

import base64
from collections.abc import Iterable
from dataclasses import dataclass

from .errors import InputValidationError
from .schemas import AudioInput, ImageInput, VideoInput

FRAME_MIN = 29
FRAME_MAX = 289


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    model_id: str
    resolutions: frozenset[str]
    ratios: frozenset[str]
    duration_range: tuple[int, int]
    supports_frames: bool
    supports_seed: bool
    supports_camera_fixed: bool
    supports_watermark: bool
    supports_generate_audio: bool
    supports_return_last_frame: bool
    supports_draft: bool
    supported_service_tiers: frozenset[str]
    max_images: int
    max_videos: int
    max_audios: int
    supports_text_to_video: bool
    requires_image: bool = False
    adaptive_requires_image: bool = False


MODEL_CAPABILITIES: dict[str, ModelCapabilities] = {
    "doubao-seedance-2-0-260128": ModelCapabilities(
        model_id="doubao-seedance-2-0-260128",
        resolutions=frozenset({"480p", "720p"}),
        ratios=frozenset({"16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"}),
        duration_range=(4, 15),
        supports_frames=False,
        supports_seed=True,
        supports_camera_fixed=False,
        supports_watermark=True,
        supports_generate_audio=True,
        supports_return_last_frame=True,
        supports_draft=False,
        supported_service_tiers=frozenset({"default"}),
        max_images=9,
        max_videos=3,
        max_audios=3,
        supports_text_to_video=True,
    ),
    "doubao-seedance-2-0-fast-260128": ModelCapabilities(
        model_id="doubao-seedance-2-0-fast-260128",
        resolutions=frozenset({"480p", "720p"}),
        ratios=frozenset({"16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"}),
        duration_range=(4, 15),
        supports_frames=False,
        supports_seed=True,
        supports_camera_fixed=False,
        supports_watermark=True,
        supports_generate_audio=True,
        supports_return_last_frame=True,
        supports_draft=False,
        supported_service_tiers=frozenset({"default"}),
        max_images=9,
        max_videos=3,
        max_audios=3,
        supports_text_to_video=True,
    ),
    "doubao-seedance-1-5-pro-251215": ModelCapabilities(
        model_id="doubao-seedance-1-5-pro-251215",
        resolutions=frozenset({"480p", "720p", "1080p"}),
        ratios=frozenset({"16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"}),
        duration_range=(4, 12),
        supports_frames=False,
        supports_seed=True,
        supports_camera_fixed=True,
        supports_watermark=True,
        supports_generate_audio=True,
        supports_return_last_frame=True,
        supports_draft=True,
        supported_service_tiers=frozenset({"default", "flex"}),
        max_images=2,
        max_videos=0,
        max_audios=0,
        supports_text_to_video=True,
    ),
    "doubao-seedance-1-0-pro-250528": ModelCapabilities(
        model_id="doubao-seedance-1-0-pro-250528",
        resolutions=frozenset({"480p", "720p", "1080p"}),
        ratios=frozenset({"16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"}),
        duration_range=(2, 12),
        supports_frames=True,
        supports_seed=True,
        supports_camera_fixed=True,
        supports_watermark=True,
        supports_generate_audio=False,
        supports_return_last_frame=True,
        supports_draft=False,
        supported_service_tiers=frozenset({"default", "flex"}),
        max_images=2,
        max_videos=0,
        max_audios=0,
        supports_text_to_video=True,
        adaptive_requires_image=True,
    ),
    "doubao-seedance-1-0-pro-fast-251015": ModelCapabilities(
        model_id="doubao-seedance-1-0-pro-fast-251015",
        resolutions=frozenset({"480p", "720p", "1080p"}),
        ratios=frozenset({"16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"}),
        duration_range=(2, 12),
        supports_frames=True,
        supports_seed=True,
        supports_camera_fixed=True,
        supports_watermark=True,
        supports_generate_audio=False,
        supports_return_last_frame=True,
        supports_draft=False,
        supported_service_tiers=frozenset({"default", "flex"}),
        max_images=2,
        max_videos=0,
        max_audios=0,
        supports_text_to_video=True,
        adaptive_requires_image=True,
    ),
    "doubao-seedance-1-0-lite-i2v-250428": ModelCapabilities(
        model_id="doubao-seedance-1-0-lite-i2v-250428",
        resolutions=frozenset({"480p", "720p"}),
        ratios=frozenset({"16:9", "4:3", "1:1", "3:4", "9:16", "21:9"}),
        duration_range=(2, 12),
        supports_frames=True,
        supports_seed=True,
        supports_camera_fixed=False,
        supports_watermark=True,
        supports_generate_audio=False,
        supports_return_last_frame=True,
        supports_draft=False,
        supported_service_tiers=frozenset({"default", "flex"}),
        max_images=4,
        max_videos=0,
        max_audios=0,
        supports_text_to_video=False,
        requires_image=True,
    ),
    "doubao-seedance-1-0-lite-t2v-250428": ModelCapabilities(
        model_id="doubao-seedance-1-0-lite-t2v-250428",
        resolutions=frozenset({"480p", "720p", "1080p"}),
        ratios=frozenset({"16:9", "4:3", "1:1", "3:4", "9:16", "21:9"}),
        duration_range=(2, 12),
        supports_frames=True,
        supports_seed=True,
        supports_camera_fixed=True,
        supports_watermark=True,
        supports_generate_audio=False,
        supports_return_last_frame=True,
        supports_draft=False,
        supported_service_tiers=frozenset({"default", "flex"}),
        max_images=0,
        max_videos=0,
        max_audios=0,
        supports_text_to_video=True,
    ),
}


def get_capabilities(model: str) -> ModelCapabilities:
    try:
        return MODEL_CAPABILITIES[model]
    except KeyError as exc:
        raise InputValidationError(f"Unsupported model: {model}") from exc


def validate_prompt(prompt: str) -> str:
    normalized = prompt.strip()
    if not normalized:
        raise InputValidationError("Prompt must not be empty.")
    return normalized


def validate_image_input(image: ImageInput) -> None:
    if image.base64:
        payload = image.base64.strip()
        if payload.startswith("data:image/"):
            return
        try:
            base64.b64decode(payload, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise InputValidationError("Image base64 payload is not valid Base64.") from exc


def validate_media_counts(
    capabilities: ModelCapabilities,
    images: Iterable[ImageInput],
    videos: Iterable[VideoInput],
    audios: Iterable[AudioInput],
) -> None:
    image_list = list(images)
    video_list = list(videos)
    audio_list = list(audios)

    if len(image_list) > capabilities.max_images:
        raise InputValidationError(
            f"Model {capabilities.model_id} supports at most {capabilities.max_images} images."
        )
    if len(video_list) > capabilities.max_videos:
        raise InputValidationError(
            f"Model {capabilities.model_id} does not support "
            f"{len(video_list)} video reference inputs."
        )
    if len(audio_list) > capabilities.max_audios:
        raise InputValidationError(
            f"Model {capabilities.model_id} does not support "
            f"{len(audio_list)} audio reference inputs."
        )
    if capabilities.requires_image and not image_list:
        raise InputValidationError(
            f"Model {capabilities.model_id} requires at least one image input."
        )
    if not capabilities.supports_text_to_video and not image_list:
        raise InputValidationError(
            f"Model {capabilities.model_id} does not support text-only generation."
        )

    for image in image_list:
        validate_image_input(image)


def validate_output_controls(
    capabilities: ModelCapabilities,
    *,
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
    has_images: bool,
) -> None:
    if resolution is not None and resolution not in capabilities.resolutions:
        raise InputValidationError(
            f"Model {capabilities.model_id} does not support resolution '{resolution}'."
        )
    if ratio is not None and ratio not in capabilities.ratios:
        raise InputValidationError(
            f"Model {capabilities.model_id} does not support ratio '{ratio}'."
        )
    if ratio == "adaptive" and capabilities.adaptive_requires_image and not has_images:
        raise InputValidationError(
            f"Model {capabilities.model_id} supports adaptive ratio only "
            "when image input is present."
        )
    if duration is None and frames is None:
        raise InputValidationError("Provide either duration or frames.")
    if duration is not None and frames is not None:
        raise InputValidationError("Provide duration or frames, not both.")
    if duration is not None:
        min_duration, max_duration = capabilities.duration_range
        if not min_duration <= duration <= max_duration:
            raise InputValidationError(
                f"Duration for {capabilities.model_id} must be between "
                f"{min_duration} and {max_duration} seconds."
            )
    if frames is not None:
        if not capabilities.supports_frames:
            raise InputValidationError(f"Model {capabilities.model_id} does not support frames.")
        if frames < FRAME_MIN or frames > FRAME_MAX or (frames - 25) % 4 != 0:
            raise InputValidationError(
                "Frames must be between 29 and 289 and match the 25 + 4n rule."
            )
    if seed is not None and not capabilities.supports_seed:
        raise InputValidationError(f"Model {capabilities.model_id} does not support seed.")
    if camera_fixed is not None and not capabilities.supports_camera_fixed:
        raise InputValidationError(f"Model {capabilities.model_id} does not support camera_fixed.")
    if watermark and not capabilities.supports_watermark:
        raise InputValidationError(
            f"Model {capabilities.model_id} does not support watermark control."
        )
    if generate_audio and not capabilities.supports_generate_audio:
        raise InputValidationError(
            f"Model {capabilities.model_id} does not support generate_audio."
        )
    if return_last_frame and not capabilities.supports_return_last_frame:
        raise InputValidationError(
            f"Model {capabilities.model_id} does not support return_last_frame."
        )
    if service_tier not in capabilities.supported_service_tiers:
        raise InputValidationError(
            f"Model {capabilities.model_id} does not support service_tier '{service_tier}'."
        )


def validate_create_request(
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
) -> ModelCapabilities:
    validate_prompt(prompt)
    capabilities = get_capabilities(model)
    validate_media_counts(capabilities, images, videos, audios)
    validate_output_controls(
        capabilities,
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
        has_images=bool(images),
    )
    return capabilities


def validate_draft_request(
    *,
    model: str,
    prompt: str,
    images: list[ImageInput],
    duration: int,
    seed: int | None,
) -> ModelCapabilities:
    capabilities = get_capabilities(model)
    if not capabilities.supports_draft:
        raise InputValidationError(f"Model {model} does not support draft mode.")
    if len(images) > 2:
        raise InputValidationError("Draft mode supports at most two images.")
    validate_prompt(prompt)
    validate_media_counts(capabilities, images, [], [])
    validate_output_controls(
        capabilities,
        resolution="480p",
        ratio=None,
        duration=duration,
        frames=None,
        seed=seed,
        camera_fixed=None,
        watermark=False,
        generate_audio=False,
        return_last_frame=False,
        service_tier="default",
        has_images=bool(images),
    )
    return capabilities


def validate_final_from_draft_request(
    *,
    model: str,
    draft_task_id: str,
    resolution: str | None,
    watermark: bool,
    return_last_frame: bool,
    service_tier: str,
) -> ModelCapabilities:
    if not draft_task_id.strip():
        raise InputValidationError("draft_task_id must not be empty.")
    capabilities = get_capabilities(model)
    if not capabilities.supports_draft:
        raise InputValidationError(f"Model {model} does not support draft mode.")
    validate_output_controls(
        capabilities,
        resolution=resolution,
        ratio=None,
        duration=capabilities.duration_range[0],
        frames=None,
        seed=None,
        camera_fixed=None,
        watermark=watermark,
        generate_audio=False,
        return_last_frame=return_last_frame,
        service_tier=service_tier,
        has_images=False,
    )
    return capabilities


def validate_sequence_request(
    *,
    model: str,
    segments_count: int,
    initial_images: list[ImageInput],
    resolution: str | None,
    ratio: str | None,
    duration: int,
    watermark: bool,
) -> ModelCapabilities:
    capabilities = get_capabilities(model)
    if segments_count <= 0:
        raise InputValidationError("segments must contain at least one segment.")
    validate_media_counts(capabilities, initial_images, [], [])
    validate_output_controls(
        capabilities,
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
        has_images=bool(initial_images),
    )
    return capabilities
