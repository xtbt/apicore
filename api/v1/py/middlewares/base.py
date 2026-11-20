"""Middleware contract and pipeline builder.

Layer: middlewares (cross-cutting). A middleware wraps the next handler, so the
pipeline is read outermost to innermost: error -> logging -> auth -> endpoint.
Every middleware and the endpoint share one signature:

    handler(request) -> (status, payload)

Keeping the response as a (status, payload) pair means no middleware needs to
know about sockets or HTTP: only main.py writes the response.
"""


class RequestContext:
    """Everything one request carries while it crosses the pipeline."""

    def __init__(self, method, path, query, headers, client_ip, read_body):
        self.method = method
        self.path = path
        self.query = query
        self.headers = headers
        self.client_ip = client_ip
        # callable() -> str: reads the body on demand, so a middleware can reject
        # a request (401, 413) before the body is read
        self.read_body = read_body
        self.token = None         # raw bearer token, set by auth_middleware
        self.user = None          # decoded token payload, set by auth_middleware
        self.extra_headers = {}   # response headers added by a middleware or endpoint


class Middleware:
    """Base contract: subclasses override handle() and call call_next(request)."""

    def handle(self, request, call_next):
        """Process the request and delegate to the next layer. Returns (status, payload)."""
        return call_next(request)


def build_pipeline(middlewares, endpoint):
    """Chain middlewares around endpoint; the first item of the list is the outermost layer."""
    def chain(index):
        if index == len(middlewares):
            return endpoint
        return lambda request: middlewares[index].handle(request, chain(index + 1))

    return chain(0)
