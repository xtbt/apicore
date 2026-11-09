"""Application errors that carry their own HTTP status code.

Layer: core (cross-cutting). Raised by any layer, translated to JSON by main.py.
"""


class AppError(Exception):
    status_code = 500


class UnauthorizedError(AppError):
    status_code = 401
