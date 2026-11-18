"""End to end tests for the `users` entity flows: registration rules, PATCH/PUT,
role permissions, pagination, logout and malformed bodies.

Mirrors tests/test_moods.py: real server (main.py) and real MySQL database,
with a dedicated throwaway user; the server subprocess is always terminated.
"""
import json
import os
import re
import secrets
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request

import mysql.connector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 65433  # Dedicated port for tests, distinct from the default 65000
BASE_URL = f'http://localhost:{PORT}'

server_process = None
test_user_id = None
auth_token = None
test_username = None
test_password = None
second_user_id = None
second_username = None


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


def db_connect():
    """Direct connection to the database configured in .env (test housekeeping only)."""
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


def setUpModule():
    """Start main.py on a dedicated port and register+login a throwaway test user."""
    global server_process, test_user_id, auth_token, test_username, test_password

    env = os.environ.copy()
    env['APP_PORT'] = str(PORT)
    server_process = subprocess.Popen(
        [sys.executable, 'main.py'], cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    try:
        if not wait_for_server():
            raise RuntimeError('Test server did not start on time: ' + server_process.stdout.read().decode())

        # Dedicated test user: does not reuse or depend on any real account
        # Username column is varchar(16): keep the generated name within that limit
        test_username = 'usertest_' + secrets.token_hex(3)
        test_password = 'TestPass123'
        status, body = call('POST', '/users', {
            'Username': test_username, 'Password': test_password,
            'Name': 'Users', 'PaternalSurname': 'Tester', 'UserStatus': 'Active'
        })
        if status != 200:
            raise RuntimeError(f'could not register the test user: {status} {body}')
        test_user_id = body['ID']

        status, body = call('POST', '/auth/login', {'Username': test_username, 'Password': test_password})
        if status != 200:
            raise RuntimeError(f'could not log in with the test user: {status} {body}')
        auth_token = body['data']['token']
    except Exception:
        # unittest does not call tearDownModule when setUpModule raises,
        # so the server subprocess must be stopped here to avoid a leak
        tearDownModule()
        raise


def tearDownModule():
    """Delete the test user (re-login if the token was revoked) and stop the server subprocess."""
    if test_user_id is not None and test_username is not None:
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


class TestUsersFlows(unittest.TestCase):
    """Exercises registration, partial/full updates, permissions and logout, in sequence."""

    def test_1_registration_rules(self):
        """Public registration: a duplicate username and a self-assigned role are rejected."""
        status, body = call('POST', '/users', {
            'Username': test_username, 'Password': 'x', 'Name': 'Dup',
            'PaternalSurname': 'Dup', 'UserStatus': 'Active'
        })
        self.assertEqual(status, 400)

        status, body = call('POST', '/users', {
            'Username': 'attacker_' + secrets.token_hex(3), 'Password': 'x', 'Name': 'E',
            'PaternalSurname': 'E', 'UserStatus': 'Active', 'UserRole': 'God'
        })
        self.assertEqual(status, 403)

    def test_1b_public_route_token_handling(self):
        """POST /users is public: a valid token is honored, an invalid one is ignored."""
        # A plain user's token does not grant role assignment
        status, body = call('POST', '/users', {
            'Username': 'role_' + secrets.token_hex(3), 'Password': 'x', 'Name': 'R',
            'PaternalSurname': 'R', 'UserStatus': 'Active', 'UserRole': 'Admin'
        }, auth_token)
        self.assertEqual(status, 403)

        # A malformed token on a public route is ignored: registration still works
        username = 'notok_' + secrets.token_hex(3)
        status, body = call('POST', '/users', {
            'Username': username, 'Password': 'x', 'Name': 'N',
            'PaternalSurname': 'N', 'UserStatus': 'Active'
        }, 'garbage-token')
        self.assertEqual(status, 200)

        # Cleanup: the new account deletes itself (a plain User cannot delete others)
        token = call('POST', '/auth/login', {'Username': username, 'Password': 'x'})[1]['data']['token']
        self.assertEqual(call('DELETE', f"/users/{body['ID']}", token=token)[0], 200)

    def test_2_patch_partial_update(self):
        """PATCH changes only the sent fields, including the password."""
        global test_password
        status, body = call('PATCH', f'/users/{test_user_id}', {'Name': 'Patched'}, auth_token)
        self.assertEqual((status, body['message']), (200, 'User updated'))

        status, body = call('GET', f'/users/{test_user_id}', token=auth_token)
        self.assertEqual(body['data']['Name'], 'Patched')

        status, body = call('PATCH', f'/users/{test_user_id}', {'Password': 'NewPass456'}, auth_token)
        self.assertEqual(status, 200)
        test_password = 'NewPass456'

        status, body = call('POST', '/auth/login', {'Username': test_username, 'Password': test_password})
        self.assertEqual(status, 200)

    def test_3_role_change_forbidden(self):
        """A plain user cannot elevate itself: UserRole is Admin/God only."""
        status, body = call('PATCH', f'/users/{test_user_id}', {'UserRole': 'God'}, auth_token)
        self.assertEqual(status, 403)

    def test_4_put_full_payload(self):
        """PUT requires the full payload and keeps the Username uniqueness handling."""
        full = {'Username': test_username, 'Name': 'Full', 'PaternalSurname': 'Update',
                'UserStatus': 'Active'}
        status, body = call('PUT', f'/users/{test_user_id}', full, auth_token)
        self.assertEqual((status, body['message']), (200, 'User updated'))

        status, body = call('PUT', f'/users/{test_user_id}', {'Name': 'Partial'}, auth_token)
        self.assertEqual(status, 400)

    def test_5_password_hidden(self):
        """GET never returns the password hash."""
        status, body = call('GET', f'/users/{test_user_id}', token=auth_token)
        self.assertEqual(status, 200)
        self.assertNotIn('Password', body['data'])

    def test_6_pagination(self):
        """GET list supports page/size; invalid values return 400; /users is Admin/God only."""
        status, body = call('GET', '/users?page=1&size=1', token=auth_token)
        self.assertEqual(status, 403)

        status, body = call('GET', '/moods?page=1&size=1', token=auth_token)
        self.assertEqual((status, len(body['data'])), (200, 1))

        status, body = call('GET', '/moods?page=0&size=1', token=auth_token)
        self.assertEqual(status, 400)

        status, body = call('GET', '/moods?page=bad&size=1', token=auth_token)
        self.assertEqual((status, body['error']), (400, 'page must be a positive integer'))

        status, body = call('GET', '/moods?page=1&size=abc', token=auth_token)
        self.assertEqual((status, body['error']), (400, 'size must be a positive integer'))

        status, body = call('GET', '/moods?page=1', token=auth_token)
        self.assertEqual(status, 200)

        status, body = call('GET', '/moods?page=1&size=101', token=auth_token)
        self.assertEqual(status, 400)

        status, body = call('GET', '/moods?page=1&size=100', token=auth_token)
        self.assertEqual(status, 200)

    def test_6b_patch_duplicate_username(self):
        """PATCH to a username already taken by another user returns 400."""
        global second_user_id, second_username
        second_username = 'other_' + secrets.token_hex(3)
        status, body = call('POST', '/users', {
            'Username': second_username, 'Password': 'OtherPass123', 'Name': 'Other',
            'PaternalSurname': 'Tester', 'UserStatus': 'Active'
        })
        self.assertEqual(status, 200)
        second_user_id = body['ID']

        status, body = call('PATCH', f'/users/{test_user_id}', {'Username': second_username}, auth_token)
        self.assertEqual(status, 400)
        self.assertIn('already exists', body['error'])

    def test_6c_delete_revokes_tokens(self):
        """Deleting a user removes it and revokes every token it owned."""
        first = call('POST', '/auth/login', {'Username': second_username, 'Password': 'OtherPass123'})
        second = call('POST', '/auth/login', {'Username': second_username, 'Password': 'OtherPass123'})
        self.assertEqual((first[0], second[0]), (200, 200))

        status, body = call('DELETE', f'/users/{second_user_id}', token=first[1]['data']['token'])
        self.assertEqual((status, body['message']), (200, 'User deleted'))

        for token in (first[1]['data']['token'], second[1]['data']['token']):
            self.assertEqual(call('GET', '/moods', token=token)[0], 401)
        # The account is gone: it can no longer log in
        self.assertEqual(call('POST', '/auth/login', {
            'Username': second_username, 'Password': 'OtherPass123'})[0], 401)

    def test_6d_expired_tokens_purged_on_login(self):
        """A login deletes the tokens of that table whose expiration already passed."""
        marker = secrets.token_hex(32)  # 64 chars, same shape as a real SHA-256 hash
        connection = db_connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO users_tokens (UserId, TokenHash, TokenExpiration, TokenCreatedAt) "
                "VALUES (%s, %s, NOW() - INTERVAL 1 DAY, NOW() - INTERVAL 2 DAY)",
                (test_user_id, marker)
            )
            connection.commit()
            cursor.close()
        finally:
            connection.close()

        status, body = call('POST', '/auth/login', {'Username': test_username, 'Password': test_password})
        self.assertEqual(status, 200)

        connection = db_connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM users_tokens WHERE TokenHash = %s", (marker,))
            remaining = cursor.fetchone()[0]
            cursor.close()
        finally:
            connection.close()
        self.assertEqual(remaining, 0)

    def test_6e_expired_row_stops_authorizing(self):
        """A token whose TokenExpiration was moved to the past is rejected with 401."""
        status, body = call('POST', '/auth/login', {'Username': test_username, 'Password': test_password})
        self.assertEqual(status, 200)
        token = body['data']['token']
        self.assertEqual(call('GET', '/moods', token=token)[0], 200)

        connection = db_connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE users_tokens SET TokenExpiration = UTC_TIMESTAMP() - INTERVAL 1 DAY "
                "WHERE TokenHash = SHA2(%s, 256)", (token,)
            )
            self.assertEqual(cursor.rowcount, 1)
            connection.commit()
            cursor.close()
        finally:
            connection.close()

        self.assertEqual(call('GET', '/moods', token=token)[0], 401)

    def test_6f_cannot_touch_another_account(self):
        """A plain User cannot modify, re-password or delete another account."""
        victim_username = 'victim_' + secrets.token_hex(3)
        status, body = call('POST', '/users', {
            'Username': victim_username, 'Password': 'Victim123', 'Name': 'Victim',
            'PaternalSurname': 'Tester', 'UserStatus': 'Active'
        })
        self.assertEqual(status, 200)
        victim_id = body['ID']

        self.assertEqual(call('PATCH', f'/users/{victim_id}', {'Name': 'Hacked'}, auth_token)[0], 403)
        self.assertEqual(call('GET', f'/users/{victim_id}', token=auth_token)[0], 403)
        self.assertEqual(call('PATCH', f'/users/{victim_id}', {'Password': 'Hijacked123'}, auth_token)[0], 403)
        self.assertEqual(call('PATCH', f'/users/{victim_id}', {'UserStatus': 'Inactive'}, auth_token)[0], 403)
        self.assertEqual(call('PUT', f'/users/{victim_id}', {
            'Username': victim_username, 'Name': 'Hacked', 'PaternalSurname': 'Tester',
            'UserStatus': 'Active'}, auth_token)[0], 403)
        self.assertEqual(call('DELETE', f'/users/{victim_id}', token=auth_token)[0], 403)

        # Nothing changed: the victim still logs in with its original password
        status, body = call('POST', '/auth/login', {'Username': victim_username, 'Password': 'Victim123'})
        self.assertEqual(status, 200)
        status, body = call('GET', f'/users/{victim_id}', token=body['data']['token'])
        self.assertEqual((status, body['data']['Name']), (200, 'Victim'))

        # Cleanup: the victim deletes its own account
        token = call('POST', '/auth/login', {'Username': victim_username, 'Password': 'Victim123'})[1]['data']['token']
        self.assertEqual(call('DELETE', f'/users/{victim_id}', token=token)[0], 200)

    def test_6g_role_change_applies_to_existing_token(self):
        """The role is read from the database: an old token loses/gains privileges at once."""
        # Promote the test user directly in the database (no God account needed)
        connection = db_connect()
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET UserRole = 'Admin' WHERE UserId = %s", (test_user_id,))
            connection.commit()
            cursor.close()
        finally:
            connection.close()

        # The token issued while the user was a plain User now acts as Admin
        status, body = call('POST', '/users', {
            'Username': 'promo_' + secrets.token_hex(3), 'Password': 'x', 'Name': 'P',
            'PaternalSurname': 'P', 'UserStatus': 'Active', 'UserRole': 'Admin'
        }, auth_token)
        self.assertEqual(status, 200)
        call('DELETE', f"/users/{body['ID']}", token=auth_token)

        # Demote again: the same token must lose the privilege immediately
        connection = db_connect()
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET UserRole = 'User' WHERE UserId = %s", (test_user_id,))
            connection.commit()
            cursor.close()
        finally:
            connection.close()

        status, body = call('POST', '/users', {
            'Username': 'promo_' + secrets.token_hex(3), 'Password': 'x', 'Name': 'P',
            'PaternalSurname': 'P', 'UserStatus': 'Active', 'UserRole': 'Admin'
        }, auth_token)
        self.assertEqual(status, 403)

    def test_6h_last_god_cannot_lose_role(self):
        """The only God account cannot be demoted, so the system always keeps one."""
        connection = db_connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT UserId, Username FROM users WHERE UserRole = 'God'")
            gods = cursor.fetchall()
            cursor.close()
        finally:
            connection.close()
        if len(gods) != 1:
            self.skipTest(f'needs exactly one God account, found {len(gods)}')

        god_id, god_username = gods[0]
        status, body = call('POST', '/auth/login', {'Username': god_username, 'Password': god_username})
        if status != 200:
            self.skipTest('cannot log in as the God account')
        god_token = body['data']['token']

        status, body = call('PATCH', f'/users/{god_id}', {'UserRole': 'User'}, god_token)
        self.assertEqual(status, 403)
        status, body = call('PUT', f'/users/{god_id}', {
            'Username': god_username, 'Name': 'God', 'PaternalSurname': 'Test',
            'UserStatus': 'Active', 'UserRole': 'User'}, god_token)
        self.assertEqual(status, 403)
        status, body = call('DELETE', f'/users/{god_id}', token=god_token)
        self.assertEqual(status, 403)

    def test_7_logout_revokes_token(self):
        """POST /auth/logout revokes the token; reusing it returns 401."""
        status, body = call('POST', '/auth/logout', token=auth_token)
        self.assertEqual(status, 200)

        status, body = call('GET', '/moods', token=auth_token)
        self.assertEqual(status, 401)

    def test_8_non_object_body(self):
        """A JSON body that is not an object returns 400, not 500."""
        status, body = call('POST', '/auth/login', ['not', 'an', 'object'])
        self.assertEqual(status, 400)


if __name__ == '__main__':
    unittest.main()
