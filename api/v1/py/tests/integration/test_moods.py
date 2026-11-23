"""Unit tests for the 5 standard CRUD methods of the `moods` entity.

Runs end to end against the real server (main.py) and the real MySQL
database configured in .env. A dedicated test user is registered through
the public POST /users endpoint and used to log in, instead of using an
existing account, to avoid touching any real user's credentials.

The server subprocess is always started on setUpModule and terminated on
tearDownModule (even on failure), so no process or port is left open.
"""
import unittest
from functools import partial

from tests.integration import support

PORT = 65432  # Dedicated port for tests, distinct from the default 65000
BASE_URL = f'http://localhost:{PORT}'

call = partial(support.call, BASE_URL)

server_process = None
test_user_id = None
auth_token = None


def setUpModule():
    """Start main.py on a dedicated port and register+login a throwaway test user."""
    global server_process, test_user_id, auth_token

    server_process = support.start_server(PORT, BASE_URL)
    try:
        test_user_id, test_username, _password, auth_token = support.register_test_user(
            BASE_URL, 'moodtest', 'Moods')
    except Exception:
        # unittest does not call tearDownModule when setUpModule raises,
        # so the server subprocess must be stopped here to avoid a leak
        tearDownModule()
        raise


def tearDownModule():
    """Delete the test user (its tokens cascade with it) and stop the server subprocess."""
    global server_process
    if auth_token is not None and test_user_id is not None:
        call('DELETE', f'/users/{test_user_id}', token=auth_token)
    support.stop_server(server_process)
    server_process = None


class TestMoodsCRUD(unittest.TestCase):
    """Exercises the 5 standard endpoints of /moods, in sequence, as user jonny-equivalent."""

    def test_1_create(self):
        """POST /moods creates a record and returns its new id."""
        status, body = call('POST', '/moods', {'MoodName': 'UnitTest', 'MoodStatus': 'Active'}, auth_token)
        self.assertEqual(status, 201)
        self.assertIn('ID', body)
        TestMoodsCRUD.mood_id = body['ID']

    def test_2_get_all(self):
        """GET /moods returns the full list, including the record just created."""
        status, body = call('GET', '/moods', token=auth_token)
        self.assertEqual(status, 200)
        ids = [row['MoodId'] for row in body['data']]
        self.assertIn(self.mood_id, ids)

    def test_3_get_by_id(self):
        """GET /moods/{id} returns the created record; an unknown id returns 404."""
        status, body = call('GET', f'/moods/{self.mood_id}', token=auth_token)
        self.assertEqual(status, 200)
        self.assertEqual(body['data']['MoodName'], 'UnitTest')

        status, body = call('GET', '/moods/999999', token=auth_token)
        self.assertEqual(status, 404)

    def test_4_update(self):
        """PUT /moods/{id}: no-op when unchanged, real update when values differ."""
        status, body = call('PUT', f'/moods/{self.mood_id}',
                            {'MoodName': 'UnitTest', 'MoodStatus': 'Active'}, auth_token)
        self.assertEqual(status, 200)
        self.assertEqual(body['message'], 'No changes to apply')

        status, body = call('PUT', f'/moods/{self.mood_id}',
                            {'MoodName': 'UnitTest', 'MoodStatus': 'Inactive'}, auth_token)
        self.assertEqual(status, 200)
        self.assertEqual(body['message'], 'Mood updated')

        status, body = call('PUT', '/moods/999999', {'MoodName': 'X', 'MoodStatus': 'Active'}, auth_token)
        self.assertEqual(status, 404)

    def test_4b_patch(self):
        """PUT rejects a partial payload; PATCH accepts it and validates only what is sent."""
        status, body = call('PUT', f'/moods/{self.mood_id}', {'MoodStatus': 'Active'}, auth_token)
        self.assertEqual(status, 400)

        status, body = call('PATCH', f'/moods/{self.mood_id}', {'MoodStatus': 'Active'}, auth_token)
        self.assertEqual((status, body['message']), (200, 'Mood updated'))

        status, body = call('PATCH', f'/moods/{self.mood_id}', {'MoodStatus': 'Active'}, auth_token)
        self.assertEqual(body['message'], 'No changes to apply')

        status, body = call('PATCH', f'/moods/{self.mood_id}', {'MoodStatus': 'Bad'}, auth_token)
        self.assertEqual(status, 400)

        status, body = call('PATCH', '/moods/999999', {'MoodStatus': 'Active'}, auth_token)
        self.assertEqual(status, 404)

    def test_5_delete(self):
        """DELETE /moods/{id} removes the record; deleting it again returns 404."""
        status, body = call('DELETE', f'/moods/{self.mood_id}', token=auth_token)
        self.assertEqual(status, 200)

        status, body = call('DELETE', f'/moods/{self.mood_id}', token=auth_token)
        self.assertEqual(status, 404)

    def test_6_login_rate_limit(self):
        """After 5 failed logins for a username the 6th attempt is blocked with 429."""
        creds = {'Username': 'nouser_ratelimit', 'Password': 'bad'}
        for _ in range(5):
            self.assertEqual(call('POST', '/auth/login', creds)[0], 401)
        self.assertEqual(call('POST', '/auth/login', creds)[0], 429)


if __name__ == '__main__':
    unittest.main()
