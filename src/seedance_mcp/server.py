from __future__ import annotations

from fastmcp import FastMCP

from .tools import register_video_tools

mcp = FastMCP("seedance-video")
register_video_tools(mcp)


def main() -> None:
    mcp.run()
