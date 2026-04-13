"""Shared log-sanitization utility.

Prevents log injection by stripping CR/LF and other control characters
from user-controlled values before they are interpolated into log messages.

Defence-in-depth: the ``LogSanitizationFilter`` can be attached to any
``logging.Handler`` to sanitise **all** log output at the framework level,
regardless of whether individual call-sites use ``sanitize_log_value``.
"""

import logging
import re

# Matches ASCII control characters that can be used for log injection
# (newlines, carriage returns, and other C0 controls except tab).
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")


def sanitize_log_value(value: object) -> str:
    """Sanitise *value* for safe inclusion in log messages.

    Replaces newlines, carriage returns, and other ASCII control characters
    with a space so that attackers cannot forge new log entries.
    """
    return _CONTROL_CHAR_RE.sub(" ", str(value))


def _sanitize_arg(arg: object) -> object:
    """Sanitise a single log-record argument if it is a string."""
    if isinstance(arg, str):
        return _CONTROL_CHAR_RE.sub(" ", arg)
    return arg


class LogSanitizationFilter(logging.Filter):
    """Logging filter that strips control characters from all log output.

    Attach to a handler via ``handler.addFilter(LogSanitizationFilter())``.
    This ensures that even if individual call-sites forget to sanitise
    user-controlled data, log injection is still prevented.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _CONTROL_CHAR_RE.sub(" ", record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: _sanitize_arg(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(_sanitize_arg(a) for a in record.args)
        return True
