"""Shared log-sanitization utility.

Prevents log injection by stripping CR/LF from user-controlled values
before they are interpolated into log messages.
"""


def sanitize_log_value(value: object) -> str:
    """Sanitise *value* for safe inclusion in log messages."""
    return str(value).replace("\n", " ").replace("\r", " ")
