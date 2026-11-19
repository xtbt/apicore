"""Unit tests for cross-cutting HTTP middlewares."""
import unittest
from unittest.mock import patch

from middlewares.base import RequestContext
from middlewares.error_middleware import ErrorMiddleware
from middlewares.logging_middleware import LoggingMiddleware


def make_request():
    """Build a minimal request context suitable for middleware tests."""
    return RequestContext('POST', '/test', {}, {}, '127.0.0.1', lambda: '')


class TestLoggingMiddleware(unittest.TestCase):
    """Logging must match the status the outer error layer returns."""

    def test_value_error_logs_400_and_propagates(self):
        request = make_request()
        logger = LoggingMiddleware()
        with patch('middlewares.logging_middleware.logging.info') as log_info:
            with self.assertRaisesRegex(ValueError, 'invalid input'):
                logger.handle(request, lambda _request: (_ for _ in ()).throw(
                    ValueError('invalid input')))

        self.assertEqual(log_info.call_args.args[4], 400)

    def test_error_pipeline_returns_400_and_logs_400(self):
        request = make_request()
        pipeline = ErrorMiddleware().handle
        logging_middleware = LoggingMiddleware()

        def endpoint(_request):
            raise ValueError('invalid input')

        handler = lambda req: logging_middleware.handle(req, endpoint)
        with patch('middlewares.logging_middleware.logging.info') as log_info:
            status, payload = pipeline(request, handler)

        self.assertEqual((status, payload), (400, {'error': 'invalid input'}))
        self.assertEqual(log_info.call_args.args[4], 400)

    def test_unexpected_exception_logs_500_and_propagates(self):
        request = make_request()
        with patch('middlewares.logging_middleware.logging.info') as log_info:
            with self.assertRaisesRegex(RuntimeError, 'unexpected'):
                LoggingMiddleware().handle(
                    request, lambda _request: (_ for _ in ()).throw(RuntimeError('unexpected')))

        self.assertEqual(log_info.call_args.args[4], 500)


if __name__ == '__main__':
    unittest.main()
