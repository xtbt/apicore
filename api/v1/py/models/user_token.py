"""UserToken model: table definition and queries specific to `users_tokens`.

A user may own many rows (one per device/session). Revoking a token means
deleting its row.
"""
from models.base_model import BaseModel


class UserToken(BaseModel):
    TABLE_NAME = 'users_tokens'
    ID_COLUMN = 'TokenId'
    COLUMNS = ('UserId', 'TokenHash', 'TokenExpiration', 'TokenCreatedAt')

    def _delete_where(self, column, value):
        """Delete rows matching `column` = `value`. Returns the number of deleted rows."""
        cur = self.db_conn.cursor()
        try:
            cur.execute(f"DELETE FROM {self.TABLE_NAME} WHERE {column} = %s", (value,))
            self.db_conn.commit()
            return cur.rowcount
        finally:
            cur.close()

    def get_by_hash(self, token_hash):
        """Return the token row for a SHA-256 hash, or None."""
        cur = self.db_conn.cursor(dictionary=True)
        try:
            cur.execute(f"SELECT * FROM {self.TABLE_NAME} WHERE TokenHash = %s", (token_hash,))
            return cur.fetchone()
        finally:
            cur.close()

    def get_user_state(self, token_hash):
        """Return (UserStatus, UserRole) of the owner of a valid token hash, or None.

        Returns None when the token does not exist or its `TokenExpiration` already
        passed, so a row edited to an earlier date stops authorizing requests.
        The role is read from the database on every request, so a role change
        applies immediately instead of waiting for the token to expire.
        """
        cur = self.db_conn.cursor()
        try:
            cur.execute(
                f"SELECT u.UserStatus, u.UserRole FROM {self.TABLE_NAME} t "
                "JOIN users u ON u.UserId = t.UserId "
                "WHERE t.TokenHash = %s AND t.TokenExpiration > UTC_TIMESTAMP()",
                (token_hash,)
            )
            return cur.fetchone()
        finally:
            cur.close()

    def delete_by_hash(self, token_hash):
        """Revoke one token."""
        return self._delete_where('TokenHash', token_hash)

    def delete_expired(self):
        """Housekeeping: delete tokens whose expiration date passed. Returns rows deleted.

        Persistent tokens hold a far-future date (year 9999), so they survive this.
        """
        cur = self.db_conn.cursor()
        try:
            cur.execute(f"DELETE FROM {self.TABLE_NAME} WHERE TokenExpiration < UTC_TIMESTAMP()")
            self.db_conn.commit()
            return cur.rowcount
        finally:
            cur.close()

    def delete_by_user(self, user_id):
        """Revoke every token of a user."""
        return self._delete_where('UserId', user_id)
