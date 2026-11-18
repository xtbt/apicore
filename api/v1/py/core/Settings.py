"""Settings: custom .env reader exposed as a single `settings` object.

Layer: core (cross-cutting). Real environment variables override the .env file.
It must never import from controllers, models or routers.
"""
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class Settings:
    REQUIRED = ('DB_NAME', 'DB_USER', 'DB_PASSWORD', 'JWT_SECRET')  # no usable default

    def __init__(self, env_path=None):
        env_path = env_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        values = self._read_env_file(env_path)

        def get(key, default=None):
            """Real environment variable first, then the .env file, then the default."""
            return os.environ.get(key, values.get(key, default))

        self.APP_HOST = get('APP_HOST', 'localhost')
        self.APP_PORT = int(get('APP_PORT', 8000))
        self.APP_TIMEZONE = get('APP_TIMEZONE', 'America/Tijuana')
        try:
            ZoneInfo(self.APP_TIMEZONE)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f'APP_TIMEZONE is not a valid IANA timezone: {self.APP_TIMEZONE}')
        self.DB_HOST = get('DB_HOST', 'localhost')
        self.DB_PORT = int(get('DB_PORT', 3306))
        self.DB_NAME = get('DB_NAME')
        self.DB_USER = get('DB_USER')
        self.DB_PASSWORD = get('DB_PASSWORD')
        self.JWT_SECRET = get('JWT_SECRET')
        self.JWT_ALGORITHM = get('JWT_ALGORITHM', 'HS256')
        self.TOKEN_LIFETIME_MINUTES = int(get('TOKEN_LIFETIME_MINUTES', 60))
        self.TOKEN_MIN_REMAINING_MINUTES = int(get('TOKEN_MIN_REMAINING_MINUTES', 10))

    def validate(self):
        """Raise ValueError listing every required setting that is missing.

        Called at startup, so a misconfigured server fails immediately instead of
        on the first request.
        """
        missing = [name for name in self.REQUIRED if not getattr(self, name)]
        if missing:
            raise ValueError('Missing required setting(s): ' + ', '.join(missing))

    @staticmethod
    def _read_env_file(path):
        """Parse KEY=VALUE lines (ignores blank lines and # comments). Missing file -> {}."""
        values = {}
        if not os.path.isfile(path):
            return values
        with open(path, encoding='utf-8') as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
        return values


settings = Settings()
