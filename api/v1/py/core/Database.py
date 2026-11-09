import mysql.connector
from core.Settings import settings


class Database:
    def __init__(self, host=None, port=None, user=None, password=None, database=None):
        # Every parameter falls back to the value configured in .env
        self.host = host or settings.DB_HOST
        self.port = port or settings.DB_PORT
        self.user = user or settings.DB_USER
        self.password = password or settings.DB_PASSWORD
        self.database = database or settings.DB_NAME
        self.connection = None

    def connect(self):
        if self.connection is None or not self.connection.is_connected():
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print("Database connection established")
        return self.connection

    def get_connection(self):
        return self.connect()

    def close(self):
        if self.connection is not None and self.connection.is_connected():
            self.connection.close()
        self.connection = None