"""Mood input schema: field rules of the `moods` entity.

Layer: schemas (cross-cutting). Validation only: no HTTP, no SQL.
"""
from schemas.base_schema import validate_enum, validate_string

STATUSES = ('Active', 'Inactive')


def validate(data, partial=False):
    """Validate a mood payload. partial=True (PATCH) checks only the fields sent."""
    validate_string(data, 'MoodName', max_length=16, required=True, partial=partial)
    validate_enum(data, 'MoodStatus', STATUSES, partial)
