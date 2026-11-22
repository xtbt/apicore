"""Unit tests for the HTTP adapter's response writer."""
import json
import unittest

from core.http import Response
from server import HTTPHandler


class FakeHandler:
    """Records what send_json_response would write, without a socket."""

    def __init__(self):
        self.status = None
        self.headers = []
        self.body = b''
        self.close_connection = False
        self.wfile = self

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.headers.append((name, value))

    def end_headers(self):
        pass

    def write(self, body):
        self.body = body

    def header(self, name):
        return [value for key, value in self.headers if key.lower() == name.lower()]


class TestSendJsonResponse(unittest.TestCase):

    def send(self, response, send_body=True):
        handler = FakeHandler()
        HTTPHandler.send_json_response(handler, response, send_body=send_body)
        return handler

    def test_body_headers_are_sent_once(self):
        handler = self.send(Response(200, {'status': 'ok'}))
        self.assertEqual(handler.header('Content-Type'), ['application/json'])
        self.assertEqual(handler.header('Content-Length'), ['16'])
        self.assertEqual(json.loads(handler.body), {'status': 'ok'})

    def test_response_cannot_duplicate_body_headers(self):
        response = Response(200, {'status': 'ok'},
                            {'Content-Type': 'text/plain', 'content-length': '999',
                             'X-Trace': 'abc'})
        handler = self.send(response)
        self.assertEqual(handler.header('Content-Type'), ['application/json'])
        self.assertEqual(handler.header('Content-Length'), ['16'])
        self.assertEqual(handler.header('X-Trace'), ['abc'])

    def test_204_has_no_body_headers(self):
        handler = self.send(Response(204, headers={'Allow': 'GET'}))
        self.assertEqual(handler.header('Allow'), ['GET'])
        self.assertEqual(handler.header('Content-Type'), [])
        self.assertEqual(handler.header('Content-Length'), [])
        self.assertEqual(handler.body, b'')

    def test_head_keeps_content_length_without_body(self):
        handler = self.send(Response(200, {'status': 'ok'}), send_body=False)
        self.assertEqual(handler.header('Content-Length'), ['16'])
        self.assertEqual(handler.body, b'')


if __name__ == '__main__':
    unittest.main()
