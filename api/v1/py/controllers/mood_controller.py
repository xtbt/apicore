"""Mood controller: only the validation rules of the `moods` entity."""
from controllers.base_controller import BaseController
from models.mood import Mood
from schemas import mood_schema


class MoodController(BaseController):
    MODEL_CLASS = Mood

    def validate(self, data, partial=False):
        """Field rules live in schemas/mood_schema.py."""
        mood_schema.validate(data, partial)
