"""Shared harness for the integration tests.

Layer: tests (integration). Every suite starts the real server (main.py) on its
own port and talks to it over HTTP; this module owns that plumbing so the four
suites do not keep four copies of it.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import mysql.connector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    """Poll /health until the server answers or timeout is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'{base_url}/health', timeout=0.5):
                return True
        except Exception:
            time.sleep(0.2)
    return False


def start_server(port, base_url, extra_env=None):
    """Start main.py on `port` and wait until /health answers."""
    env = os.environ.copy()
    env['APP_PORT'] = str(port)
    env.update(extra_env or {})
    process = subprocess.Popen(
        [sys.executable, 'main.py'], cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    if not wait_for_server(base_url):
        output = stop_server(process)
        raise RuntimeError('Test server did not start on time: ' + output)
    return process


def stop_server(process):
    """Terminate the server subprocess, release its port and return its output."""
    if process is None:
        return ''
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
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
