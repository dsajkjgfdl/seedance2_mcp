# Seedance FastMCP 工具清单

本文档用于审查当前 Seedance FastMCP 服务中已经实现并注册的 MCP Tools。

当前服务入口位于 `server.py`，工具注册位于 `src/seedance_mcp/tools/video.py` 的 `register_video_tools()`。

## 当前能力概览

- MCP 服务名：`seedance-video`
- 当前已注册工具数：`8`
- 当前未实现：`resources`、`prompts`、Webhook 接收服务、对象存储上传、FFmpeg 拼接
- 当前页面测试入口：`streamlit_app.py`

## 工具列表

### 1. `create_video_task`

作用：
创建一个通用的视频生成任务，覆盖文生视频、图生视频、多模态参考、视频参考、音频参考等场景。

主要参数：

- `prompt`
- `images`
- `videos`
- `audios`
- `model`
- `resolution`
- `ratio`
- `duration`
- `frames`
- `seed`
- `camera_fixed`
- `watermark`
- `generate_audio`
- `return_last_frame`
- `service_tier`
- `callback_url`

返回：

- `TaskReference`
- 字段：`task_id`、`model`、`service_tier`

说明：

- 图片支持 `url` 和 `base64`
- 视频和音频当前只支持 `url`
- 调用前会执行模型能力与参数组合校验

### 2. `create_draft_video_task`

作用：
创建 Draft 样片视频任务，目前用于 Seedance 1.5 Pro 的低成本预览流程。

主要参数：

- `prompt`
- `duration`
- `images`
- `model`
- `seed`

返回：

- `TaskReference`

说明：

- 内部固定 `draft=true`
- 当前只允许支持 Draft 的模型使用
- 当前默认模型为 `doubao-seedance-1-5-pro-251215`

### 3. `create_final_video_from_draft`

作用：
基于已有 Draft 任务 ID 生成正式视频。

主要参数：

- `draft_task_id`
- `model`
- `resolution`
- `watermark`
- `return_last_frame`
- `service_tier`

返回：

- `TaskReference`

说明：

- 内部使用 `content=[{"type": "draft_task", ...}]`
- 调用前会校验模型是否支持 Draft 正式生成链路

### 4. `get_video_task`

作用：
查询单个视频任务当前状态和结果。

主要参数：

- `task_id`

返回：

- `VideoTaskResult`

主要返回字段：

- `task_id`
- `model`
- `status`
- `video_url`
- `last_frame_url`
- `usage`
- `resolution`
- `ratio`
- `duration`
- `fps`
- `service_tier`
- `error`

### 5. `wait_video_task`

作用：
轮询等待任务完成，直到进入终态。

主要参数：

- `task_id`
- `poll_interval_seconds`
- `timeout_seconds`
- `download`
- `output_dir`

返回：

- `WaitVideoTaskResult`

额外字段：

- `saved_path`

说明：

- 终态包括：`succeeded`、`failed`、`expired`
- 成功且 `download=true` 时，会把视频下载到本地
- 默认下载目录来自环境变量 `SEEDANCE_OUTPUT_DIR`

### 6. `list_video_tasks`

作用：
查询任务列表，可按状态过滤。

主要参数：

- `status`
- `page_size`
- `page_token`

返回：

- `ListVideoTasksResult`

主要返回字段：

- `tasks`
- `next_page_token`
- `has_more`
- `raw_page`

### 7. `delete_video_task`

作用：
删除任务记录，或取消尚未完成的任务。

主要参数：

- `task_id`

返回：

- `DeleteVideoTaskResult`

主要返回字段：

- `task_id`
- `deleted`
- `message`

### 8. `generate_video_sequence`

作用：
生成多段连续视频，并使用上一段的 `last_frame_url` 作为下一段首帧，实现镜头连续衔接。

主要参数：

- `segments`
- `initial_images`
- `model`
- `resolution`
- `ratio`
- `duration`
- `watermark`

返回：

- `VideoSequenceResult`

主要返回字段：

- `model`
- `segment_count`
- `results`

说明：

- 每个分段使用 `VideoSequenceSegment`
- 当前流程内部会自动调用 `create_video_task` 和 `wait_video_task`
- 若某一段没有返回 `last_frame_url`，链式生成会报错

## 当前公共输入类型

### `ImageInput`

- `url: str | None`
- `base64: str | None`

约束：

- 两者必须且只能提供一个

### `VideoInput`

- `url: str`

### `AudioInput`

- `url: str`

### `VideoSequenceSegment`

- `prompt: str`
- `images: list[ImageInput]`
- `videos: list[VideoInput]`
- `audios: list[AudioInput]`

## 当前公共状态枚举

任务状态统一按以下值处理：

- `queued`
- `running`
- `succeeded`
- `failed`
- `expired`

## 当前默认配置

- 默认模型：`doubao-seedance-2-0-260128`
- 默认 Draft 模型：`doubao-seedance-1-5-pro-251215`
- 默认轮询间隔：`10` 秒
- 默认在线超时：`1800` 秒
- 默认 flex 超时：`21600` 秒

## 审查重点建议

- 工具命名是否满足你的调用习惯
- `create_video_task` 是否还需要继续拆分成更细粒度工具
- `list_video_tasks` 的分页字段是否要进一步标准化
- `wait_video_task` 是否需要增加更细的进度回调输出
- `generate_video_sequence` 是否需要扩展为自动拼接成长视频

