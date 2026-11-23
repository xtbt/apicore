"""User input schema: field rules of the `users` entity.

Layer: schemas (cross-cutting). Validation only: no HTTP, no SQL. Business rules
(duplicated username, password hashing, role permissions) live in the controller.
"""
from schemas.base_schema import validate_enum, validate_string

REQUIRED = {'Username': 16, 'Name': 45, 'PaternalSurname': 25}
OPTIONAL = {'MaternalSurname': 25}
STATUSES = ('Active', 'Inactive')
ROLES = ('God', 'Admin', 'User')


def validate(data, partial=False):
    """Validate a user payload. partial=True (PATCH) checks only the fields sent."""
    for field, max_length in {**REQUIRED, **OPTIONAL}.items():
        validate_string(data, field, max_length=max_length,
                        required=field in REQUIRED, partial=partial)
    validate_enum(data, 'UserStatus', STATUSES, partial)
    if 'UserRole' in data:
        validate_enum(data, 'UserRole', ROLES)
