"""Auth controller: login (token generation) and logout (token revocation)."""
from controllers.base_controller import BaseController
from services.token_service import generate_token, revoke_token
from core.exceptions import UnauthorizedError
from core.rate_limiter import RateLimiter
from core.security import build_token_response, hash_password, verify_password
from core.settings import settings
from models.user import User
from models.user_token import UserToken

# Verified against a dummy hash when the username does not exist, so the response
# time matches a real check and users cannot be enumerated by timing
_DUMMY_HASH = hash_password('timing-equalizer')


class AuthController(BaseController):
    MODEL_CLASS = User
    limiter = RateLimiter()  # shared by all requests: failed logins per username

    def login(self, data):
        """Validate credentials and return a new token (a user may hold many at once).

        `Persistent: true` issues a token without expiration ("keep me signed in");
        it stays valid until it is revoked (logout) or the user is deleted.
        """
        username, password = data.get('Username'), data.get('Password')
        if not username or not password:
            raise ValueError('Username and Password are required')
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValueError('Username and Password must be strings')
        persistent = data.get('Persistent', False)
        if not isinstance(persistent, bool):
            raise ValueError('Persistent must be a boolean')
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
                persistent=persistent, token_model=tokens
            )
        finally:
            tokens.close()
        return build_token_response(token)

    def logout(self):
        """Revoke the token used in the current request."""
        revoke_token(self.auth_token)
