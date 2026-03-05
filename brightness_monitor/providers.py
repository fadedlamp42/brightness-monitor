"""usage provider adapters for brightness-monitor.

supports:
  - claude: polls anthropic oauth usage endpoint (existing behavior)
  - codex: polls codex/chatgpt usage endpoint (`/backend-api/wham/usage`)
  - codex_logs: reads local codex session logs for rate-limit windows
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from prism.logging import get_logger

from brightness_monitor.auth import attempt_reauth
from brightness_monitor.usage import UsageData, fetch_usage, get_token

if TYPE_CHECKING:
    from brightness_monitor.config import Config

logger = get_logger()


class UsageProvider:
    """provider contract for all usage backends."""

    provider_name = "unknown"

    def fetch_usage(self) -> UsageData:
        raise NotImplementedError

    def attempt_reauth(self) -> bool:
        return False


class ClaudeUsageProvider(UsageProvider):
    """usage provider that delegates to the existing claude oauth implementation."""

    provider_name = "claude"

    def __init__(self, token_override: str | None = None):
        self._token_override = token_override

    def fetch_usage(self) -> UsageData:
        token = get_token(explicit_token=self._token_override)
        return fetch_usage(token)

    def attempt_reauth(self) -> bool:
        return attempt_reauth()


def create_usage_provider(config: Config, token_override: str | None = None) -> UsageProvider:
    """build the configured usage provider instance."""
    provider_name = config.provider.name.strip().lower()

    if provider_name == "claude":
        return ClaudeUsageProvider(token_override=token_override)

    if provider_name in {"codex", "codex_api"}:
        from brightness_monitor.codex_api_provider import CodexApiUsageProvider

        codex_config = config.provider.codex
        return CodexApiUsageProvider(
            auth_file=Path(codex_config.auth_file),
            fallback_auth_files=codex_config.fallback_auth_files,
            usage_url=codex_config.usage_url,
            refresh_url=codex_config.refresh_url,
            refresh_client_id=codex_config.refresh_client_id,
            request_timeout_seconds=codex_config.request_timeout_seconds,
            token_override=token_override,
        )

    if provider_name == "codex_logs":
        from brightness_monitor.codex_log_provider import CodexLogUsageProvider

        if token_override:
            logger.warning("ignoring --token for codex_logs provider")

        codex_config = config.provider.codex
        return CodexLogUsageProvider(
            sessions_root=Path(codex_config.sessions_root),
            max_staleness_seconds=codex_config.max_staleness_seconds,
        )

    raise RuntimeError(
        "unknown provider '%(provider)s'. expected one of: claude, codex, codex_logs"
        % {"provider": config.provider.name}
    )
