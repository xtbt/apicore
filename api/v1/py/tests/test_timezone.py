"""Timezone tests: the API renders timestamps in APP_TIMEZONE (America/Tijuana)
while the database stores UTC.

Runs end to end against the real server (main.py) on a dedicated port, with a
throwaway user that is deleted afterwards. The server subprocess is always
terminated, so no process or port is left open.
"""
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import mysql.connector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 65438  # Dedicated port for tests, distinct from the default 65000
BASE_URL = f'http://localhost:{PORT}'
TIJUANA = ZoneInfo('America/Tijuana')

server_process = None
server_log = []  # lines printed by the server subprocess (filled by a reader thread)
test_user_id = None
test_username = None
test_password = 'TzPass123'


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
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'{BASE_URL}/health', timeout=0.5):
                return True
        except Exception:
            time.sleep(0.2)
    return False


def db_connect():
    """Direct connection to the database configured in .env (test assertions only)."""
    config = {}
    with open(os.path.join(ROOT, '.env')) as env_file:
        for line in env_file:
            match = re.match(r'([A-Z_]+)=(.*)', line.strip())
            if match:
                config[match.group(1)] = match.group(2)
    return mysql.connector.connect(
        host=config.get('DB_HOST', 'localhost'), port=int(config.get('DB_PORT', 3306)),
        user=config['DB_USER'], password=config['DB_PASSWORD'], database=config['DB_NAME']
    )


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
    global server_process, test_user_id, test_username
    env = os.environ.copy()
    env['APP_PORT'] = str(PORT)
    server_process = subprocess.Popen(
        [sys.executable, 'main.py'], cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    threading.Thread(target=read_log, daemon=True).start()
    try:
        if not wait_for_server():
            raise RuntimeError('Test server did not start on time')
        test_username = 'tztest_' + secrets.token_hex(3)
        status, body = call('POST', '/users', {
            'Username': test_username, 'Password': test_password,
            'Name': 'Tz', 'PaternalSurname': 'Tester', 'UserStatus': 'Active'
        })
        if status != 200:
            raise RuntimeError(f'could not register the test user: {status} {body}')
        test_user_id = body['ID']
    except Exception:
        tearDownModule()
        raise


def tearDownModule():
    if test_user_id is not None:
        status, body = call('POST', '/auth/login', {'Username': test_username, 'Password': test_password})
        if status == 200:
            call('DELETE', f'/users/{test_user_id}', token=body['data']['token'])
    if server_process is not None:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait()


class TestTimezone(unittest.TestCase):
    """Checks that responses use America/Tijuana and storage stays in UTC."""

    def test_1_expires_at_uses_tijuana_offset(self):
        """expires_at is ISO 8601 with the America/Tijuana offset, not UTC."""
        status, body = call('POST', '/auth/login', {'Username': test_username, 'Password': test_password})
        self.assertEqual(status, 200)
        expires_at = body['data']['expires_at']
        self.assertIsNotNone(expires_at)

        parsed = datetime.fromisoformat(expires_at)
        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(parsed.utcoffset(), parsed.astimezone(TIJUANA).utcoffset())
        self.assertIn(parsed.utcoffset(), (timedelta(hours=-8), timedelta(hours=-7)))
        self.assertNotEqual(parsed.utcoffset(), timedelta(0))

    def test_2_database_stores_utc(self):
        """TokenExpiration is written in UTC: it matches UTC_TIMESTAMP() + lifetime."""
        status, body = call('POST', '/auth/login', {'Username': test_username, 'Password': test_password})
        self.assertEqual(status, 200)

        connection = db_connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT t.TokenExpiration, UTC_TIMESTAMP(), "
                "TIMESTAMPDIFF(MINUTE, UTC_TIMESTAMP(), t.TokenExpiration) "
                "FROM users_tokens t JOIN users u ON u.UserId = t.UserId "
                "WHERE u.Username = %s ORDER BY t.TokenId DESC LIMIT 1",
                (test_username,)
            )
            expiration, utc_now, minutes = cursor.fetchone()
            cursor.close()
        finally:
            connection.close()

        # 60 minute lifetime, allowing a minute of clock drift
        self.assertIn(minutes, (59, 60, 61))
        self.assertGreater(expiration, utc_now)

    def test_2b_app_session_compares_in_utc(self):
        """The API session runs in UTC: a token expired 30 min ago in UTC is rejected.

        The machine clock is 8 hours behind UTC, so a session using local NOW()
        would still accept that row; only a UTC session rejects it.
        """
        status, body = call('POST', '/auth/login', {'Username': test_username, 'Password': test_password})
        self.assertEqual(status, 200)
        token = body['data']['token']
        self.assertEqual(call('GET', '/moods', token=token)[0], 200)

        connection = db_connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE users_tokens SET TokenExpiration = UTC_TIMESTAMP() - INTERVAL 30 MINUTE "
                "WHERE TokenHash = SHA2(%s, 256)", (token,)
            )
            self.assertEqual(cursor.rowcount, 1)
            connection.commit()
            cursor.close()
        finally:
            connection.close()

        self.assertEqual(call('GET', '/moods', token=token)[0], 401)

    def test_3_request_log_uses_tijuana_time(self):
        """The request log timestamp is rendered in America/Tijuana."""
        call('GET', '/health')
        found = wait_for_log(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} INFO 127\.0\.0\.1 GET /health 200 \d+ms')
        self.assertIsNotNone(found, 'no request log line found: ' + repr(server_log[-5:]))
        logged_hour = int(re.search(r'(\d{2}):\d{2}:\d{2}', found).group(1))
        expected_hour = datetime.now(TIJUANA).hour
        self.assertIn(logged_hour, (expected_hour, (expected_hour - 1) % 24))


if __name__ == '__main__':
    unittest.main()
