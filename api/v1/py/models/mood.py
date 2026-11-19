"""Mood model: only the table definition of the `moods` entity."""
from models.base_model import BaseModel


class Mood(BaseModel):
    TABLE_NAME = 'moods'
    ID_COLUMN = 'MoodId'
    COLUMNS = ('MoodName', 'MoodStatus')
