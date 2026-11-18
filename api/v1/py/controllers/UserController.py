"""User controller: validation rules and password handling of the `users` entity."""
from controllers.BaseController import BaseController
from core.Exceptions import ForbiddenError
from core.Security import hash_password
from models.User import User
from models.UserToken import UserToken


class UserController(BaseController):
    MODEL_CLASS = User
    REQUIRED = {'Username': 16, 'Name': 45, 'PaternalSurname': 25}
    OPTIONAL = {'MaternalSurname': 25}
    PRIVILEGED_ROLES = ('Admin', 'God')  # the only roles allowed to assign UserRole

    def validate(self, data, partial=False):
        for field, max_length in {**self.REQUIRED, **self.OPTIONAL}.items():
            if partial and field not in data:
                continue
            value = data.get(field)
            if value is not None and not isinstance(value, str):
                raise ValueError(f'{field} must be a string')
            if field in self.REQUIRED and not value:
                raise ValueError(f'{field} is required')
            if value and len(value) > max_length:
                raise ValueError(f'{field} must be {max_length} chars max')
        self._validate_enum(data, 'UserStatus', ('Active', 'Inactive'), partial)
        if not partial:
            data.setdefault('UserRole', 'User')  # self-registration via POST /users defaults to User
        self._validate_enum(data, 'UserRole', ('God', 'Admin', 'User'), partial)

    def get_all(self, page=None, size=None):
        """The user list is restricted to Admin and God."""
        if (self.auth_user or {}).get('role') not in self.PRIVILEGED_ROLES:
            raise ForbiddenError('Only Admin or God can list users')
        return super().get_all(page, size)

    def get_by_id(self, record_id):
        """A user may read its own account; any other account is Admin/God only."""
        caller = self.auth_user or {}
        if (caller.get('role') not in self.PRIVILEGED_ROLES
                and str(record_id) != str(caller.get('sub'))):
            raise ForbiddenError('You can only read your own account')
        return super().get_by_id(record_id)

    def authorize(self, record_id, action, data=None):
        """Ownership rules for /users/{id}: own account, or Admin/God over others.

        - A plain User may only touch its own account (403 otherwise, without
          revealing whether the record exists).
        - An Admin may not touch a God account.
        - The last God account cannot be deleted nor lose its role.
        """
        caller = self.auth_user or {}
        caller_role = caller.get('role')
        if caller_role not in self.PRIVILEGED_ROLES and str(record_id) != str(caller.get('sub')):
            raise ForbiddenError('You can only modify your own account')
        target = self.model.get_by_id(record_id)
        if target is None:
            return  # the model reports 404
        if caller_role == 'Admin' and target['UserRole'] == 'God':
            raise ForbiddenError('Only God can modify a God account')
        if target['UserRole'] != 'God' or self.model.count_by_role('God') > 1:
            return
        # Last God account: deleting it or changing its role would leave no God
        if action == 'delete':
            raise ForbiddenError('The last God account cannot be deleted')
        if (data or {}).get('UserRole', 'God') != 'God':
            raise ForbiddenError('The last God account cannot lose its role')

    def prepare(self, data, record_id=None):
        """Reject duplicated usernames, enforce role permissions and store the password hashed.

        The password is required on create and optional on update (omitted = unchanged).
        Only Admin or God may assign a role other than 'User'; self-registration
        (public POST /users) always creates a plain 'User'.
        """
        if 'Username' in data:
            existing = self.model.get_by_username(data['Username'])
            if existing and str(existing['UserId']) != str(record_id):
                raise ValueError('Username already exists')
        role = data.get('UserRole')
        caller = (self.auth_user or {}).get('role')
        if role is not None and role != 'User':
            if caller not in self.PRIVILEGED_ROLES:
                raise ForbiddenError('Only Admin or God can assign roles')
            if role == 'God' and caller != 'God':
                raise ForbiddenError('Only God can assign the God role')
        data = dict(data)
        if data.get('Password') is not None and not isinstance(data['Password'], str):
            raise ValueError('Password must be a string')
        if data.get('Password'):
            data['Password'] = hash_password(data['Password'])
        elif record_id is None:
            raise ValueError('Password is required')
        else:
            data.pop('Password', None)
        return data

    def delete(self, record_id):
        """Delete the user and revoke all of its tokens."""
        self.authorize(record_id, 'delete')  # before revoking: a refused delete changes nothing
        tokens = UserToken()
        try:
            tokens.delete_by_user(record_id)
        finally:
            tokens.close()
        return super().delete(record_id)
