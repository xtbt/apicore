"""Example input schema: field rules of the `example` entity.

Layer: schemas (cross-cutting). Validation only: no HTTP, no SQL.

Each field shows the validator that matches its column type, so a student can
copy the pair (column type -> validator) into their own schema.
"""
from schemas.base_schema import (
    validate_boolean, validate_date, validate_datetime, validate_enum,
    validate_integer, validate_json, validate_number, validate_string,
    validate_text, validate_time, validate_year,
)

STATUSES = ('Active', 'Inactive')


def validate(data, partial=False):
    """Validate an example payload. partial=True (PATCH) checks only the fields sent."""
    validate_string(data, 'ExampleName', max_length=45, required=True, partial=partial)
    validate_string(data, 'ExampleCode', max_length=3, partial=partial)
    validate_text(data, 'ExampleDescription', partial=partial)
    validate_number(data, 'ExamplePrice', minimum=0, partial=partial)
    validate_integer(data, 'ExampleQuantity', minimum=0, partial=partial)
    validate_integer(data, 'ExampleBigNumber', partial=partial)
    validate_number(data, 'ExampleRatio', partial=partial)
    validate_boolean(data, 'ExampleActive', partial=partial)
    validate_enum(data, 'ExampleStatus', STATUSES, partial)
    validate_date(data, 'ExampleBirthDate', partial=partial)
    validate_datetime(data, 'ExampleCreatedAt', partial=partial)
    validate_time(data, 'ExampleStartTime', partial=partial)
    validate_year(data, 'ExampleYear', partial=partial)
    validate_json(data, 'ExampleMetadata', partial=partial)
    # BLOB holds 65535 bytes; base64 grows that to 87380 chars (4 * ceil(65535 / 3))
    validate_string(data, 'ExamplePicture', max_length=87380, partial=partial)
