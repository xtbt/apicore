"""Protocol level tests: unknown route, wrong method, oversized body, keep-alive,
request log format and /health payload.

Runs end to end against the real server (main.py) on a dedicated port. The
server subprocess is always terminated, so no process or port is left open.
"""
import http.client
import json
import unittest
from functools import partial

from tests.integration import support

PORT = 65434 + support.port_offset()  # Dedicated port for tests, distinct from the default 8000
BASE_URL = f'http://localhost:{PORT}'
MAX_BODY_BYTES = 1024 * 1024

call = partial(support.call, BASE_URL)

server_process = None
server_log = []  # lines printed by the server subprocess (filled by a reader thread)


def setUpModule():
    global server_process, server_log
    server_process = support.start_server(PORT, BASE_URL)
    server_log = support.start_log_reader(server_process)


def tearDownModule():
    global server_process
    support.stop_server(server_process)
    server_process = None


class TestHttpProtocol(unittest.TestCase):
    """Checks the transport level behaviour that the CRUD tests do not cover."""

    def test_1_unknown_route(self):
        """An unknown path returns 404 with a JSON error."""
        status, body = call('GET', '/nope')
        self.assertEqual((status, body['error']), (404, 'Not found'))

    def test_2_method_not_allowed(self):
        """An existing path with an unsupported method returns 405."""
        status, body = call('POST', '/moods/1', {})
        self.assertEqual((status, body['error']), (405, 'Method not allowed'))

    def test_3_payload_too_large(self):
        """A Content-Length above the 1 MB cap is rejected with 413."""
        connection = http.client.HTTPConnection('localhost', PORT, timeout=10)
        try:
            connection.putrequest('POST', '/auth/login')
            connection.putheader('Content-Type', 'application/json')
            connection.putheader('Content-Length', str(MAX_BODY_BYTES + 1))
            connection.endheaders()
            if support.LANGUAGE == 'php':
                # php -S buffers the body before running the script, so the
                # rejection can only happen once the body has been sent.
                connection.send(b'x' * (MAX_BODY_BYTES + 1))
            response = connection.getresponse()
            self.assertEqual(response.status, 413)
            self.assertIn('error', json.loads(response.read()))
        finally:
            connection.close()

    def test_3b_body_at_limit_is_read(self):
        """A body of exactly the cap is read normally (rejected as invalid JSON, not as too large)."""
        body = b'x' * MAX_BODY_BYTES
        connection = http.client.HTTPConnection('localhost', PORT, timeout=10)
        try:
            connection.request('POST', '/auth/login', body=body,
                               headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
        finally:
            connection.close()

    def test_4_keep_alive(self):
        """HTTP/1.1 keeps the TCP connection open for the next request."""
        connection = http.client.HTTPConnection('localhost', PORT, timeout=5)
        try:
            connection.request('GET', '/health')
            first = connection.getresponse()
            first.read()
            socket_before = connection.sock
            connection.request('GET', '/health')
            second = connection.getresponse()
            second.read()
            self.assertEqual((first.status, second.status), (200, 200))
            self.assertIs(connection.sock, socket_before)
        finally:
            connection.close()

    def test_5_request_log_format(self):
        """Each request logs "IP METHOD ROUTE STATUS DURATIONms"."""
        call('GET', '/health')
        line = support.wait_for_log(server_log, r'INFO 127\.0\.0\.1 GET /health 200 \d+ms')
        self.assertIsNotNone(line, 'log line not found: ' + repr(server_log[-5:]))

    def test_6_health_hides_body(self):
        """The health check no longer echoes the request body."""
        status, body = call('GET', '/health')
        self.assertEqual(status, 200)
        self.assertNotIn('debug', body)

    def test_7_health_is_a_route(self):
        """The health check is registered like any other route: wrong method gives 405."""
        status, body = call('POST', '/health', {})
        self.assertEqual((status, body['error']), (405, 'Method not allowed'))

    def test_8_head_returns_headers_only(self):
        """HEAD answers with the GET status and headers but no body."""
        connection = http.client.HTTPConnection('localhost', PORT, timeout=5)
        try:
            connection.request('HEAD', '/health')
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertGreater(int(response.getheader('Content-Length')), 0)
            self.assertEqual(response.read(), b'')
        finally:
            connection.close()

    def test_9_options_lists_allowed_methods(self):
        """OPTIONS returns 204 with an Allow header; an unknown path gives 404."""
        connection = http.client.HTTPConnection('localhost', PORT, timeout=5)
        try:
            connection.request('OPTIONS', '/moods/1')
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 204)
            allow = response.getheader('Allow')
            for method in ('GET', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'):
                self.assertIn(method, allow)
        finally:
            connection.close()

        status, body = call('OPTIONS', '/nope')
        self.assertEqual(status, 404)

    def test_10_negative_content_length(self):
        """A negative Content-Length is a client error instead of blocking the thread."""
        connection = http.client.HTTPConnection('localhost', PORT, timeout=5)
        try:
            connection.putrequest('POST', '/auth/login')
            connection.putheader('Content-Length', '-1')
            connection.endheaders()
            try:
                response = connection.getresponse()
            except http.client.RemoteDisconnected:
                # php -S rejects the malformed length itself and closes the
                # connection before the script runs: still a client error.
                self.assertEqual(support.LANGUAGE, 'php')
            else:
                self.assertEqual(response.status, 400)
                self.assertIn('Content-Length', json.loads(response.read())['error'])
        finally:
            connection.close()

        # The server is still responsive afterwards
        self.assertEqual(call('GET', '/health')[0], 200)

    def test_12_healthcheck_alias_removed(self):
        """Only /health exists: the old /healthcheck alias is gone."""
        status, body = call('GET', '/health')
        self.assertEqual((status, body['status']), (200, 'ok'))
        self.assertEqual(call('GET', '/healthcheck')[0], 404)
        self.assertEqual(call('POST', '/health', {})[0], 405)

    def test_11_non_numeric_content_length(self):
        """A non-numeric Content-Length is a client error, not a 500."""
        connection = http.client.HTTPConnection('localhost', PORT, timeout=5)
        try:
            connection.putrequest('POST', '/auth/login')
            connection.putheader('Content-Length', 'abc')
            connection.endheaders()
            try:
                response = connection.getresponse()
            except http.client.RemoteDisconnected:
                # php -S rejects the malformed length itself and closes the
                # connection before the script runs: still a client error.
                self.assertEqual(support.LANGUAGE, 'php')
            else:
                self.assertEqual(response.status, 400)
        finally:
            connection.close()

        # The server is still responsive afterwards
        self.assertEqual(call('GET', '/health')[0], 200)


if __name__ == '__main__':
    unittest.main()
