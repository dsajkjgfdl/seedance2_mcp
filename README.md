# Seedance FastMCP

Seedance video generation MCP server built with FastMCP v3 and the Volcengine Ark Python SDK.

## Features

- Unified video creation tool for text, image, video, and audio references
- Draft-to-final flow for `doubao-seedance-1-5-pro-251215`
- Task get / wait / list / delete helpers
- Sequence generation with previous `last_frame_url` chaining
- URL-first media inputs, with image Base64 support
- Local file download only when requested

## Requirements

- Python 3.11+
- `ARK_API_KEY`

## Quick Start

```bash
uv sync --extra dev
```

Create a `.env` file from `.env.example` and set `ARK_API_KEY`.

Run the server directly:

```bash
uv run python server.py
```

Or run it with the FastMCP CLI:

```bash
uv run fastmcp run server.py
```

Run the Streamlit test console:

```bash
uv run streamlit run streamlit_app.py
```

## Environment Variables

- `ARK_API_KEY`: required
- `ARK_BASE_URL`: default `https://ark.cn-beijing.volces.com/api/v3`
- `SEEDANCE_DEFAULT_MODEL`: default `doubao-seedance-2-0-260128`
- `SEEDANCE_DEFAULT_DRAFT_MODEL`: default `doubao-seedance-1-5-pro-251215`
- `SEEDANCE_OUTPUT_DIR`: default `outputs/seedance`
- `SEEDANCE_POLL_INTERVAL_SECONDS`: default `10`
- `SEEDANCE_TIMEOUT_SECONDS`: default `1800`
- `SEEDANCE_FLEX_TIMEOUT_SECONDS`: default `21600`

## Available Tools

- `create_video_task`
- `create_draft_video_task`
- `create_final_video_from_draft`
- `get_video_task`
- `wait_video_task`
- `list_video_tasks`
- `delete_video_task`
- `generate_video_sequence`

## Testing

```bash
uv run pytest
```
