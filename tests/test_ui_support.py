from __future__ import annotations

from seedance_mcp.ui_support import (
    build_audio_inputs,
    build_image_inputs,
    build_sequence_segments,
    build_video_inputs,
    split_non_empty_lines,
)


class FakeUpload:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def getvalue(self) -> bytes:
        return self._payload


def test_split_non_empty_lines() -> None:
    assert split_non_empty_lines("a\n\n b \n") == ["a", "b"]


def test_build_image_inputs_supports_urls_and_uploads() -> None:
    result = build_image_inputs(
        "https://example.com/image.png",
        [FakeUpload(b"abc")],
    )
    assert result[0].url == "https://example.com/image.png"
    assert result[1].base64 == "YWJj"


def test_build_video_and_audio_inputs() -> None:
    videos = build_video_inputs("https://example.com/1.mp4\nhttps://example.com/2.mp4")
    audios = build_audio_inputs("https://example.com/1.mp3")
    assert [item.url for item in videos] == [
        "https://example.com/1.mp4",
        "https://example.com/2.mp4",
    ]
    assert [item.url for item in audios] == ["https://example.com/1.mp3"]


def test_build_sequence_segments() -> None:
    segments = build_sequence_segments("片段一\n片段二")
    assert [item.prompt for item in segments] == ["片段一", "片段二"]
