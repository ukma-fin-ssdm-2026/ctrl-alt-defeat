"""
Reading numeric settings from the environment (reliability report, finding 15).

A typo in a hosting dashboard ("24h", an empty value, a negative number) must not stop the API at import
time with a bare ValueError. These settings are not critical, so the reaction is a safe failure:
the default value is used and the log names the variable and the rejected value.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def env_int(name: str, default: int, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    """Integer from the environment variable `name`; the default when it is unset, not a number or out of range."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        logger.warning("%s=%r is not a whole number; using the default %s.", name, raw, default)
        return default
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        logger.warning("%s=%s is outside %s..%s; using the default %s.", name, value, minimum, maximum, default)
        return default
    return value
