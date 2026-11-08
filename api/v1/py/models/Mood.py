from models.BaseModel import BaseModel


class Mood(BaseModel):
    TABLE_NAME = 'moods'
    ID_COLUMN = 'MoodId'

    def __init__(self):
        super().__init__()

    def create_mood(self, data):
        insert_data = {k: v for k, v in data.items() if k != self.ID_COLUMN}
        return self.create(self.TABLE_NAME, insert_data)

    def get_moods(self):
        return self.get_all(self.TABLE_NAME)

    def get_mood_by_id(self, mood_id):
        return self.get_by_id(self.TABLE_NAME, mood_id)

    def modify_mood(self, mood_id, data):
        self.update(self.TABLE_NAME, mood_id, data)

    def delete_mood(self, mood_id):
        self.delete(self.TABLE_NAME, mood_id)
