import threading

from mysql.connector import pooling

from core.exceptions import ServiceUnavailableError
from core.settings import settings

POOL_SIZE = 32  # connector maximum
ACQUIRE_TIMEOUT_SECONDS = 30

_pool = None
_pool_lock = threading.Lock()
# One slot per borrowed connection: ThreadingHTTPServer can start more threads
# than the pool size, so extra requests wait here instead of failing
_slots = threading.BoundedSemaphore(POOL_SIZE)


def _get_pool():
    """Create the shared connection pool on first use."""
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = pooling.MySQLConnectionPool(
                pool_name='apicore',
                pool_size=POOL_SIZE,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                # Store and compare timestamps in UTC: NOW() then equals UTC_TIMESTAMP()
                # whatever the MySQL server timezone is (named zones need the tz tables)
                time_zone='+00:00'
            )
    return _pool


class Database:
    def __init__(self):
        self.connection = None
        self._slot = False

    def connect(self):
        """Borrow a connection from the pool (reused while this instance lives)."""
        if self.connection is not None and self.connection.is_connected():
            return self.connection
        self.close()
        if not _slots.acquire(timeout=ACQUIRE_TIMEOUT_SECONDS):
            raise ServiceUnavailableError('Server busy, try again later')
        self._slot = True
        try:
            self.connection = _get_pool().get_connection()
        except Exception as error:
            self.close()
            # The database is unreachable: answer 503 instead of a generic 500
            raise ServiceUnavailableError('Database unavailable') from error
        return self.connection

    def close(self):
        """Return the connection to the pool and release its slot."""
        if self.connection is not None:
            self.connection.close()
        self.connection = None
        if self._slot:
            self._slot = False
            _slots.release()
