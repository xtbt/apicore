"""Unit tests for the Response value object."""
import unittest

from core.http import Response


class TestResponse(unittest.TestCase):

    def test_defaults(self):
        response = Response()
        self.assertEqual((response.status, response.payload, response.headers), (200, None, {}))

    def test_error_builds_uniform_body(self):
        response = Response.error(404, 'Not found')
        self.assertEqual((response.status, response.payload), (404, {'error': 'Not found'}))

    def test_headers_are_not_shared_between_instances(self):
        first, second = Response(), Response()
        first.headers['Allow'] = 'GET'
        self.assertEqual(second.headers, {})


if __name__ == '__main__':
    unittest.main()
