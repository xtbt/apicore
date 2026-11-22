"""Unit tests for cross-cutting HTTP middlewares."""
import unittest
from unittest.mock import patch

from core.exceptions import UnauthorizedError
from core.http import Response
from core.router import Router
from middlewares.auth_middleware import AuthMiddleware
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
            response = pipeline(request, handler)

        self.assertEqual((response.status, response.payload), (400, {'error': 'invalid input'}))
        self.assertEqual(log_info.call_args.args[4], 400)

    def test_unexpected_exception_logs_500_and_propagates(self):
        request = make_request()
        with patch('middlewares.logging_middleware.logging.info') as log_info:
            with self.assertRaisesRegex(RuntimeError, 'unexpected'):
                LoggingMiddleware().handle(
                    request, lambda _request: (_ for _ in ()).throw(RuntimeError('unexpected')))

        self.assertEqual(log_info.call_args.args[4], 500)


class TestAuthMiddleware(unittest.TestCase):
    """AuthMiddleware owns the Authorization header parsing and the public/protected policy."""

    @staticmethod
    def build(authenticator=lambda token: {'sub': 1, 'role': 'User'}):
        router = Router()
        router.add_route('GET', '/private', None, None)
        router.add_route('GET', '/open', None, None, public=True)
        return AuthMiddleware(router, authenticator)

    @staticmethod
    def send(middleware, method, path, headers):
        request = RequestContext(method, path, {}, headers, '127.0.0.1', lambda: '')
        middleware.handle(request, lambda req: Response(200))
        return request

    def test_protected_without_header_is_401(self):
        with self.assertRaises(UnauthorizedError):
            self.send(self.build(), 'GET', '/private', {})

    def test_protected_with_malformed_header_is_401(self):
        for header in ('Basic abc', 'Bearer', 'abc'):
            with self.assertRaises(UnauthorizedError):
                self.send(self.build(), 'GET', '/private', {'Authorization': header})

    def test_protected_valid_token_sets_token_and_user(self):
        request = self.send(self.build(), 'GET', '/private', {'Authorization': 'bearer tok'})
        self.assertEqual((request.token, request.user['sub']), ('tok', 1))

    def test_authenticator_rejection_propagates(self):
        def reject(token):
            raise UnauthorizedError('Token revoked or unknown')

        with self.assertRaises(UnauthorizedError):
            self.send(self.build(reject), 'GET', '/private', {'Authorization': 'Bearer tok'})

    def test_head_uses_the_get_route_policy(self):
        with self.assertRaises(UnauthorizedError):
            self.send(self.build(), 'HEAD', '/private', {})

    def test_public_without_token_passes_anonymous(self):
        request = self.send(self.build(), 'GET', '/open', {})
        self.assertEqual((request.token, request.user), (None, None))

    def test_public_with_valid_token_sets_user(self):
        request = self.send(self.build(), 'GET', '/open', {'Authorization': 'Bearer tok'})
        self.assertEqual(request.user['role'], 'User')

    def test_public_with_invalid_token_is_ignored(self):
        def reject(token):
            raise UnauthorizedError('bad')

        request = self.send(self.build(reject), 'GET', '/open', {'Authorization': 'Bearer tok'})
        self.assertEqual((request.token, request.user), (None, None))

    def test_unknown_route_passes_through_for_router_to_answer(self):
        request = self.send(self.build(), 'GET', '/nope', {})
        self.assertIsNone(request.user)


if __name__ == '__main__':
    unittest.main()
