"""OpenTelemetry / Azure Monitor configuration."""

from __future__ import annotations

import logging

import structlog

from src.common.config import Settings, get_settings

_CONFIGURED = False


def configure_telemetry(settings: Settings | None = None) -> None:
    """Configure structured logging and (if enabled) Azure Monitor exporters.

    Idempotent — safe to call from each FastAPI app at startup.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    cfg = settings or get_settings()
    level = getattr(logging, cfg.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    if cfg.enable_telemetry and cfg.applicationinsights_connection_string:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(
                connection_string=cfg.applicationinsights_connection_string,
                logger_name="foundry_usecase_factory",
            )
        except Exception as exc:  # pragma: no cover — defensive
            logging.getLogger(__name__).warning("Azure Monitor not configured: %s", exc)

    _CONFIGURED = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
