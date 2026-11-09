"""Security: password hashing and manual JWT (HS256) generation/validation.

Layer: core (cross-cutting). Standard library only. Tokens are persisted in
`users_tokens` (one row per token, so a user can be logged in on many devices);
revoking a token means deleting its row.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone

from core.Exceptions import UnauthorizedError
from core.Settings import settings
from models.User import User
from models.UserToken import UserToken

HASH_ALGORITHM = 'pbkdf2_sha256'
HASH_ITERATIONS = 100000
# `users_tokens.TokenExpiration` is NOT NULL, so persistent tokens get a far-future date
PERSISTENT_EXPIRATION = datetime(9999, 12, 31, 23, 59, 59)


# --- Password hashing ---

def hash_password(password: str) -> str:
    """Return "algorithm$iterations$salt$hash" (self-contained, salt is random)."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), HASH_ITERATIONS)
    return f'{HASH_ALGORITHM}${HASH_ITERATIONS}${salt}${digest.hex()}'


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a password against a stored hash in constant time.

    Also accepts the legacy "salt:hash" format (PBKDF2-SHA256, 100000 iterations)
    used by the rows already present in the database.
    """
    try:
        if '$' in stored_hash:
            _, iterations, salt, expected = stored_hash.split('$')
        else:
            salt, expected = stored_hash.split(':')
            iterations = HASH_ITERATIONS
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations))
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), expected)


# --- Base64 URL encoding (JWT) ---

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def base64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))


# --- Tokens ---

def _sign(signing_input: str) -> str:
    """HMAC-SHA256 signature of "header.payload"."""
    return base64url_encode(hmac.new(settings.JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).digest())


def _hash_token(token: str) -> str:
    """SHA-256 of the raw token: this is what is stored and looked up in the DB."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(user_id: int, role: str, lifetime_minutes: int, min_remaining_minutes: int,
                   persistent: bool = False, extra_claims: dict = None) -> str:
    """Create a signed JWT and persist its hash in `users_tokens`.

    lifetime_minutes is ignored when persistent=True (no `exp` claim).
    min_remaining_minutes is only a claim: the client decides when to renew.
    """
    now = int(time.time())
    payload = {
        'sub': user_id, 'role': role, 'iat': now, 'jti': secrets.token_hex(16),
        'min_remaining_minutes': min_remaining_minutes,
    }
    if not persistent:
        payload['exp'] = now + lifetime_minutes * 60
    payload.update(extra_claims or {})

    header = {'alg': settings.JWT_ALGORITHM, 'typ': 'JWT'}
    signing_input = '.'.join(base64url_encode(json.dumps(part, separators=(',', ':')).encode())
                             for part in (header, payload))
    token = f'{signing_input}.{_sign(signing_input)}'

    expiration = PERSISTENT_EXPIRATION if persistent else datetime.fromtimestamp(payload['exp'], timezone.utc).replace(tzinfo=None)
    model = UserToken()
    try:
        model.create({
            'UserId': user_id,
            'TokenHash': _hash_token(token),
            'TokenExpiration': expiration,
            'TokenCreatedAt': datetime.fromtimestamp(now, timezone.utc).replace(tzinfo=None),
        })
    finally:
        model.close()
    return token


def decode_token(token: str) -> dict:
    """Validate a token and return its payload.

    Checks: structure, signature, algorithm, expiration (skipped for persistent
    tokens), presence in `users_tokens` (not revoked) and that the user is Active.
    Raises UnauthorizedError on any failure.
    """
    try:
        header_b64, payload_b64, signature = token.split('.')
        header = json.loads(base64url_decode(header_b64))
        payload = json.loads(base64url_decode(payload_b64))
    except ValueError:
        raise UnauthorizedError('Invalid token')

    if header.get('alg') != settings.JWT_ALGORITHM:
        raise UnauthorizedError('Invalid token')
    if not hmac.compare_digest(_sign(f'{header_b64}.{payload_b64}'), signature):
        raise UnauthorizedError('Invalid token')
    if 'exp' in payload and payload['exp'] < time.time():
        raise UnauthorizedError('Token expired')

    token_model, user_model = UserToken(), User()
    try:
        if token_model.get_by_hash(_hash_token(token)) is None:
            raise UnauthorizedError('Token revoked or unknown')
        user = user_model.get_by_id(payload.get('sub'))
        if user is None or user['UserStatus'] != 'Active':
            raise UnauthorizedError('User inactive or not found')
    finally:
        token_model.close()
        user_model.close()
    return payload


def revoke_token(token: str) -> bool:
    """Delete the token row. Returns True if it existed."""
    model = UserToken()
    try:
        return model.delete_by_hash(_hash_token(token)) > 0
    finally:
        model.close()


def build_token_response(token: str) -> dict:
    """Format the login response from a token generated by generate_token."""
    payload = json.loads(base64url_decode(token.split('.')[1]))
    expires_at = None
    if 'exp' in payload:
        expires_at = datetime.fromtimestamp(payload['exp'], timezone.utc).isoformat()
    return {
        'token': token,
        'token_type': 'Bearer',
        'expires_at': expires_at,
        'min_remaining_minutes': payload['min_remaining_minutes'],
    }
