"""Settings: custom .env reader exposed as a single `settings` object.

Layer: core (cross-cutting). Real environment variables override the .env file.
It must never import from controllers, models or routers.
"""
import os


class Settings:
    def __init__(self, env_path=None):
        env_path = env_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        values = self._read_env_file(env_path)
        get = lambda key, default=None: os.environ.get(key, values.get(key, default))

        self.HOST = get('HOST', 'localhost')
        self.PORT = int(get('PORT', 8000))
        self.DB_HOST = get('DB_HOST', 'localhost')
        self.DB_PORT = int(get('DB_PORT', 3306))
        self.DB_NAME = get('DB_NAME')
        self.DB_USER = get('DB_USER')
        self.DB_PASSWORD = get('DB_PASSWORD')
        self.JWT_SECRET = get('JWT_SECRET')
        self.JWT_ALGORITHM = get('JWT_ALGORITHM', 'HS256')
        self.TOKEN_LIFETIME_MINUTES = int(get('TOKEN_LIFETIME_MINUTES', 60))
        self.TOKEN_MIN_REMAINING_MINUTES = int(get('TOKEN_MIN_REMAINING_MINUTES', 10))

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
