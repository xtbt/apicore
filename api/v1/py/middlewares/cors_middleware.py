"""CORS headers for browser clients.

Layer: middlewares (cross-cutting). Outermost layer, so the headers are added to
every response, including the ones produced by error_middleware. It never
rejects a request: the browser is the one that enforces the policy.
"""
from core.settings import settings
from middlewares.base import Middleware

ALLOWED_METHODS = 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS'
ALLOWED_HEADERS = 'Authorization, Content-Type'
MAX_AGE_SECONDS = '600'


class CorsMiddleware(Middleware):
    """Adds Access-Control-* headers so a frontend on another origin can call the API."""

    def __init__(self, allow_origin=None):
        self.allow_origin = allow_origin or settings.CORS_ALLOW_ORIGIN

    def handle(self, request, call_next):
        response = call_next(request)
        response.headers['Access-Control-Allow-Origin'] = self.allow_origin
        response.headers['Access-Control-Allow-Methods'] = ALLOWED_METHODS
        response.headers['Access-Control-Allow-Headers'] = ALLOWED_HEADERS
        response.headers['Access-Control-Max-Age'] = MAX_AGE_SECONDS
        if self.allow_origin != '*':
            # The response depends on the caller's Origin, so caches must not share it
            response.headers['Vary'] = 'Origin'
        return response
