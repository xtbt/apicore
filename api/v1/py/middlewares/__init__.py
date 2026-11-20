"""Middleware pipeline: error handling, request logging and authentication.

Layer: middlewares (cross-cutting). main.py builds the pipeline once and runs it
on every request; the order below is the only place that order is defined.
"""
from middlewares.auth_middleware import AuthMiddleware
from middlewares.base import RequestContext, build_pipeline
from middlewares.error_middleware import ErrorMiddleware
from middlewares.logging_middleware import LoggingMiddleware


def default_pipeline(router, endpoint, authenticator):
    """Build the standard pipeline: error -> logging -> auth -> endpoint."""
    return build_pipeline(
        [ErrorMiddleware(), LoggingMiddleware(), AuthMiddleware(router, authenticator)],
        endpoint,
    )
