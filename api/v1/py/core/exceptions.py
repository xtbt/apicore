"""Application errors that carry their own HTTP status code.

Layer: core (cross-cutting). Raised by any layer, translated to JSON by
middlewares/error_middleware.py.
"""


class AppError(Exception):
    status_code = 500

    def __init__(self, message, status_code=None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class PayloadTooLargeError(AppError):
    status_code = 413


class TooManyRequestsError(AppError):
    status_code = 429


class ServiceUnavailableError(AppError):
    status_code = 503


def status_of(error):
    """HTTP status an exception maps to: AppError keeps its own, ValueError is a 400, the rest a 500."""
    if isinstance(error, AppError):
        return error.status_code
    if isinstance(error, ValueError):
        return 400
    return 500
