"""Auth controller: login (token generation) and logout (token revocation)."""
from controllers.BaseController import BaseController
from core.Exceptions import UnauthorizedError
from core.Security import build_token_response, generate_token, revoke_token, verify_password
from core.Settings import settings
from models.User import User


class AuthController(BaseController):
    MODEL_CLASS = User

    def login(self, data):
        """Validate credentials and return a new token (a user may hold many at once)."""
        username, password = data.get('Username'), data.get('Password')
        if not username or not password:
            raise ValueError('Username and Password are required')
        user = self.model.get_by_username(username)
        # Same error for unknown user / wrong password / inactive user: do not reveal which
        if (user is None or user['UserStatus'] != 'Active'
                or not verify_password(password, user['Password'])):
            raise UnauthorizedError('Invalid credentials')
        token = generate_token(
            user['UserId'], 'user',
            settings.TOKEN_LIFETIME_MINUTES, settings.TOKEN_MIN_REMAINING_MINUTES
        )
        return build_token_response(token)

    def logout(self):
        """Revoke the token used in the current request."""
        revoke_token(self.auth_token)
