"""re-authentication flow for expired OAuth tokens.

wraps `claude auth login` to restore credentials when the API
returns 401. used both at daemon startup (proactive validation)
and during runtime (periodic auto-reauth to minimize UsageDB gaps).
"""

from __future__ import annotations

import logging
import shutil
import subprocess

log = logging.getLogger(__name__)

# how often to automatically attempt re-authentication when token is expired.
# keeps UsageDB gaps to at most this duration instead of waiting for SIGUSR1.
REAUTH_INTERVAL_SECONDS = 300  # 5 minutes


def attempt_reauth() -> bool:
    """run `claude auth login` and return whether it succeeded.

    blocks until the OAuth flow completes (user clicks through browser).
    returns False if claude CLI isn't found or the process exits non-zero.
    """
    claude_path = shutil.which("claude")
    if not claude_path:
        log.error("claude CLI not found in PATH, cannot re-authenticate")
        return False

    log.info("starting claude auth login")
    try:
        result = subprocess.run(
            [claude_path, "auth", "login"],
            timeout=120,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log.info("claude auth login succeeded")
            return True

        log.warning(
            "claude auth login failed (exit %(code)d): %(stderr)s",
            {"code": result.returncode, "stderr": result.stderr.strip()},
        )
        return False
    except subprocess.TimeoutExpired:
        log.warning("claude auth login timed out after 120s")
        return False
    except Exception as error:
        log.warning(
            "claude auth login error: %(error)s",
            {"error": error},
        )
        return False
