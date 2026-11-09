"""User controller: validation rules and password handling of the `users` entity."""
from controllers.BaseController import BaseController
from core.Security import hash_password
from models.User import User
from models.UserToken import UserToken


class UserController(BaseController):
    MODEL_CLASS = User
    REQUIRED = {'Username': 16, 'Name': 45, 'PaternalSurname': 25}
    OPTIONAL = {'MaternalSurname': 25}

    def validate(self, data):
        for field, max_length in {**self.REQUIRED, **self.OPTIONAL}.items():
            value = data.get(field)
            if field in self.REQUIRED and not value:
                raise ValueError(f'{field} is required')
            if value and len(value) > max_length:
                raise ValueError(f'{field} must be {max_length} chars max')
        if data.get('UserStatus') not in ('Active', 'Inactive'):
            raise ValueError('UserStatus must be "Active" or "Inactive"')

    def prepare(self, data, record_id=None):
        """Reject duplicated usernames and store the password hashed.

        The password is required on create and optional on update (omitted = unchanged).
        """
        existing = self.model.get_by_username(data['Username'])
        if existing and str(existing['UserId']) != str(record_id):
            raise ValueError('Username already exists')
        data = dict(data)
        if data.get('Password'):
            data['Password'] = hash_password(data['Password'])
        elif record_id is None:
            raise ValueError('Password is required')
        else:
            data.pop('Password', None)
        return data

    def delete(self, record_id):
        """Delete the user and revoke all of its tokens."""
        tokens = UserToken()
        try:
            tokens.delete_by_user(record_id)
        finally:
            tokens.close()
        return super().delete(record_id)
