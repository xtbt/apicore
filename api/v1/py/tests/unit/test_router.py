"""Unit tests for core/router.py: route matching, dispatch and request parsing.

No server and no database: a stub controller stands in for a real one.
"""
import unittest

from core.router import MAX_PAGE_SIZE, Router, json_object, positive_int


class StubController:
    """Minimal controller: records that it was closed."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def ok_handler(controller, params, body):
    return 200, {'params': params, 'body': body}


def build_router():
    router = Router()
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
    def test_path_parameter_and_body(self):
        router = build_router()
        status, payload = router.dispatch(
            'GET', '/items/42', '', token='raw-token', user={'sub': 1})
        self.assertEqual((status, payload['params']), (200, {'id': '42'}))
        self.assertEqual(payload['body'], '')

    def test_unknown_path(self):
        self.assertEqual(build_router().dispatch('GET', '/nope', ''),
                         (404, {'error': 'Not found'}))

    def test_wrong_method(self):
        self.assertEqual(build_router().dispatch('POST', '/items', ''),
                         (405, {'error': 'Method not allowed'}))

    def test_trailing_slash_does_not_match(self):
        self.assertEqual(build_router().dispatch('GET', '/items/', '')[0], 404)

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
        router.dispatch('GET', '/x', '')
        self.assertTrue(created[0].closed)


class TestPageSizeLimit(unittest.TestCase):
    def test_limit_is_positive(self):
        self.assertGreater(MAX_PAGE_SIZE, 0)


class TestCreateResponse(unittest.TestCase):
    """POST returns 201 with a Location header pointing at the new record."""

    def test_create_returns_201_and_location(self):
        class CrudStub(StubController):
            NOT_FOUND, UNCHANGED, UPDATED = 'not_found', 'unchanged', 'updated'

            def create(self, data):
                return 7

        router = Router()
        router.add_crud_routes('/items', CrudStub, 'Item', public=True)
        response = router.dispatch('POST', '/items', '{"a": 1}')
        self.assertEqual((response.status, response.payload['ID']), (201, 7))
        self.assertEqual(response.headers['Location'], '/items/7')


if __name__ == '__main__':
    unittest.main()
