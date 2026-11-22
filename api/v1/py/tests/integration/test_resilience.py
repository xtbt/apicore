"""Resilience tests: database outage, body-size boundary and concurrent writes.

Layer: tests (integration). Each test starts its own server on a dedicated port
so a failure cannot leak into the CRUD suites.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT = 65439
BASE_URL = f'http://localhost:{PORT}'
MAX_BODY_BYTES = 1024 * 1024

server_process = None


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
    """Poll /health until the server answers or timeout is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'{BASE_URL}/health', timeout=0.5):
                return True
        except Exception:
            time.sleep(0.2)
    return False


def start_server(extra_env=None):
    """Start main.py on PORT and wait until /health answers."""
    global server_process
    env = os.environ.copy()
    env['APP_PORT'] = str(PORT)
    env.update(extra_env or {})
    server_process = subprocess.Popen(
        [sys.executable, 'main.py'], cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    if not wait_for_server():
        stop_server()
        raise RuntimeError('Test server did not start on time')


def stop_server():
    """Terminate the server subprocess and wait for the port to be released."""
    global server_process
    if server_process is not None:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait()
        if server_process.stdout is not None:
            server_process.stdout.close()
        server_process = None


class TestDatabaseOutage(unittest.TestCase):
    """An unreachable database must answer 503, not a generic 500."""

    @classmethod
    def setUpClass(cls):
        start_server({'DB_PORT': '1'})

    @classmethod
    def tearDownClass(cls):
        stop_server()

    def test_login_reports_service_unavailable(self):
        status, body = call('POST', '/auth/login',
                            {'Username': 'godtest', 'Password': 'godtest'})
        self.assertEqual(status, 503)
        self.assertEqual(body, {'error': 'Database unavailable'})


class TestBodySizeBoundary(unittest.TestCase):
    """The 1 MB cap rejects one byte more and accepts exactly the limit."""

    @classmethod
    def setUpClass(cls):
        start_server()
        status, body = call('POST', '/auth/login',
                            {'Username': 'godtest', 'Password': 'godtest'})
        if status != 200:
            stop_server()
            raise RuntimeError(f'could not log in: {status} {body}')
        cls.token = body['data']['token']

    @classmethod
    def tearDownClass(cls):
        stop_server()

    def send_raw(self, content_length, body=b''):
        """Send the declared body (if any) and return the status line."""
        connection = socket.create_connection(('127.0.0.1', PORT), timeout=20)
        try:
            connection.sendall(
                b'POST /moods HTTP/1.1\r\nHost: localhost\r\n'
                b'Content-Type: application/json\r\n'
                b'Authorization: Bearer ' + self.token.encode() + b'\r\n'
                b'Content-Length: ' + str(content_length).encode() + b'\r\n\r\n' + body)
            return connection.recv(200).split(b'\r\n', 1)[0]
        finally:
            connection.close()

    def test_one_byte_over_the_cap_is_rejected(self):
        self.assertIn(b'413', self.send_raw(MAX_BODY_BYTES + 1))

    def test_exactly_the_cap_is_not_rejected_by_size(self):
        status = self.send_raw(MAX_BODY_BYTES, b'x' * MAX_BODY_BYTES)
        self.assertNotIn(b'413', status)


class TestConcurrentWrites(unittest.TestCase):
    """Parallel PATCH requests on one record all succeed and leave it consistent."""

    @classmethod
    def setUpClass(cls):
        start_server()
        status, body = call('POST', '/auth/login',
                            {'Username': 'godtest', 'Password': 'godtest'})
        if status != 200:
            stop_server()
            raise RuntimeError(f'could not log in: {status} {body}')
        cls.token = body['data']['token']
        status, body = call('POST', '/moods',
                            {'MoodName': 'TMPConc', 'MoodStatus': 'Active'}, token=cls.token)
        if status != 200:
            stop_server()
            raise RuntimeError(f'could not create the mood: {status} {body}')
        cls.mood_id = body['ID']

    @classmethod
    def tearDownClass(cls):
        call('DELETE', f'/moods/{cls.mood_id}', token=cls.token)
        stop_server()

    def test_parallel_patches_all_succeed(self):
        statuses = []
        lock = threading.Lock()

        def patch(status_value):
            status, _body = call('PATCH', f'/moods/{self.mood_id}',
                                 {'MoodStatus': status_value}, token=self.token)
            with lock:
                statuses.append(status)

        threads = [threading.Thread(target=patch, args=('Inactive' if i % 2 else 'Active',))
                   for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(statuses, [200] * 8)
        status, body = call('GET', f'/moods/{self.mood_id}', token=self.token)
        self.assertEqual(status, 200)
        self.assertIn(body['data']['MoodStatus'], ('Active', 'Inactive'))


if __name__ == '__main__':
    unittest.main()
