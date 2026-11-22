"""HTTP response value object shared by the whole pipeline.

Layer: core. A Response only carries data (status, JSON payload and extra
headers); it never touches the socket, so middlewares and tests can build and
inspect it freely. Only server.py serializes it and writes it to the client.
"""


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
