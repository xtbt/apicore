"""Middleware contract and pipeline builder.

Layer: middlewares (cross-cutting). A middleware wraps the next handler, so the
pipeline is read outermost to innermost: cors -> error -> logging -> auth -> endpoint.
Every middleware and the endpoint share one signature:

    handler(request) -> Response

Request and Response (core/http.py) only carry data, so no middleware needs to
know about sockets: only server.py reads the request and writes the response.
"""


class Middleware:
    """Base contract: subclasses override handle() and call call_next(request)."""

    def handle(self, request, call_next):
        """Process the request and delegate to the next layer. Returns a Response."""
        return call_next(request)


def build_pipeline(middlewares, endpoint):
    """Chain middlewares around endpoint; the first item of the list is the outermost layer."""
    def chain(index):
        if index == len(middlewares):
            return endpoint
        return lambda request: middlewares[index].handle(request, chain(index + 1))

    return chain(0)
