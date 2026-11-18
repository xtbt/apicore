"""Token service: lifecycle of bearer tokens (create, validate, revoke).

Layer: services. Business rules and orchestration over the `users_tokens`
repository (one row per token, so a user can be logged in on many devices;
revoking a token means deleting its row). It never knows about HTTP: no
request objects, no status codes. core/Security.py holds the pure crypto.
"""
from datetime import datetime
import time

from core.date_utils import utc_from_timestamp, utc_now
from core.Exceptions import UnauthorizedError
from core.Security import encode_token, generate_payload, hash_token, verify_token
from models.UserToken import UserToken

# `users_tokens.TokenExpiration` is NOT NULL, so persistent tokens get a far-future date
PERSISTENT_EXPIRATION = datetime(9999, 12, 31, 23, 59, 59)


def generate_token(user_id, role, lifetime_minutes, min_remaining_minutes,
                   persistent=False, extra_claims=None, token_model=None):
    """Create a signed JWT and persist its hash in `users_tokens`.

    lifetime_minutes is ignored when persistent=True (no `exp` claim).
    min_remaining_minutes is only a claim: the client decides when to renew.
    An existing `token_model` is reused (and left open); otherwise a new one
    is created and closed here.
    """
    payload = generate_payload(user_id, role, lifetime_minutes, min_remaining_minutes,
                               persistent, extra_claims)
    token = encode_token(payload)

    now = int(time.time())
    expiration = PERSISTENT_EXPIRATION if persistent else utc_from_timestamp(payload['exp'])
    model = token_model or UserToken()
    try:
        model.create({
            'UserId': user_id,
            'TokenHash': hash_token(token),
            'TokenExpiration': expiration,
            'TokenCreatedAt': utc_now(),
        })
    finally:
        if token_model is None:
            model.close()
    return token


def decode_token(token):
    """Validate a token and return its payload.

    Checks: structure, signature, algorithm, expiration claim (verify_token), presence
    in `users_tokens` with a `TokenExpiration` still in the future (not revoked, not
    expired in the database) and that the user is Active. The role claim is replaced
    with the current value in `users`, so a role change applies immediately.
    Raises UnauthorizedError on any failure.
    """
    payload = verify_token(token)
    model = UserToken()
    try:
        state = model.get_user_state(hash_token(token))
    finally:
        model.close()
    if state is None:
        raise UnauthorizedError('Token revoked or unknown')
    status, role = state
    if status != 'Active':
        raise UnauthorizedError('User inactive or not found')
    # The database is the source of truth for the role: a token issued before a
    # role change must not keep the old privileges
    payload['role'] = role
    return payload


def revoke_token(token):
    """Delete the token row. Returns True if it existed."""
    model = UserToken()
    try:
        return model.delete_by_hash(hash_token(token)) > 0
    finally:
        model.close()
