"""Translate exceptions into (status, payload) pairs, the pipeline's response shape.

Layer: middlewares (cross-cutting). Outermost layer: nothing above it can fail,
so every error leaves the pipeline as a uniform JSON body.
"""
import logging

from core.exceptions import AppError
from middlewares.base import Middleware


class ErrorMiddleware(Middleware):
    """AppError keeps its status code, ValueError is a 400 and anything else a 500.

    The traceback is always logged and never returned to the client.
    """

    def handle(self, request, call_next):
        try:
            return call_next(request)
        except AppError as error:
            return error.status_code, {'error': str(error)}
        except ValueError as error:
            return 400, {'error': str(error)}
        except Exception:
            logging.exception('Unhandled error on %s %s', request.method, request.path)
            return 500, {'error': 'Internal server error'}
