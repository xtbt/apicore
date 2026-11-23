"""Timezone tests: the API renders timestamps in APP_TIMEZONE (America/Tijuana)
while the database stores UTC.

Runs end to end against the real server (main.py) on a dedicated port, with a
throwaway user that is deleted afterwards. The server subprocess is always
terminated, so no process or port is left open.
"""
import re
import unittest
from datetime import datetime, timedelta
from functools import partial
from zoneinfo import ZoneInfo

from tests.integration import support
from tests.integration.support import db_connect

PORT = 65438 + support.port_offset()  # Dedicated port for tests, distinct from the default 8000
BASE_URL = f'http://localhost:{PORT}'
TIJUANA = ZoneInfo('America/Tijuana')

call = partial(support.call, BASE_URL)

server_process = None
server_log = []  # lines printed by the server subprocess (filled by a reader thread)
test_user_id = None
test_username = None
test_password = 'TzPass123'


def setUpModule():
    global server_process, server_log, test_user_id, test_username, test_password
    server_process = support.start_server(PORT, BASE_URL)
    server_log = support.start_log_reader(server_process)
    try:
        test_user_id, test_username, test_password, _token = support.register_test_user(
            BASE_URL, 'tztest', 'Tz')
    except Exception:
        tearDownModule()
        raise


def tearDownModule():
    global server_process
    if test_user_id is not None:
        status, body = call('POST', '/auth/login', {'Username': test_username, 'Password': test_password})
        if status == 200:
            call('DELETE', f'/users/{test_user_id}', token=body['data']['token'])
    support.stop_server(server_process)
    server_process = None


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
        found = support.wait_for_log(server_log, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} INFO 127\.0\.0\.1 GET /health 200 \d+ms')
        self.assertIsNotNone(found, 'no request log line found: ' + repr(server_log[-5:]))
        logged_hour = int(re.search(r'(\d{2}):\d{2}:\d{2}', found).group(1))
        expected_hour = datetime.now(TIJUANA).hour
        self.assertIn(logged_hour, (expected_hour, (expected_hour - 1) % 24))


if __name__ == '__main__':
    unittest.main()
