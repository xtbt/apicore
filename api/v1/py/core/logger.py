"""Logging configuration: one console handler shared by every module.

Layer: core (cross-cutting). main.py calls configure_logging() once at startup;
everywhere else uses the root logger via logging.info()/logging.exception().
"""
import logging
from datetime import datetime

from utils.date_utils import LOCAL_TZ


def _local_time_converter(seconds):
    """Log timestamps in APP_TIMEZONE (America/Tijuana), not the machine clock.

    Set on the formatter instance: a class-level function would receive `self`
    as first argument.
    """
    return datetime.fromtimestamp(seconds, LOCAL_TZ).timetuple()


def configure_logging():
    """Set up the root logger: format, local-time timestamps and console output."""
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    formatter.converter = _local_time_converter
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    # The connector logs every plugin detail at INFO: keep it at warnings only
    logging.getLogger('mysql.connector').setLevel(logging.WARNING)
