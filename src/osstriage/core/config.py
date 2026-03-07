"""Configuration management for OSSTriage.

Reads settings from environment variables and ``.env`` files with
clear validation and error messages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from osstriage.core.exceptions import ConfigError


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable application settings loaded from the environment.

    Attributes:
        github_token: GitHub Personal Access Token.
        openai_api_key: OpenAI API key for LLM access.
        log_level: Logging verbosity (default ``INFO``).
        model: OpenAI model identifier (default ``gpt-4o``).
    """

    github_token: str
    openai_api_key: str
    log_level: str = "INFO"
    model: str = "gpt-4o"

    # Private: paths searched for .env (not exposed as a setting)
    _env_paths: tuple[str, ...] = field(default=(".env",), repr=False)

    @classmethod
    def load(cls, env_file: str | Path | None = None) -> Settings:
        """Load settings from environment variables, optionally reading a ``.env`` file first.

        The method searches for ``.env`` in the current working directory by
        default.  Explicit *env_file* takes precedence.

        Args:
            env_file: Path to a specific ``.env`` file (optional).

        Returns:
            A validated :class:`Settings` instance.

        Raises:
            ConfigError: If required environment variables are missing.
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()  # searches cwd and parents

        github_token = os.getenv("GITHUB_TOKEN", "").strip()
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

        missing: list[str] = []
        if not github_token:
            missing.append("GITHUB_TOKEN")
        if not openai_api_key:
            missing.append("OPENAI_API_KEY")

        if missing:
            vars_str = ", ".join(missing)
            raise ConfigError(
                f"Missing required environment variable(s): {vars_str}. "
                f"Set them in your shell or create a .env file "
                f"(see .env.example for reference)."
            )

        return cls(
            github_token=github_token,
            openai_api_key=openai_api_key,
            log_level=os.getenv("OSSTRIAGE_LOG_LEVEL", "INFO").strip().upper(),
            model=os.getenv("OSSTRIAGE_MODEL", "gpt-4o").strip(),
        )
