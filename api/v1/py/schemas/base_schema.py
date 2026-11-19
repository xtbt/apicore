"""Reusable field validators shared by every entity schema.

Layer: schemas (cross-cutting). Pure functions over a dict: no HTTP, no SQL,
no database access. Each entity schema composes these helpers.
"""


def validate_enum(data, field, options, partial=False):
    """Raise ValueError unless data[field] is one of `options`.

    partial=True (PATCH) skips the check when the field is absent.
    """
    if partial and field not in data:
        return
    if data.get(field) not in options:
        raise ValueError(f'{field} must be ' + ' or '.join(f'"{option}"' for option in options))


def validate_string(data, field, max_length=None, required=False, partial=False):
    """Raise ValueError unless data[field] is a string within `max_length`.

    required=True rejects a missing or empty value. partial=True (PATCH) skips
    the check when the field is absent.
    """
    if partial and field not in data:
        return
    value = data.get(field)
    if value is not None and not isinstance(value, str):
        raise ValueError(f'{field} must be a string')
    if required and not value:
        raise ValueError(f'{field} is required')
    if value and max_length and len(value) > max_length:
        raise ValueError(f'{field} must be {max_length} chars max')
