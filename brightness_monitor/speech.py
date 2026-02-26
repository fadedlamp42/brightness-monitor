"""voice output for brightness-monitor via cute-say.

two modes:
  - whisper: short, ambient hourly readout via chatterbox with [whispering] tag
  - full report: thorough status via kokoro at 1.4x speed covering all windows
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from typing import Optional

from brightness_monitor.usage import UsageData

log = logging.getLogger(__name__)


def _format_relative_time(target: Optional[datetime]) -> str:
    """format a datetime as natural spoken relative time.

    returns phrases like "in about an hour", "in 3 days", "tomorrow".
    returns empty string if target is None.
    """
    if target is None:
        return ""

    now = datetime.now(tz=target.tzinfo)
    total_seconds = (target - now).total_seconds()

    if total_seconds <= 0:
        return "any moment now"

    minutes = total_seconds / 60
    hours = total_seconds / 3600
    days = total_seconds / 86400

    if minutes < 2:
        return "in about a minute"
    if hours < 1:
        return "in %d minutes" % int(minutes)
    if hours < 2:
        return "in about an hour"
    if hours < 24:
        return "in %d hours" % int(hours)
    if days < 2:
        return "tomorrow"

    return "in %d days" % int(days)


def format_voice_status(usage: UsageData) -> str:
    """format a thorough spoken status update for cute-say.

    includes: hourly remaining (for verifying blink readouts), weekly remaining,
    per-model breakdown (opus/sonnet), and reset times for all windows.
    plain delivery, no paralinguistic tags.
    """
    windows_by_name = {w.name: w for w in usage.windows}

    five_hour = windows_by_name.get("five_hour")
    seven_day = windows_by_name.get("seven_day")
    opus = windows_by_name.get("seven_day_opus")
    sonnet = windows_by_name.get("seven_day_sonnet")

    parts = []

    # hourly first — this is what the keyboard blinks show, so state it
    # clearly so the user can verify what they just saw
    if five_hour:
        hr_left = int(100 - five_hour.utilization)
        reset = _format_relative_time(five_hour.resets_at)
        fragment = "hourly has %d percent left" % hr_left
        if reset:
            fragment += ", resets %s" % reset
        parts.append(fragment)

    # weekly aggregate
    if seven_day:
        wk_left = int(100 - seven_day.utilization)
        reset = _format_relative_time(seven_day.resets_at)
        fragment = "weekly has %d percent left" % wk_left
        if reset:
            fragment += ", resets %s" % reset
        parts.append(fragment)

    # per-model breakdown when available
    model_bits = []
    if opus:
        model_bits.append("opus at %d" % int(100 - opus.utilization))
    if sonnet:
        model_bits.append("sonnet at %d" % int(100 - sonnet.utilization))
    if model_bits:
        parts.append(", ".join(model_bits))

    return ". ".join(parts)


def whisper_hourly(usage: UsageData) -> None:
    """fire-and-forget: whisper the hourly remaining % via chatterbox.

    uses the [whispering] paralinguistic tag for a subtle, ambient readout.
    chatterbox (default mode) supports these tags natively.
    """
    windows_by_name = {w.name: w for w in usage.windows}
    five_hour = windows_by_name.get("five_hour")
    if not five_hour:
        log.warning("no five_hour window available for whisper readout")
        return

    hr_left = int(100 - five_hour.utilization)
    text = "[whispering] %d percent" % hr_left
    log.info("whisper readout: %(text)s", {"text": text})

    try:
        subprocess.Popen(
            ["cute-say", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        log.warning("cute-say not found in PATH, skipping whisper readout")


def speak_full_status(usage: UsageData) -> None:
    """fire-and-forget: thorough voice status via kokoro at 1.4x speed.

    covers hourly, weekly, per-model breakdown, and reset times.
    uses kokoro mode for speed control.
    """
    text = format_voice_status(usage)
    log.info("voice readout: %(text)s", {"text": text})

    try:
        subprocess.Popen(
            ["cute-say", "-k", "-s", "1.4", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        log.warning("cute-say not found in PATH, skipping voice readout")
