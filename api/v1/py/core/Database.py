import pymysql


class Database:
    def __init__(self, host='localhost', port=3306, user='root', password='root', database='apitest'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        if self.connection is None or not self.connection.open:
            self.connection = pymysql.connect(
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
        if self.connection is not None and self.connection.open:
            self.connection.close()
        self.connection = None