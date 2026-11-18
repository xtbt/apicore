"""Protocol level tests: unknown route, wrong method, oversized body, keep-alive,
request log format and /healthcheck payload.

Runs end to end against the real server (main.py) on a dedicated port. The
server subprocess is always terminated, so no process or port is left open.
"""
import http.client
import json
import os
import re
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 65434  # Dedicated port for tests, distinct from the default 65000
BASE_URL = f'http://localhost:{PORT}'
MAX_BODY_BYTES = 1024 * 1024

server_process = None
server_log = []  # lines printed by the server subprocess (filled by a reader thread)


def call(method, path, data=None, token=None):
    """Minimal HTTP client (stdlib only). Returns (status, json_body)."""
    body = json.dumps(data).encode() if data is not None else b''
    request = urllib.request.Request(f'{BASE_URL}{path}', data=body, method=method)
    if token:
        request.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def wait_for_server(timeout=5):
    """Poll /healthcheck until the server answers or timeout is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'{BASE_URL}/healthcheck', timeout=0.5):
                return True
        except Exception:
            time.sleep(0.2)
    return False


def read_log():
    """Keep draining the server stdout so its pipe never fills up."""
    for line in server_process.stdout:
        server_log.append(line.decode(errors='replace').rstrip())


def wait_for_log(pattern, timeout=5):
    """Return the first collected log line matching `pattern`, or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for line in list(server_log):
            if re.search(pattern, line):
                return line
        time.sleep(0.05)
    return None


def setUpModule():
    global server_process
    env = os.environ.copy()
    env['APP_PORT'] = str(PORT)
    server_process = subprocess.Popen(
        [sys.executable, 'main.py'], cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    threading.Thread(target=read_log, daemon=True).start()
    if not wait_for_server():
        tearDownModule()
        raise RuntimeError('Test server did not start on time')


def tearDownModule():
    if server_process is not None:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait()


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
        """A Content-Length above the 1 MB cap is rejected with 413 before the body is read."""
        connection = http.client.HTTPConnection('localhost', PORT, timeout=10)
        try:
            # Headers only: the server must reject on Content-Length, without reading the body
            connection.putrequest('POST', '/auth/login')
            connection.putheader('Content-Type', 'application/json')
            connection.putheader('Content-Length', str(MAX_BODY_BYTES + 1))
            connection.endheaders()
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
            connection.request('GET', '/healthcheck')
            first = connection.getresponse()
            first.read()
            socket_before = connection.sock
            connection.request('GET', '/healthcheck')
            second = connection.getresponse()
            second.read()
            self.assertEqual((first.status, second.status), (200, 200))
            self.assertIs(connection.sock, socket_before)
        finally:
            connection.close()

    def test_5_request_log_format(self):
        """Each request logs "IP METHOD ROUTE STATUS DURATIONms"."""
        call('GET', '/healthcheck')
        line = wait_for_log(r'INFO 127\.0\.0\.1 GET /healthcheck 200 \d+ms')
        self.assertIsNotNone(line, 'log line not found: ' + repr(server_log[-5:]))

    def test_6_healthcheck_hides_body(self):
        """The health check no longer echoes the request body."""
        status, body = call('GET', '/healthcheck')
        self.assertEqual(status, 200)
        self.assertNotIn('debug', body)

    def test_7_healthcheck_is_a_route(self):
        """The health check is registered like any other route: wrong method gives 405."""
        status, body = call('POST', '/healthcheck', {})
        self.assertEqual((status, body['error']), (405, 'Method not allowed'))

    def test_8_head_returns_headers_only(self):
        """HEAD answers with the GET status and headers but no body."""
        connection = http.client.HTTPConnection('localhost', PORT, timeout=5)
        try:
            connection.request('HEAD', '/healthcheck')
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
        """A negative Content-Length is rejected with 400 instead of blocking the thread."""
        connection = http.client.HTTPConnection('localhost', PORT, timeout=5)
        try:
            connection.putrequest('POST', '/auth/login')
            connection.putheader('Content-Length', '-1')
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
            self.assertIn('Content-Length', json.loads(response.read())['error'])
        finally:
            connection.close()

        # The server is still responsive afterwards
        self.assertEqual(call('GET', '/healthcheck')[0], 200)

    def test_11_non_numeric_content_length(self):
        """A non-numeric Content-Length is a client error (400), not a 500."""
        connection = http.client.HTTPConnection('localhost', PORT, timeout=5)
        try:
            connection.putrequest('POST', '/auth/login')
            connection.putheader('Content-Length', 'abc')
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
        finally:
            connection.close()


if __name__ == '__main__':
    unittest.main()
