"""User model: table definition and queries specific to `users`."""
from models.base_model import BaseModel


class User(BaseModel):
    TABLE_NAME = 'users'
    ID_COLUMN = 'UserId'
    COLUMNS = ('Username', 'Password', 'Name', 'PaternalSurname', 'MaternalSurname', 'UserStatus', 'UserRole')
    HIDDEN_COLUMNS = ('Password',)

    def get_by_username(self, username):
        """Return the full row (including the password hash, for login) or None."""
        with self._cursor(dictionary=True) as cur:
            cur.execute(f"SELECT * FROM {self.TABLE_NAME} WHERE Username = %s", (username,))
            return cur.fetchone()

    def count_by_role(self, role):
        """Number of users holding `role` (used to protect the last God account)."""
        with self._cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE UserRole = %s", (role,))
            return cur.fetchone()[0]
