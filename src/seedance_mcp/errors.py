class SeedanceMCPError(Exception):
    """Base exception for this MCP server."""


class ConfigurationError(SeedanceMCPError):
    """Raised when environment or dependency configuration is invalid."""


class InputValidationError(SeedanceMCPError):
    """Raised when tool input does not match supported Seedance capabilities."""


class ArkAPIError(SeedanceMCPError):
    """Raised when the Ark SDK request fails."""


class TaskTimeoutError(SeedanceMCPError):
    """Raised when waiting for a task exceeds the allowed timeout."""
