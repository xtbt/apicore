"""Unit tests for core/router.py: route matching, dispatch and request parsing.

No server and no database: a stub controller stands in for a real one.
"""
import unittest

from core.exceptions import UnauthorizedError
from core.router import MAX_PAGE_SIZE, Router, json_object, positive_int


class StubController:
    """Minimal controller: records that it was closed."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def ok_handler(controller, params, body):
    return 200, {'params': params, 'body': body}


def build_router(authenticator=None):
    router = Router(authenticator=authenticator)
    router.add_route('GET', '/items', StubController, ok_handler, public=True)
    router.add_route('GET', '/items/{id}', StubController, ok_handler)
    router.add_route('PUT', '/items/{id}', StubController, ok_handler)
    return router


class TestJsonObject(unittest.TestCase):
    def test_object(self):
        self.assertEqual(json_object('{"a": 1}'), {'a': 1})

    def test_empty_object(self):
        self.assertEqual(json_object('{}'), {})

    def test_non_object(self):
        for body in ('[]', '"text"', '3', 'null'):
            with self.assertRaises(ValueError):
                json_object(body)

    def test_invalid_json(self):
        with self.assertRaises(ValueError):
            json_object('{')


class TestPositiveInt(unittest.TestCase):
    def test_absent(self):
        self.assertEqual(positive_int({}, 'page'), 0)
        self.assertEqual(positive_int({'page': ''}, 'page'), 0)

    def test_valid(self):
        self.assertEqual(positive_int({'page': '3'}, 'page'), 3)

    def test_invalid(self):
        for raw in ('abc', '1.5', '0', '-1'):
            with self.assertRaises(ValueError) as context:
                positive_int({'page': raw}, 'page')
            self.assertEqual(str(context.exception), 'page must be a positive integer')


class TestRouteMatching(unittest.TestCase):
    def test_path_parameter(self):
        router = build_router(lambda token: {'sub': 1})
        status, payload = router.dispatch('GET', '/items/42', '', {'Authorization': 'Bearer t'})
        self.assertEqual((status, payload['params']), (200, {'id': '42'}))

    def test_unknown_path(self):
        self.assertEqual(build_router().dispatch('GET', '/nope', '', {}),
                         (404, {'error': 'Not found'}))

    def test_wrong_method(self):
        self.assertEqual(build_router().dispatch('POST', '/items', '', {}),
                         (405, {'error': 'Method not allowed'}))

    def test_trailing_slash_does_not_match(self):
        self.assertEqual(build_router().dispatch('GET', '/items/', '', {})[0], 404)

    def test_allowed_methods(self):
        router = build_router()
        self.assertEqual(sorted(router.allowed_methods('/items/1')), ['GET', 'PUT'])
        self.assertEqual(router.allowed_methods('/nope'), [])

    def test_controller_is_closed(self):
        """The controller is closed even when the handler succeeds."""
        router = Router()
        created = []

        class Tracking(StubController):
            def __init__(self):
                super().__init__()
                created.append(self)

        router.add_route('GET', '/x', Tracking, ok_handler, public=True)
        router.dispatch('GET', '/x', '', {})
        self.assertTrue(created[0].closed)


class TestAuthentication(unittest.TestCase):
    def test_missing_header(self):
        with self.assertRaises(UnauthorizedError):
            build_router(lambda token: {'sub': 1}).dispatch('GET', '/items/1', '', {})

    def test_malformed_header(self):
        for value in ('Token abc', 'Bearer', 'Bearer ', 'abc'):
            with self.assertRaises(UnauthorizedError):
                build_router(lambda token: {'sub': 1}).dispatch(
                    'GET', '/items/1', '', {'Authorization': value})

    def test_scheme_is_case_insensitive(self):
        """RFC 7235: the auth scheme is case-insensitive."""
        for scheme in ('Bearer', 'bearer', 'BEARER', 'BeArEr'):
            status, payload = build_router(lambda token: {'sub': 1}).dispatch(
                'GET', '/items/1', '', {'Authorization': f'{scheme} abc'})
            self.assertEqual(status, 200)

    def test_token_reaches_authenticator(self):
        seen = []
        build_router(lambda token: seen.append(token) or {'sub': 1}).dispatch(
            'GET', '/items/1', '', {'Authorization': 'Bearer my-token'})
        self.assertEqual(seen, ['my-token'])

    def test_public_route_ignores_invalid_token(self):
        """A public route still works when the token is invalid."""

        def reject(token):
            raise UnauthorizedError('Invalid token')

        self.assertEqual(build_router(reject).dispatch('GET', '/items', '', {
            'Authorization': 'Bearer garbage'})[0], 200)

    def test_public_route_uses_valid_token(self):
        """A public route exposes the payload when the token is valid."""
        router = Router(authenticator=lambda token: {'sub': 9, 'role': 'God'})
        router.add_route('GET', '/open', StubController,
                         lambda c, p, b: (200, {'user': c.auth_user}), public=True)
        status, payload = router.dispatch('GET', '/open', '', {'Authorization': 'Bearer t'})
        self.assertEqual(payload['user'], {'sub': 9, 'role': 'God'})


class TestPageSizeLimit(unittest.TestCase):
    def test_limit_is_positive(self):
        self.assertGreater(MAX_PAGE_SIZE, 0)


if __name__ == '__main__':
    unittest.main()
