"""Logging helpers and request tracing."""

import contextvars
import logging
import uuid
from collections.abc import Callable

from fastapi import Request, Response

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


class TraceIdFilter(logging.Filter):
    """Inject the active trace id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure global logging once."""

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.addFilter(TraceIdFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(trace_id)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())


async def trace_middleware(
    request: Request, call_next: Callable[[Request], Response]
) -> Response:
    """Attach a trace id to each request."""

    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    token = trace_id_var.set(trace_id)
    try:
        response = await call_next(request)
    finally:
        trace_id_var.reset(token)
    response.headers["X-Trace-Id"] = trace_id
    return response


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""

    return logging.getLogger(name)
