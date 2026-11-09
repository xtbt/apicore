"""Mood controller: only the validation rules of the `moods` entity."""
from controllers.BaseController import BaseController
from models.Mood import Mood


class MoodController(BaseController):
    MODEL_CLASS = Mood

    def validate(self, data):
        mood_name = data.get('MoodName')
        mood_status = data.get('MoodStatus')
        if not mood_name:
            raise ValueError('MoodName is required')
        if len(mood_name) > 16:
            raise ValueError('MoodName must be 16 chars max')
        if mood_status not in ('Active', 'Inactive'):
            raise ValueError('MoodStatus must be "Active" or "Inactive"')
