from __future__ import annotations

from functools import lru_cache
from typing import Any

from .config import get_settings
from .errors import ArkAPIError, ConfigurationError


def _to_plain_data(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {key: _to_plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_plain_data(item) for item in value]
    if hasattr(value, "model_dump"):
        return _to_plain_data(value.model_dump(exclude_none=True))
    if hasattr(value, "to_dict"):
        return _to_plain_data(value.to_dict())
    if hasattr(value, "__dict__"):
        return {
            key: _to_plain_data(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


class ArkVideoGenerationClient:
    def __init__(self, sdk_client: Any) -> None:
        self._sdk_client = sdk_client

    def create_task(self, payload: dict[str, Any]) -> Any:
        try:
            return self._sdk_client.content_generation.tasks.create(**payload)
        except Exception as exc:  # noqa: BLE001
            raise ArkAPIError(f"Failed to create video task: {exc}") from exc

    def get_task(self, task_id: str) -> Any:
        try:
            return self._sdk_client.content_generation.tasks.get(task_id=task_id)
        except Exception as exc:  # noqa: BLE001
            raise ArkAPIError(f"Failed to get video task '{task_id}': {exc}") from exc

    def list_tasks(
        self,
        *,
        page_size: int,
        status: str | None = None,
        page_token: str | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {"page_size": page_size}
        if status:
            kwargs["status"] = status
        if page_token:
            kwargs["page_token"] = page_token

        try:
            return self._sdk_client.content_generation.tasks.list(**kwargs)
        except TypeError as exc:
            kwargs.pop("page_token", None)
            if page_token is not None:
                raise ArkAPIError(
                    "This SDK version does not support page_token for list_tasks."
                ) from exc
            return self._sdk_client.content_generation.tasks.list(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise ArkAPIError(f"Failed to list video tasks: {exc}") from exc

    def delete_task(self, task_id: str) -> None:
        try:
            self._sdk_client.content_generation.tasks.delete(task_id=task_id)
        except Exception as exc:  # noqa: BLE001
            raise ArkAPIError(f"Failed to delete video task '{task_id}': {exc}") from exc


@lru_cache(maxsize=1)
def get_ark_client() -> ArkVideoGenerationClient:
    settings = get_settings()
    if not settings.ark_api_key:
        raise ConfigurationError("ARK_API_KEY is required.")

    try:
        from volcenginesdkarkruntime import Ark
    except ImportError as exc:
        raise ConfigurationError(
            "volcengine-python-sdk[ark] is not installed. Run `uv sync --extra dev`."
        ) from exc

    sdk_client = Ark(api_key=settings.ark_api_key, base_url=settings.ark_base_url)
    return ArkVideoGenerationClient(sdk_client)


__all__ = ["ArkVideoGenerationClient", "get_ark_client", "_to_plain_data"]
