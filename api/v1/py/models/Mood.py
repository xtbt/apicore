import pymysql
from core import Database

def create_mood(data):
    mood_name = data.get('MoodName')
    mood_status = data.get('MoodStatus')
    if not mood_name:
        raise ValueError('MoodName is required')
    if mood_status not in ('Active', 'Inactive'):
        raise ValueError('MoodStatus must be "Active" or "Inactive"')
    dbconn = Database.Database().get_connection()
    cur = dbconn.cursor()
    cur.execute(
        "INSERT INTO moods (MoodId, MoodName, MoodStatus) VALUES (%s, %s, %s)",
        (None, mood_name, mood_status)
    )
    dbconn.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id


def get_moods():
    dbconn = Database.Database().get_connection()
    cur = dbconn.cursor()
    cur.execute("SELECT * FROM moods")
    results = cur.fetchall()
    cur.close()
    return results


def modify_mood(mood_id, data):
    mood_name = data.get('MoodName')
    mood_status = data.get('MoodStatus')
    if not mood_name:
        raise ValueError('MoodName is required')
    if mood_status not in ('Active', 'Inactive'):
        raise ValueError('MoodStatus must be "Active" or "Inactive"')
    dbconn = Database.Database().get_connection()
    cur = dbconn.cursor()
    cur.execute(
        "UPDATE moods SET MoodName = %s, MoodStatus = %s WHERE MoodId = %s",
        (mood_name, mood_status, mood_id)
    )
    dbconn.commit()
    cur.close()


def delete_mood(mood_id):
    dbconn = Database.Database().get_connection()
    cur = dbconn.cursor()
    cur.execute(
        "DELETE FROM moods WHERE MoodId = %s",
        (mood_id,)
    )
    dbconn.commit()
    cur.close()
