from __future__ import annotations

import asyncio
import sys
import threading
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from seedance_mcp.config import get_settings  # noqa: E402
from seedance_mcp.errors import SeedanceMCPError  # noqa: E402
from seedance_mcp.schemas import TaskReference, VideoTaskResult, WaitVideoTaskResult  # noqa: E402
from seedance_mcp.tools.video import SeedanceVideoService, get_service  # noqa: E402
from seedance_mcp.ui_support import (  # noqa: E402
    build_audio_inputs,
    build_image_inputs,
    build_sequence_segments,
    build_video_inputs,
)
from seedance_mcp.validators import FRAME_MIN, MODEL_CAPABILITIES, ModelCapabilities  # noqa: E402

DEFAULT_OPTION = "使用默认值"
RATIO_ORDER = ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"]
RESOLUTION_ORDER = ["480p", "720p", "1080p"]


def run_async(awaitable: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    result: dict[str, Any] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(awaitable)
        except Exception as exc:  # noqa: BLE001
            result["error"] = exc

    thread = threading.Thread(target=runner, daemon=False)
    thread.start()
    thread.join()
    if "error" in result:
        raise result["error"]
    return result.get("value")


def ensure_state() -> None:
    if "task_history" not in st.session_state:
        st.session_state.task_history = []
    if "latest_task_id" not in st.session_state:
        st.session_state.latest_task_id = ""
    if "latest_draft_task_id" not in st.session_state:
        st.session_state.latest_draft_task_id = ""


def remember_task_id(task_id: str, *, is_draft: bool = False) -> None:
    history = st.session_state.task_history
    if task_id in history:
        history.remove(task_id)
    history.insert(0, task_id)
    st.session_state.task_history = history[:20]
    st.session_state.latest_task_id = task_id
    if is_draft:
        st.session_state.latest_draft_task_id = task_id


def get_service_or_raise() -> SeedanceVideoService:
    return get_service()


def parse_optional_int(value: str, label: str) -> int | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return int(normalized)
    except ValueError as exc:
        raise ValueError(f"{label} 必须是整数。") from exc


def parse_optional_bool(value: str) -> bool | None:
    if value == DEFAULT_OPTION:
        return None
    return value == "true"


def optional_choice(choice: str) -> str | None:
    if choice == DEFAULT_OPTION:
        return None
    return choice


def ordered_choices(values: set[str] | frozenset[str], ordered_defaults: list[str]) -> list[str]:
    return [value for value in ordered_defaults if value in values]


def render_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top right, #dceeff 0, transparent 28%),
                linear-gradient(180deg, #f7fafc 0%, #edf2f7 100%);
        }
        .hero-card {
            padding: 1.4rem 1.6rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #38bdf8 100%);
            color: white;
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18);
            margin-bottom: 1rem;
        }
        .hero-title {
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 0.4rem;
        }
        .hero-copy {
            font-size: 0.98rem;
            line-height: 1.6;
            opacity: 0.95;
        }
        .cap-card {
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: rgba(255, 255, 255, 0.82);
            border-radius: 16px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(settings: Any) -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Seedance 测试控制台</div>
            <div class="hero-copy">
                直接调用当前仓库里的 SeedanceVideoService，快速验证文生视频、图生视频、
                Draft 样片、任务轮询和连续视频链式生成。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, middle, right = st.columns(3)
    left.metric("默认模型", settings.default_model)
    middle.metric("默认 Draft 模型", settings.default_draft_model)
    right.metric("API Key", "已配置" if settings.ark_api_key else "未配置")


def render_capabilities(model: str) -> ModelCapabilities:
    caps = MODEL_CAPABILITIES[model]
    st.markdown('<div class="cap-card">', unsafe_allow_html=True)
    st.markdown(f"**当前模型**: `{caps.model_id}`")
    st.caption(
        f"分辨率: {', '.join(ordered_choices(caps.resolutions, RESOLUTION_ORDER))} | "
        f"比例: {', '.join(ordered_choices(caps.ratios, RATIO_ORDER))}"
    )
    st.caption(
        f"时长: {caps.duration_range[0]}-{caps.duration_range[1]} 秒 | "
        f"图片: 最多 {caps.max_images} 张 | 视频: 最多 {caps.max_videos} 段 | "
        f"音频: 最多 {caps.max_audios} 段"
    )
    st.caption(
        f"支持 generate_audio: {caps.supports_generate_audio} | "
        f"return_last_frame: {caps.supports_return_last_frame} | "
        f"draft: {caps.supports_draft} | "
        f"service_tier: {', '.join(sorted(caps.supported_service_tiers))}"
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return caps


def render_task_reference(task_ref: TaskReference) -> None:
    remember_task_id(task_ref.task_id)
    st.success(f"任务已创建: {task_ref.task_id}")
    st.json(task_ref.model_dump(mode="json"))


def render_task_result(
    result: VideoTaskResult | WaitVideoTaskResult,
    heading: str = "任务结果",
) -> None:
    remember_task_id(result.task_id)
    st.subheader(heading)
    top_left, top_mid, top_right = st.columns(3)
    top_left.metric("任务 ID", result.task_id)
    top_mid.metric("状态", result.status)
    top_right.metric("模型", result.model or "-")

    info_left, info_mid, info_right = st.columns(3)
    info_left.metric("分辨率", result.resolution or "-")
    info_mid.metric("比例", result.ratio or "-")
    info_right.metric("时长", str(result.duration) if result.duration is not None else "-")

    if result.error and result.error.message:
        st.error(f"{result.error.code or 'ArkError'}: {result.error.message}")

    if result.video_url:
        st.video(result.video_url)

    if result.last_frame_url:
        st.image(result.last_frame_url, caption="返回的尾帧")

    if isinstance(result, WaitVideoTaskResult) and result.saved_path:
        saved_path = Path(result.saved_path)
        st.success(f"视频已下载到本地: {saved_path}")
        if saved_path.exists():
            with saved_path.open("rb") as file_handle:
                st.download_button(
                    "下载本地视频文件",
                    data=file_handle.read(),
                    file_name=saved_path.name,
                    mime="video/mp4",
                )

    with st.expander("查看完整 JSON", expanded=False):
        st.json(result.model_dump(mode="json"))


def execute_action(label: str, callback: Any) -> Any | None:
    try:
        with st.spinner(label):
            return callback()
    except (SeedanceMCPError, ValueError) as exc:
        st.error(str(exc))
    except Exception as exc:  # noqa: BLE001
        st.exception(exc)
    return None


def render_sidebar(settings: Any) -> None:
    with st.sidebar:
        st.header("运行状态")
        st.write(f"Ark Base URL: `{settings.ark_base_url}`")
        st.write(f"默认输出目录: `{settings.output_dir}`")
        st.write(f"默认轮询间隔: `{settings.poll_interval_seconds}` 秒")
        if not settings.ark_api_key:
            st.warning("尚未检测到 ARK_API_KEY，页面可以打开，但提交任务会失败。")

        st.header("最近任务")
        if st.session_state.task_history:
            for task_id in st.session_state.task_history[:10]:
                st.code(task_id)
        else:
            st.caption("暂无历史任务。")


def render_create_tab(settings: Any) -> None:
    st.subheader("基础视频生成")
    default_model_index = list(MODEL_CAPABILITIES).index(settings.default_model)
    model = st.selectbox("选择模型", list(MODEL_CAPABILITIES), index=default_model_index)
    caps = render_capabilities(model)

    with st.form("create_video_form"):
        prompt = st.text_area(
            "Prompt",
            height=140,
            placeholder="写实风格，晴朗的蓝天之下，一大片白色的雏菊花田，镜头逐渐拉近……",
        )

        image_urls = st.text_area("图片 URL", placeholder="每行一个 URL，可留空")
        uploaded_images = st.file_uploader(
            "或上传图片转 Base64",
            type=["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"],
            accept_multiple_files=True,
        )

        media_left, media_right = st.columns(2)
        video_urls = media_left.text_area("视频参考 URL", placeholder="每行一个 URL，可留空")
        audio_urls = media_right.text_area("音频参考 URL", placeholder="每行一个 URL，可留空")

        control_left, control_mid, control_right = st.columns(3)
        resolution = control_left.selectbox(
            "分辨率",
            [DEFAULT_OPTION, *ordered_choices(caps.resolutions, RESOLUTION_ORDER)],
        )
        ratio = control_mid.selectbox(
            "宽高比",
            [DEFAULT_OPTION, *ordered_choices(caps.ratios, RATIO_ORDER)],
        )
        service_tier = control_right.selectbox(
            "推理层级",
            sorted(caps.supported_service_tiers),
        )

        seed_text = st.text_input("Seed", placeholder="留空表示不指定")
        camera_fixed = st.selectbox(
            "固定镜头",
            [DEFAULT_OPTION, "true", "false"],
            disabled=not caps.supports_camera_fixed,
        )

        if caps.supports_frames:
            output_mode = st.radio("输出控制", ["duration", "frames"], horizontal=True)
        else:
            output_mode = "duration"

        min_duration, max_duration = caps.duration_range
        duration_value = st.number_input(
            "时长（秒）",
            min_value=min_duration,
            max_value=max_duration,
            value=min(5, max_duration),
            disabled=output_mode != "duration",
        )
        frames_value = st.number_input(
            "帧数",
            min_value=FRAME_MIN,
            max_value=289,
            value=FRAME_MIN,
            disabled=output_mode != "frames",
        )

        flag_left, flag_mid, flag_right = st.columns(3)
        watermark = flag_left.checkbox("包含水印", value=False)
        generate_audio = flag_mid.checkbox(
            "生成音频",
            value=False,
            disabled=not caps.supports_generate_audio,
        )
        return_last_frame = flag_right.checkbox(
            "返回尾帧",
            value=False,
            disabled=not caps.supports_return_last_frame,
        )

        callback_url = st.text_input("callback_url", placeholder="可留空")
        wait_left, wait_mid, wait_right = st.columns(3)
        auto_wait = wait_left.checkbox("创建后自动轮询", value=True)
        download = wait_mid.checkbox("完成后下载到本地", value=False)
        poll_interval = wait_right.number_input(
            "轮询间隔（秒）",
            min_value=1,
            max_value=60,
            value=settings.poll_interval_seconds,
        )
        timeout_seconds = st.number_input(
            "超时（秒，填 0 使用默认值）",
            min_value=0,
            max_value=86400,
            value=0,
        )
        output_dir = st.text_input("下载目录", placeholder=str(settings.output_dir))

        submitted = st.form_submit_button("创建视频任务", use_container_width=True)

    if not submitted:
        return

    def action() -> None:
        service = get_service_or_raise()
        images = build_image_inputs(image_urls, list(uploaded_images or []))
        videos = build_video_inputs(video_urls)
        audios = build_audio_inputs(audio_urls)
        seed = parse_optional_int(seed_text, "Seed")
        duration = duration_value if output_mode == "duration" else None
        frames = frames_value if output_mode == "frames" else None

        task_ref = run_async(
            service.create_video_task(
                prompt=prompt,
                images=images,
                videos=videos,
                audios=audios,
                model=model,
                resolution=optional_choice(resolution),
                ratio=optional_choice(ratio),
                duration=duration,
                frames=frames,
                seed=seed,
                camera_fixed=parse_optional_bool(camera_fixed),
                watermark=watermark,
                generate_audio=generate_audio,
                return_last_frame=return_last_frame,
                service_tier=service_tier,
                callback_url=callback_url.strip() or None,
            )
        )
        render_task_reference(task_ref)

        if auto_wait:
            result = run_async(
                service.wait_video_task(
                    task_id=task_ref.task_id,
                    poll_interval_seconds=int(poll_interval),
                    timeout_seconds=None if timeout_seconds == 0 else int(timeout_seconds),
                    download=download,
                    output_dir=output_dir.strip() or None,
                )
            )
            render_task_result(result, heading="生成结果")

    execute_action("正在创建视频任务...", action)


def render_draft_tab(settings: Any) -> None:
    st.subheader("Draft 样片流程")
    draft_models = [model for model, caps in MODEL_CAPABILITIES.items() if caps.supports_draft]
    default_index = draft_models.index(settings.default_draft_model)
    draft_model = st.selectbox("Draft 模型", draft_models, index=default_index)
    caps = render_capabilities(draft_model)

    st.markdown("### 1. 创建 Draft 视频")
    with st.form("draft_create_form"):
        prompt = st.text_area(
            "Draft Prompt",
            height=120,
            placeholder="女孩抱着狐狸，女孩睁开眼，温柔地看向镜头……",
        )
        image_urls = st.text_area("图片 URL", placeholder="最多 2 张，每行一个 URL")
        uploaded_images = st.file_uploader(
            "或上传 Draft 图片",
            type=["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"],
            accept_multiple_files=True,
            key="draft_uploaded_images",
        )
        duration = st.number_input(
            "Draft 时长（秒）",
            min_value=caps.duration_range[0],
            max_value=caps.duration_range[1],
            value=6,
        )
        seed_text = st.text_input("Draft Seed", placeholder="留空表示不指定")
        auto_wait = st.checkbox("创建后自动轮询 Draft", value=True)
        download = st.checkbox("完成后下载 Draft 视频", value=False)
        submitted = st.form_submit_button("创建 Draft 任务", use_container_width=True)

    if submitted:

        def action() -> None:
            service = get_service_or_raise()
            images = build_image_inputs(image_urls, list(uploaded_images or []))
            task_ref = run_async(
                service.create_draft_video_task(
                    prompt=prompt,
                    images=images,
                    model=draft_model,
                    duration=int(duration),
                    seed=parse_optional_int(seed_text, "Draft Seed"),
                )
            )
            remember_task_id(task_ref.task_id, is_draft=True)
            render_task_reference(task_ref)

            if auto_wait:
                result = run_async(
                    service.wait_video_task(
                        task_id=task_ref.task_id,
                        poll_interval_seconds=settings.poll_interval_seconds,
                        timeout_seconds=settings.timeout_seconds,
                        download=download,
                        output_dir=None,
                    )
                )
                render_task_result(result, heading="Draft 结果")

        execute_action("正在创建 Draft 视频...", action)

    st.markdown("### 2. 基于 Draft 生成正式视频")
    with st.form("draft_final_form"):
        draft_task_id = st.text_input(
            "Draft Task ID",
            value=st.session_state.latest_draft_task_id,
            placeholder="输入 Draft 任务 ID",
        )
        resolution = st.selectbox(
            "正式视频分辨率",
            [DEFAULT_OPTION, *ordered_choices(caps.resolutions, RESOLUTION_ORDER)],
            index=2 if "720p" in caps.resolutions else 0,
        )
        service_tier = st.selectbox("推理层级", sorted(caps.supported_service_tiers))
        return_last_frame = st.checkbox(
            "正式视频返回尾帧",
            value=True,
            disabled=not caps.supports_return_last_frame,
        )
        watermark = st.checkbox("正式视频带水印", value=False)
        auto_wait = st.checkbox("创建后自动轮询正式视频", value=True)
        download = st.checkbox("完成后下载正式视频", value=False)
        submitted = st.form_submit_button("创建正式视频任务", use_container_width=True)

    if submitted:

        def action() -> None:
            service = get_service_or_raise()
            task_ref = run_async(
                service.create_final_video_from_draft(
                    draft_task_id=draft_task_id,
                    model=draft_model,
                    resolution=optional_choice(resolution),
                    watermark=watermark,
                    return_last_frame=return_last_frame,
                    service_tier=service_tier,
                )
            )
            render_task_reference(task_ref)
            if auto_wait:
                result = run_async(
                    service.wait_video_task(
                        task_id=task_ref.task_id,
                        poll_interval_seconds=settings.poll_interval_seconds,
                        timeout_seconds=settings.timeout_for(service_tier),
                        download=download,
                        output_dir=None,
                    )
                )
                render_task_result(result, heading="正式视频结果")

        execute_action("正在生成正式视频...", action)


def render_sequence_tab(settings: Any) -> None:
    st.subheader("连续视频生成")
    sequence_models = [
        model for model, caps in MODEL_CAPABILITIES.items() if caps.supports_return_last_frame
    ]
    default_index = sequence_models.index(settings.default_model)
    model = st.selectbox("选择连续生成模型", sequence_models, index=default_index)
    caps = render_capabilities(model)

    with st.form("sequence_form"):
        prompts = st.text_area(
            "分段 Prompt",
            height=160,
            placeholder="每行一个分段 prompt，至少两行。",
        )
        image_urls = st.text_area("首段初始图片 URL", placeholder="每行一个 URL，可留空")
        uploaded_images = st.file_uploader(
            "或上传首段图片",
            type=["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"],
            accept_multiple_files=True,
            key="sequence_uploaded_images",
        )

        left, middle, right = st.columns(3)
        resolution = left.selectbox(
            "分辨率",
            [DEFAULT_OPTION, *ordered_choices(caps.resolutions, RESOLUTION_ORDER)],
            key="sequence_resolution",
        )
        ratio = middle.selectbox(
            "宽高比",
            [DEFAULT_OPTION, *ordered_choices(caps.ratios, RATIO_ORDER)],
            index=1 if "16:9" in caps.ratios else 0,
            key="sequence_ratio",
        )
        duration = right.number_input(
            "每段时长（秒）",
            min_value=caps.duration_range[0],
            max_value=caps.duration_range[1],
            value=min(5, caps.duration_range[1]),
        )
        watermark = st.checkbox("包含水印", value=False, key="sequence_watermark")
        submitted = st.form_submit_button("生成连续视频", use_container_width=True)

    if not submitted:
        return

    def action() -> None:
        service = get_service_or_raise()
        result = run_async(
            service.generate_video_sequence(
                segments=build_sequence_segments(prompts),
                initial_images=build_image_inputs(image_urls, list(uploaded_images or [])),
                model=model,
                resolution=optional_choice(resolution),
                ratio=optional_choice(ratio) or "adaptive",
                duration=int(duration),
                watermark=watermark,
            )
        )
        st.success(f"连续视频生成完成，共 {result.segment_count} 段。")
        for item in result.results:
            render_task_result(item.task, heading=f"第 {item.index} 段")

    execute_action("正在生成连续视频...", action)


def render_task_management_tab(settings: Any) -> None:
    st.subheader("任务管理")
    history_options = ["", *st.session_state.task_history]

    st.markdown("### 查询单个任务")
    with st.form("get_task_form"):
        selected_task = st.selectbox("最近任务", history_options, key="get_selected_task")
        task_id = st.text_input(
            "任务 ID",
            value=st.session_state.latest_task_id,
            key="get_task_id_input",
        )
        submitted = st.form_submit_button("查询任务", use_container_width=True)

    if submitted:

        def action() -> None:
            service = get_service_or_raise()
            effective_task_id = task_id.strip() or selected_task
            result = run_async(service.get_video_task(task_id=effective_task_id))
            render_task_result(result)

        execute_action("正在查询任务...", action)

    st.markdown("### 等待任务完成")
    with st.form("wait_task_form"):
        selected_task = st.selectbox("最近任务 ID", history_options, key="wait_selected_task")
        task_id = st.text_input("任务 ID", key="wait_task_id_input")
        poll_interval = st.number_input(
            "轮询间隔（秒）",
            min_value=1,
            max_value=60,
            value=settings.poll_interval_seconds,
            key="wait_poll_interval",
        )
        timeout_seconds = st.number_input(
            "超时（秒，填 0 使用默认值）",
            min_value=0,
            max_value=86400,
            value=0,
            key="wait_timeout",
        )
        download = st.checkbox("完成后下载到本地", value=False, key="wait_download")
        output_dir = st.text_input(
            "下载目录",
            placeholder=str(settings.output_dir),
            key="wait_output_dir",
        )
        submitted = st.form_submit_button("开始等待", use_container_width=True)

    if submitted:

        def action() -> None:
            service = get_service_or_raise()
            effective_task_id = task_id.strip() or selected_task
            result = run_async(
                service.wait_video_task(
                    task_id=effective_task_id,
                    poll_interval_seconds=int(poll_interval),
                    timeout_seconds=None if timeout_seconds == 0 else int(timeout_seconds),
                    download=download,
                    output_dir=output_dir.strip() or None,
                )
            )
            render_task_result(result, heading="等待结果")

        execute_action("正在轮询任务...", action)

    st.markdown("### 查询任务列表")
    with st.form("list_tasks_form"):
        status = st.selectbox(
            "状态过滤",
            ["", "queued", "running", "succeeded", "failed", "expired"],
        )
        page_size = st.number_input("page_size", min_value=1, max_value=100, value=20)
        page_token = st.text_input("page_token", placeholder="可留空")
        submitted = st.form_submit_button("查询列表", use_container_width=True)

    if submitted:

        def action() -> None:
            service = get_service_or_raise()
            result = run_async(
                service.list_video_tasks(
                    status=status or None,
                    page_size=int(page_size),
                    page_token=page_token.strip() or None,
                )
            )
            st.success(f"返回 {len(result.tasks)} 条任务记录。")
            st.json(result.model_dump(mode="json"))
            for item in result.tasks:
                render_task_result(item, heading=f"任务 {item.task_id}")

        execute_action("正在查询任务列表...", action)

    st.markdown("### 删除或取消任务")
    with st.form("delete_task_form"):
        selected_task = st.selectbox("最近任务记录", history_options, key="delete_selected_task")
        task_id = st.text_input("任务 ID", key="delete_task_id_input")
        submitted = st.form_submit_button("删除任务", use_container_width=True)

    if submitted:

        def action() -> None:
            service = get_service_or_raise()
            effective_task_id = task_id.strip() or selected_task
            result = run_async(service.delete_video_task(task_id=effective_task_id))
            st.success(result.message)
            st.json(result.model_dump(mode="json"))

        execute_action("正在删除任务...", action)


def main() -> None:
    st.set_page_config(
        page_title="Seedance 测试控制台",
        page_icon="S",
        layout="wide",
    )
    ensure_state()
    settings = get_settings()
    render_styles()
    render_header(settings)
    render_sidebar(settings)

    tab_create, tab_draft, tab_sequence, tab_tasks = st.tabs(
        ["基础生成", "Draft 流程", "连续视频", "任务管理"]
    )
    with tab_create:
        render_create_tab(settings)
    with tab_draft:
        render_draft_tab(settings)
    with tab_sequence:
        render_sequence_tab(settings)
    with tab_tasks:
        render_task_management_tab(settings)


if __name__ == "__main__":
    main()
