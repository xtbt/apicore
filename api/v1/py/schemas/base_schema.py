"""Reusable field validators shared by every entity schema.

Layer: schemas (cross-cutting). Pure functions over a dict: no HTTP, no SQL,
no database access. Each entity schema composes these helpers.
"""
from datetime import datetime


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


def validate_text(data, field, required=False, partial=False):
    """Raise ValueError unless data[field] is a string of any length (TEXT column)."""
    if partial and field not in data:
        return
    value = data.get(field)
    if value is not None and not isinstance(value, str):
        raise ValueError(f'{field} must be a string')
    if required and not value:
        raise ValueError(f'{field} is required')


def validate_integer(data, field, minimum=None, maximum=None, required=False, partial=False):
    """Raise ValueError unless data[field] is an int inside the given range.

    bool is rejected on purpose: in Python True is an int, but it is not a number
    a client should send for an INT column.
    """
    if partial and field not in data:
        return
    value = data.get(field)
    if value is None:
        if required:
            raise ValueError(f'{field} is required')
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{field} must be an integer')
    if minimum is not None and value < minimum:
        raise ValueError(f'{field} must be {minimum} or more')
    if maximum is not None and value > maximum:
        raise ValueError(f'{field} must be {maximum} or less')


def validate_number(data, field, minimum=None, maximum=None, required=False, partial=False):
    """Raise ValueError unless data[field] is an int or float inside the given range.

    DECIMAL and FLOAT columns accept both; the database rounds to the column scale.
    """
    if partial and field not in data:
        return
    value = data.get(field)
    if value is None:
        if required:
            raise ValueError(f'{field} is required')
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{field} must be a number')
    if minimum is not None and value < minimum:
        raise ValueError(f'{field} must be {minimum} or more')
    if maximum is not None and value > maximum:
        raise ValueError(f'{field} must be {maximum} or less')


def validate_boolean(data, field, required=False, partial=False):
    """Raise ValueError unless data[field] is true or false (tinyint(1) column)."""
    if partial and field not in data:
        return
    value = data.get(field)
    if value is None:
        if required:
            raise ValueError(f'{field} is required')
        return
    if not isinstance(value, bool):
        raise ValueError(f'{field} must be true or false')


def _validate_iso(data, field, fmt, label, example, required, partial):
    """Shared check for the date, datetime and time validators."""
    if partial and field not in data:
        return
    value = data.get(field)
    if value is None:
        if required:
            raise ValueError(f'{field} is required')
        return
    if not isinstance(value, str):
        raise ValueError(f'{field} must be a string')
    try:
        datetime.strptime(value, fmt)
    except ValueError:
        raise ValueError(f'{field} must be a {label} like {example}')


def validate_date(data, field, required=False, partial=False):
    """Raise ValueError unless data[field] is a 'YYYY-MM-DD' string (DATE column)."""
    _validate_iso(data, field, '%Y-%m-%d', 'date', '2026-01-31', required, partial)


def validate_datetime(data, field, required=False, partial=False):
    """Raise ValueError unless data[field] is 'YYYY-MM-DD HH:MM:SS' (DATETIME column)."""
    _validate_iso(data, field, '%Y-%m-%d %H:%M:%S', 'datetime', '2026-01-31 08:30:00', required, partial)


def validate_time(data, field, required=False, partial=False):
    """Raise ValueError unless data[field] is a 'HH:MM:SS' string (TIME column)."""
    _validate_iso(data, field, '%H:%M:%S', 'time', '08:30:00', required, partial)


def validate_year(data, field, minimum=1901, maximum=2155, required=False, partial=False):
    """Raise ValueError unless data[field] is a four-digit year (YEAR column).

    The bounds are the ones MySQL accepts for YEAR(4); the message names the
    field as a year so the client knows what to send, not just a range.
    """
    if partial and field not in data:
        return
    value = data.get(field)
    if value is None:
        if required:
            raise ValueError(f'{field} is required')
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{field} must be a four-digit year')
    if not minimum <= value <= maximum:
        raise ValueError(f'{field} must be a four-digit year between {minimum} and {maximum}')


def validate_json(data, field, required=False, partial=False):
    """Raise ValueError unless data[field] is a dict or a list (JSON column)."""
    if partial and field not in data:
        return
    value = data.get(field)
    if value is None:
        if required:
            raise ValueError(f'{field} is required')
        return
    if not isinstance(value, (dict, list)):
        raise ValueError(f'{field} must be a JSON object or array')
