"""Mood controller: only the validation rules of the `moods` entity."""
from controllers.BaseController import BaseController
from models.Mood import Mood


class MoodController(BaseController):
    MODEL_CLASS = Mood

    def validate(self, data, partial=False):
        if not partial or 'MoodName' in data:
            mood_name = data.get('MoodName')
            if mood_name is not None and not isinstance(mood_name, str):
                raise ValueError('MoodName must be a string')
            if not mood_name:
                raise ValueError('MoodName is required')
            if len(mood_name) > 16:
                raise ValueError('MoodName must be 16 chars max')
        self._validate_enum(data, 'MoodStatus', ('Active', 'Inactive'), partial)
