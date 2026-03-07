"""Custom exception hierarchy for OSSTriage."""

from __future__ import annotations


class OSSTriageError(Exception):
    """Base exception for all OSSTriage errors."""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class ConfigError(OSSTriageError):
    """Raised when a required configuration value is missing or invalid."""


class GitHubAPIError(OSSTriageError):
    """Raised when a GitHub API call fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.status_code = status_code


class RateLimitError(GitHubAPIError):
    """Raised when the GitHub API rate limit is exceeded."""

    def __init__(self, reset_at: str, *, cause: Exception | None = None) -> None:
        super().__init__(
            f"GitHub API rate limit exceeded. Resets at {reset_at}",
            status_code=403,
            cause=cause,
        )
        self.reset_at = reset_at


class AIModuleError(OSSTriageError):
    """Raised when an AI/DSPy module fails to produce a valid result."""
