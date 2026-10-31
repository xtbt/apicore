from core import Database

class BaseModel:
    ID_COLUMN = 'Id'

    def __init__(self):
        self.db_conn = Database.Database().get_connection()

    def create(self, table_name, data):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        values = tuple(data.values())
        cur = self.db_conn.cursor()
        cur.execute(
            f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
            values
        )
        self.db_conn.commit()
        new_id = cur.lastrowid
        cur.close()
        return new_id
    
    def get_all(self, table_name):
        cur = self.db_conn.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        results = cur.fetchall()
        cur.close()
        return results

    def get_by_id(self, table_name, id):
        cur = self.db_conn.cursor()
        cur.execute(f"SELECT * FROM {table_name} WHERE {self.ID_COLUMN} = %s", (id,))
        result = cur.fetchone()
        cur.close()
        return result

    def update(self, table_name, id, data):
        set_clause = ', '.join([f"{key} = %s" for key in data.keys()])
        values = tuple(data.values()) + (id,)
        cur = self.db_conn.cursor()
        cur.execute(f"UPDATE {table_name} SET {set_clause} WHERE {self.ID_COLUMN} = %s", values)
        self.db_conn.commit()
        cur.close()

    def delete(self, table_name, id):
        cur = self.db_conn.cursor()
        cur.execute(f"DELETE FROM {table_name} WHERE {self.ID_COLUMN} = %s", (id,))
        self.db_conn.commit()
        cur.close()