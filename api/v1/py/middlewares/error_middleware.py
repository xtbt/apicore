"""Translate exceptions into Response objects, the pipeline's response shape.

Layer: middlewares (cross-cutting). Sits inside cors_middleware, so every error
leaves the pipeline as a uniform JSON body that still carries the CORS headers.
"""
import logging

from core.exceptions import AppError, status_of
from core.http import Response
from middlewares.base import Middleware


class ErrorMiddleware(Middleware):
    """AppError keeps its status code, ValueError is a 400 and anything else a 500.

    The traceback is always logged and never returned to the client.
    """

    def handle(self, request, call_next):
        try:
            return call_next(request)
        except (AppError, ValueError) as error:
            return Response.error(status_of(error), str(error))
        except Exception as error:
            logging.exception('Unhandled error on %s %s', request.method, request.path)
            return Response.error(status_of(error), 'Internal server error')
