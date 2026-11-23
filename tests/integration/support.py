"""Shared harness for the integration tests.

Layer: tests (integration). Every suite starts a real server on its own port and
talks to it over HTTP; this module owns that plumbing so the suites do not keep
copies of it.

The same suites run against both implementations. Pick one with the
API_LANGUAGE environment variable (default: python):

    python3 -m unittest discover -s tests -t .                    # Python API
    API_LANGUAGE=php python3 -m unittest discover -s tests -t .   # PHP API
"""
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import mysql.connector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY_DIR = os.path.join(ROOT, 'api', 'v1', 'py')
PHP_DIR = os.path.join(ROOT, 'api', 'v1', 'php')

LANGUAGE = os.environ.get('API_LANGUAGE', 'python').strip().lower()
if LANGUAGE not in ('python', 'php'):
    raise RuntimeError(f'API_LANGUAGE must be "python" or "php", not {LANGUAGE!r}')

# Each implementation gets its own port range, so a leftover server from one
# language never blocks the other. The offset stays small: the highest base
# port is 65440 and a TCP port cannot exceed 65535.
PORT_OFFSET = 0 if LANGUAGE == 'python' else 50


def port_offset():
    """Offset added to every suite's base port for the selected language."""
    return PORT_OFFSET


def call(base_url, method, path, data=None, token=None):
    """Minimal HTTP client (stdlib only). Returns (status, json_body)."""
    body = json.dumps(data).encode() if data is not None else b''
    request = urllib.request.Request(f'{base_url}{path}', data=body, method=method)
    if token:
        request.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def wait_for_server(base_url, timeout=5):
    """Poll /health until the server answers or timeout is reached.

    Any HTTP answer counts as alive, including 503: the server is listening even
    when its database is down, which is exactly what the outage test needs.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'{base_url}/health', timeout=0.5):
                return True
        except urllib.error.HTTPError:
            return True
        except Exception:
            time.sleep(0.2)
    return False


def register_test_user(base_url, prefix, name='Tester'):
    """Create and log in a throwaway user. Returns (user_id, username, password, token).

    Username column is varchar(16), so the generated name stays within that limit.
    """
    username = f'{prefix}_' + secrets.token_hex(3)
    password = 'TestPass123'
    status, body = call(base_url, 'POST', '/users', {
        'Username': username, 'Password': password,
        'Name': name, 'PaternalSurname': 'Tester', 'UserStatus': 'Active'
    })
    if status != 201:
        raise RuntimeError(f'could not register the test user: {status} {body}')
    user_id = body['ID']
    status, body = call(base_url, 'POST', '/auth/login',
                        {'Username': username, 'Password': password})
    if status != 200:
        raise RuntimeError(f'could not log in with the test user: {status} {body}')
    return user_id, username, password, body['data']['token']


def server_command(port, language=None):
    """Command and working directory that start `language` on `port`."""
    language = (language or LANGUAGE).lower()
    if language == 'python':
        return [sys.executable, 'main.py'], PY_DIR
    if language == 'php':
        php = shutil.which('php')
        if php is None:
            raise RuntimeError('php is not installed or not in PATH')
        # The built-in server is single-threaded unless workers are requested
        return [php, '-S', f'127.0.0.1:{port}', 'index.php'], PHP_DIR
    raise RuntimeError(f'unknown language: {language!r}')


def start_server(port, base_url, extra_env=None, language=None):
    """Start the selected server on `port` and wait until /health answers."""
    command, directory = server_command(port, language)
    env = os.environ.copy()
    env['APP_PORT'] = str(port)
    env.update(extra_env or {})
    process = subprocess.Popen(
        command, cwd=directory, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        start_new_session=True,  # own process group: workers die with the parent
    )
    if not wait_for_server(base_url):
        output = stop_server(process)
        raise RuntimeError('Test server did not start on time: ' + output)
    return process


def stop_server(process):
    """Terminate the server and its workers, release the port and return its output."""
    if process is None:
        return ''
    # php -S forks workers that inherit the stdout pipe: signal the whole group,
    # otherwise reading the pipe blocks forever waiting for the children.
    try:
        group = os.getpgid(process.pid)
    except ProcessLookupError:
        group = None
    if group is not None:
        try:
            os.killpg(group, signal.SIGTERM)
        except ProcessLookupError:
            pass
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if group is not None:
            try:
                os.killpg(group, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.wait()
    output = ''
    if process.stdout is not None:
        output = process.stdout.read().decode(errors='replace')
        process.stdout.close()
    return output


def start_log_reader(process):
    """Drain the server stdout in a thread so its pipe never fills up."""
    lines = []

    def read():
        for line in process.stdout:
            lines.append(line.decode(errors='replace').rstrip())

    threading.Thread(target=read, daemon=True).start()
    return lines


def wait_for_log(lines, pattern, timeout=5):
    """Return the first collected log line matching `pattern`, or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for line in list(lines):
            if re.search(pattern, line):
                return line
        time.sleep(0.05)
    return None


def db_connect(language=None):
    """Direct connection to the database configured in .env (test housekeeping only).

    Environment variables win over the file, so CI can run without a .env.
    """
    directory = PHP_DIR if (language or LANGUAGE).lower() == 'php' else PY_DIR
    config = {}
    path = os.path.join(directory, '.env')
    if os.path.isfile(path):
        with open(path) as env_file:
            for line in env_file:
                match = re.match(r'([A-Z_]+)=(.*)', line.strip())
                if match:
                    config[match.group(1)] = match.group(2)
    for key in ('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'):
        if os.environ.get(key):
            config[key] = os.environ[key]
    return mysql.connector.connect(
        host=config.get('DB_HOST', 'localhost'), port=int(config.get('DB_PORT', 3306)),
        user=config['DB_USER'], password=config['DB_PASSWORD'], database=config['DB_NAME']
    )
