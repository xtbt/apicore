"""Resilience tests: database outage, body-size boundary and concurrent writes.

Layer: tests (integration). Each test starts its own server on a dedicated port
so a failure cannot leak into the CRUD suites.
"""
import socket
import threading
import unittest
from functools import partial

from tests.integration import support

PORT = 65439 + support.port_offset()
BASE_URL = f'http://localhost:{PORT}'
MAX_BODY_BYTES = 1024 * 1024

call = partial(support.call, BASE_URL)

server_process = None


def start_server(extra_env=None):
    """Start main.py on PORT and wait until /health answers."""
    global server_process
    server_process = support.start_server(PORT, BASE_URL, extra_env)


def stop_server():
    """Terminate the server subprocess and wait for the port to be released."""
    global server_process
    support.stop_server(server_process)
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

    def test_health_reports_service_unavailable(self):
        """The probe reports the database, not just the process: 503 with its own body."""
        status, body = call('GET', '/health')
        self.assertEqual(status, 503)
        self.assertEqual(body, {'status': 'error', 'message': 'Database unavailable'})


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
        # php -S buffers the body before running the script, so the rejection
        # can only happen once the body has been sent.
        body = b'x' * (MAX_BODY_BYTES + 1) if support.LANGUAGE == 'php' else b''
        self.assertIn(b'413', self.send_raw(MAX_BODY_BYTES + 1, body))

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
        if status != 201:
            stop_server()
            raise RuntimeError(f'could not create the mood: {status} {body}')
        cls.mood_id = body['ID']

    @classmethod
    def tearDownClass(cls):
        call('DELETE', f'/moods/{cls.mood_id}', token=cls.token)
        stop_server()

    def test_parallel_patches_all_succeed(self):
        results = []
        lock = threading.Lock()

        def patch(status_value):
            try:
                status, _body = call('PATCH', f'/moods/{self.mood_id}',
                                     {'MoodStatus': status_value}, token=self.token)
            except Exception as error:  # recorded, so a transport failure is visible
                status = repr(error)
            with lock:
                results.append(status)

        threads = [threading.Thread(target=patch, args=('Inactive' if i % 2 else 'Active',))
                   for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(results, [200] * 8)
        status, body = call('GET', f'/moods/{self.mood_id}', token=self.token)
        self.assertEqual(status, 200)
        self.assertIn(body['data']['MoodStatus'], ('Active', 'Inactive'))


if __name__ == '__main__':
    unittest.main()
