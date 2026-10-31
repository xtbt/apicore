from models.BaseModel import BaseModel

class Mood(BaseModel):
    TABLE_NAME = 'moods'
    ID_COLUMN = 'MoodId'
    ALLOWED_STATUSES = ('Active', 'Inactive')
    MAX_NAME_LENGTH = 16

    def __init__(self):
        super().__init__()

    def _validate(self, data):
        mood_name = data.get('MoodName')
        mood_status = data.get('MoodStatus')
        if not mood_name:
            raise ValueError('MoodName is required')
        if len(mood_name) > self.MAX_NAME_LENGTH:
            raise ValueError(f'MoodName must be {self.MAX_NAME_LENGTH} chars max')
        if mood_status not in self.ALLOWED_STATUSES:
            raise ValueError('MoodStatus must be "Active" or "Inactive"')

    def create_mood(self, data):
        self._validate(data)
        insert_data = {k: v for k, v in data.items() if k != self.ID_COLUMN}
        return self.create(self.TABLE_NAME, insert_data)

    def get_moods(self):
        return self.get_all(self.TABLE_NAME)

    def get_mood_by_id(self, mood_id):
        return self.get_by_id(self.TABLE_NAME, mood_id)

    def modify_mood(self, mood_id, data):
        self._validate(data)
        self.update(self.TABLE_NAME, mood_id, data)

    def delete_mood(self, mood_id):
        self.delete(self.TABLE_NAME, mood_id)
