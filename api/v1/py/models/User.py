"""User model: table definition and queries specific to `users`."""
from models.BaseModel import BaseModel


class User(BaseModel):
    TABLE_NAME = 'users'
    ID_COLUMN = 'UserId'
    COLUMNS = ('Username', 'Password', 'Name', 'PaternalSurname', 'MaternalSurname', 'UserStatus')
    HIDDEN_COLUMNS = ('Password',)

    def get_by_username(self, username):
        """Return the full row (including the password hash, for login) or None."""
        cur = self.db_conn.cursor(dictionary=True)
        try:
            cur.execute(f"SELECT * FROM {self.TABLE_NAME} WHERE Username = %s", (username,))
            return cur.fetchone()
        finally:
            cur.close()
