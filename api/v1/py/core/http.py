"""HTTP value objects shared by the whole pipeline.

Layer: core. Request and Response only carry data; neither touches the socket,
so middlewares and tests can build and inspect them freely. Only server.py
reads the socket and writes the response back to the client.
"""


class Request:
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


def route_method(method):
    """HEAD reuses the GET route: same handler and headers, body suppressed by server.py."""
    return 'GET' if method == 'HEAD' else method


class Response:
    """What an endpoint or middleware returns: status code, payload and headers."""

    def __init__(self, status=200, payload=None, headers=None):
        self.status = status
        self.payload = payload      # dict/list serialized as JSON, or None for no body
        self.headers = headers or {}

    @classmethod
    def error(cls, status, message):
        """Uniform error body: {'error': message}."""
        return cls(status, {'error': message})

    def __repr__(self):
        return f'Response({self.status}, {self.payload!r}, {self.headers!r})'
