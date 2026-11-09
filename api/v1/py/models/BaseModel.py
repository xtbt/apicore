"""Base model: generic CRUD data access shared by every entity.

Layer: models. Entity models only declare TABLE_NAME, ID_COLUMN and COLUMNS
(plus any query that is specific to that entity). It must never handle HTTP.
"""
from core.Database import Database


class BaseModel:
    TABLE_NAME = None   # Table of the entity (set by subclasses)
    ID_COLUMN = 'Id'    # Primary key column (override if different)
    COLUMNS = ()        # Writable columns (whitelist, excludes the primary key)

    # Results of update()
    NOT_FOUND = 'not_found'
    UNCHANGED = 'unchanged'
    UPDATED = 'updated'

    def __init__(self):
        # One connection per model instance (pymysql connections are not thread-safe)
        self.database = Database()
        self.db_conn = self.database.get_connection()

    def close(self):
        """Release the database connection."""
        self.database.close()

    def _filter(self, data):
        """Return only the writable columns of `data` (primary key removed).

        Column names are interpolated into SQL, so unknown keys are rejected
        (raises ValueError) to prevent SQL injection through the JSON body.
        """
        # The primary key is auto-increment: never written by the client, so drop it
        data = {k: v for k, v in data.items() if k != self.ID_COLUMN}
        unknown = [k for k in data if k not in self.COLUMNS]
        if unknown:
            raise ValueError('Unknown field(s): ' + ', '.join(unknown))
        if not data:
            raise ValueError('No data provided')
        return data

    def create(self, data):
        """Insert a record. Returns the new id."""
        data = self._filter(data)
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        cur = self.db_conn.cursor(dictionary=True)
        try:
            cur.execute(
                f"INSERT INTO {self.TABLE_NAME} ({columns}) VALUES ({placeholders})",
                tuple(data.values())
            )
            self.db_conn.commit()
            return cur.lastrowid
        finally:
            cur.close()

    def get_all(self):
        """Return all records of the table."""
        cur = self.db_conn.cursor(dictionary=True)
        try:
            cur.execute(f"SELECT * FROM {self.TABLE_NAME}")
            return cur.fetchall()
        finally:
            cur.close()

    def get_by_id(self, record_id):
        """Return one record, or None when it does not exist."""
        cur = self.db_conn.cursor(dictionary=True)
        try:
            cur.execute(
                f"SELECT * FROM {self.TABLE_NAME} WHERE {self.ID_COLUMN} = %s",
                (record_id,)
            )
            return cur.fetchone()
        finally:
            cur.close()

    def update(self, record_id, data):
        """Update a record by id.

        Returns 'not_found' if the id does not exist, 'unchanged' if the sent
        values equal the stored ones, or 'updated' after writing the changes.
        """
        data = self._filter(data)
        columns = list(data.keys())
        cur = self.db_conn.cursor(dictionary=True)
        try:
            # Read the current values (as a dict) of only the columns being modified
            cur.execute(
                f"SELECT {', '.join(columns)} FROM {self.TABLE_NAME} WHERE {self.ID_COLUMN} = %s",
                (record_id,)
            )
            current = cur.fetchone()
            if current is None:
                return self.NOT_FOUND
            if current == data:
                return self.UNCHANGED

            set_clause = ', '.join(f"{key} = %s" for key in columns)
            cur.execute(
                f"UPDATE {self.TABLE_NAME} SET {set_clause} WHERE {self.ID_COLUMN} = %s",
                tuple(data.values()) + (record_id,)
            )
            self.db_conn.commit()
            return self.UPDATED
        finally:
            cur.close()

    def delete(self, record_id):
        """Delete a record by id. Returns True if a row was deleted, False if the id does not exist."""
        cur = self.db_conn.cursor(dictionary=True)
        try:
            cur.execute(
                f"DELETE FROM {self.TABLE_NAME} WHERE {self.ID_COLUMN} = %s",
                (record_id,)
            )
            self.db_conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
