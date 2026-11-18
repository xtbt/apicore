"""Auth controller: login (token generation) and logout (token revocation)."""
from controllers.BaseController import BaseController
from services.token_service import generate_token, revoke_token
from core.Exceptions import UnauthorizedError
from core.RateLimiter import RateLimiter
from core.Security import build_token_response, hash_password, verify_password
from core.Settings import settings
from models.User import User
from models.UserToken import UserToken

# Verified against a dummy hash when the username does not exist, so the response
# time matches a real check and users cannot be enumerated by timing
_DUMMY_HASH = hash_password('timing-equalizer')


class AuthController(BaseController):
    MODEL_CLASS = User
    limiter = RateLimiter()  # shared by all requests: failed logins per username

    def login(self, data):
        """Validate credentials and return a new token (a user may hold many at once)."""
        username, password = data.get('Username'), data.get('Password')
        if not username or not password:
            raise ValueError('Username and Password are required')
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValueError('Username and Password must be strings')
        key = username.lower()
        self.limiter.check(key)
        user = self.model.get_by_username(username)
        # Same error for unknown user / wrong password / inactive user: do not reveal which
        if (user is None or user['UserStatus'] != 'Active'
                or not verify_password(password, user['Password'])):
            if user is None:
                verify_password(password, _DUMMY_HASH)  # uniform response time
            self.limiter.fail(key)
            raise UnauthorizedError('Invalid credentials')
        self.limiter.reset(key)

        tokens = UserToken()
        try:
            tokens.delete_expired()  # housekeeping: drop tokens whose expiration passed
            token = generate_token(
                user['UserId'], user['UserRole'],
                settings.TOKEN_LIFETIME_MINUTES, settings.TOKEN_MIN_REMAINING_MINUTES,
                token_model=tokens
            )
        finally:
            tokens.close()
        return build_token_response(token)

    def logout(self):
        """Revoke the token used in the current request."""
        revoke_token(self.auth_token)
