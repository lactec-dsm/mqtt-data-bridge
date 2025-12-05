"""
logger.py

Utilitário simples para padronizar logs do projeto.

- Respeita `settings.LOG_LEVEL` e `settings.LOG_JSON`.
- Configura um handler de console único para evitar handlers duplicados.
- Exponibiliza `get_logger(name)` para uso nos módulos.
"""

import json
import logging
from typing import Any, Dict

from mqtt_data_bridge.config.settings import settings

_CONFIGURED = False


class JSONFormatter(logging.Formatter):
    """
    Formata logs como JSON, incluindo campos básicos.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def _configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    handler = logging.StreamHandler()

    if settings.LOG_JSON:
        formatter: logging.Formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    handler.setFormatter(formatter)

    # Evita acumular handlers se o módulo for importado várias vezes
    root.handlers.clear()
    root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado.
    """
    if not _CONFIGURED:
        _configure_logging()
    return logging.getLogger(name)
