import asyncio

from seedance_mcp.server import mcp


def test_server_registers_expected_tools() -> None:
    tool_names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    assert tool_names == {
        "create_video_task",
        "create_draft_video_task",
        "create_final_video_from_draft",
        "get_video_task",
        "wait_video_task",
        "list_video_tasks",
        "delete_video_task",
        "generate_video_sequence",
    }
