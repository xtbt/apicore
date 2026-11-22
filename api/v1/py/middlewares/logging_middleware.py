"""Structured request log: IP METHOD ROUTE STATUS DURATIONms.

Layer: middlewares (cross-cutting). Sits inside error_middleware, so it logs the
status of a failed request too, before the error is translated into a response.
"""
import logging
import time

from core.exceptions import AppError
from middlewares.base import Middleware


class LoggingMiddleware(Middleware):
    """Times every request and logs one line per request, whatever its outcome."""

    def handle(self, request, call_next):
        start = time.perf_counter()
        try:
            response = call_next(request)
        except AppError as error:
            self._log(request, error.status_code, start)
            raise
        except ValueError:
            self._log(request, 400, start)
            raise
        except Exception:
            self._log(request, 500, start)
            raise
        self._log(request, response.status, start)
        return response

    @staticmethod
    def _log(request, status, start):
        logging.info('%s %s %s %s %dms', request.client_ip, request.method, request.path,
                     status, (time.perf_counter() - start) * 1000)
