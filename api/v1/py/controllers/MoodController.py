from controllers.BaseController import BaseController
from models.BaseModel import BaseModel

class MoodController(BaseController):
    def __init__(self):
        super().__init__()
        print("MoodController initialized")

    def validate(self, data):
        mood_name = data.get('MoodName')
        mood_status = data.get('MoodStatus')
        if not mood_name:
            raise ValueError('MoodName is required')
        if len(mood_name) > 16:
            raise ValueError('MoodName must be 16 chars max')
        if mood_status not in ('Active', 'Inactive'):
            raise ValueError('MoodStatus must be "Active" or "Inactive"')
    
    def get_moods(self, table):
        # Placeholder for fetching moods from the database
        return BaseModel.get_all(BaseModel, table)
    
    def get_mood_by_id(self, table, mood_id):
        # Placeholder for fetching a mood by ID from the database
        return BaseModel.get_by_id(BaseModel, table, mood_id)