"""Rate limiter: blocks a key (e.g. a username) after too many failed attempts.

Layer: core (cross-cutting). In-memory and per process: counters reset on restart.
"""
import threading
import time

from core.Exceptions import TooManyRequestsError

MAX_KEYS = 1024  # purge stale keys beyond this, so unknown usernames cannot grow memory


class RateLimiter:
    def __init__(self, max_failures=5, window_seconds=900):
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures = {}  # key -> list of failure timestamps
        self._lock = threading.Lock()

    def _recent(self, key):
        """Failures of `key` inside the window (caller must hold the lock)."""
        limit = time.time() - self.window
        recent = [t for t in self._failures.get(key, []) if t > limit]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def check(self, key):
        """Raise TooManyRequestsError (429) if `key` is blocked."""
        with self._lock:
            if len(self._recent(key)) >= self.max_failures:
                raise TooManyRequestsError('Too many failed attempts, try again later')

    def fail(self, key):
        with self._lock:
            self._recent(key)
            if len(self._failures) >= MAX_KEYS:
                limit = time.time() - self.window
                stale = [k for k, times in self._failures.items() if all(t <= limit for t in times)]
                for k in stale:
                    del self._failures[k]
            self._failures.setdefault(key, []).append(time.time())

    def reset(self, key):
        with self._lock:
            self._failures.pop(key, None)
