"""keyboard brightness control via CoreBrightness private framework.

uses pyobjc to load Apple's private CoreBrightness.framework and
talk to KeyboardBrightnessClient, the same interface that
mac-brightnessctl and KBPulse use under the hood.
"""

from __future__ import annotations

import logging

import objc

log = logging.getLogger(__name__)

BUILTIN_KEYBOARD_ID = 1

# lazy-loaded singleton; framework loading is expensive
_client = None


def _load_client():
    """load CoreBrightness.framework and create a KeyboardBrightnessClient."""
    global _client
    if _client is not None:
        return _client

    bundle_path = "/System/Library/PrivateFrameworks/CoreBrightness.framework"

    try:
        objc.loadBundle(
            "CoreBrightness",
            bundle_path=bundle_path,
            module_globals=globals(),
        )
        KeyboardBrightnessClient = objc.lookUpClass("KeyboardBrightnessClient")
        _client = KeyboardBrightnessClient.alloc().init()
        log.debug("loaded CoreBrightness framework")
        return _client
    except Exception as error:
        raise RuntimeError(
            "failed to load CoreBrightness.framework: %(error)s" % {"error": error}
        ) from error


def get_brightness() -> float:
    """get current keyboard brightness (0.0 to 1.0)."""
    client = _load_client()
    return float(client.brightnessForKeyboard_(BUILTIN_KEYBOARD_ID))


def set_brightness(level: float, fade_speed: int = -1) -> None:
    """set keyboard brightness (0.0 to 1.0), clamped to valid range.

    fade_speed controls the transition:
      -1 = system default (smooth fade)
       0 = instant snap (no fade)
       higher values = slower fades
    """
    level = max(0.0, min(1.0, level))
    client = _load_client()
    if fade_speed < 0:
        client.setBrightness_forKeyboard_(level, BUILTIN_KEYBOARD_ID)
    else:
        client.setBrightness_fadeSpeed_commit_forKeyboard_(
            level,
            fade_speed,
            True,
            BUILTIN_KEYBOARD_ID,
        )


def suspend_idle_dimming(suspend: bool) -> None:
    """prevent or allow the keyboard from auto-dimming on idle.

    must be suspended while we're controlling brightness,
    otherwise the system fights us.
    """
    client = _load_client()
    client.suspendIdleDimming_forKeyboard_(suspend, BUILTIN_KEYBOARD_ID)


def set_auto_brightness(enabled: bool) -> None:
    """enable or disable ambient-light auto-brightness.

    should be disabled while we're controlling brightness directly.
    """
    client = _load_client()
    client.enableAutoBrightness_forKeyboard_(enabled, BUILTIN_KEYBOARD_ID)
