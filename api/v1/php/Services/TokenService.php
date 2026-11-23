<?php
declare(strict_types=1);

namespace Apicore\Services;

use Apicore\Core\Security;
use Apicore\Core\Settings;
use Apicore\Core\UnauthorizedError;
use Apicore\Models\UserToken;
use DateTimeImmutable;
use DateTimeZone;

/**
 * Token service: lifecycle of bearer tokens (create, validate, revoke).
 *
 * Layer: services. Business rules and orchestration over the `users_tokens`
 * repository (one row per token, so a user can be logged in on many devices;
 * revoking a token means deleting its row). It never knows about HTTP: no
 * request objects, no status codes. Core\Security holds the pure crypto.
 */
final class TokenService
{
    /** users_tokens.TokenExpiration is NOT NULL, so persistent tokens get a far-future date. */
    public const PERSISTENT_EXPIRATION = '9999-12-31 23:59:59';

    /**
     * Create a signed JWT and persist its hash in `users_tokens`.
     *
     * lifetimeMinutes is ignored when persistent=true (no `exp` claim).
     * minRemainingMinutes is only a claim: the client decides when to renew.
     * An existing $tokenModel is reused (and left open); otherwise a new one is
     * created and closed here. Returns the signed token and its exact payload,
     * so the response formatter need not decode the token again.
     *
     * @return array{0: string, 1: array<string, mixed>}
     */
    public static function generateToken(
        int $userId,
        string $role,
        int $lifetimeMinutes,
        int $minRemainingMinutes,
        bool $persistent = false,
        ?UserToken $tokenModel = null,
    ): array {
        $payload = Security::generatePayload($userId, $role, $lifetimeMinutes, $minRemainingMinutes, $persistent);
        $token = Security::encodeToken($payload);

        $expiration = $persistent
            ? self::PERSISTENT_EXPIRATION
            : gmdate('Y-m-d H:i:s', (int) $payload['exp']);
        $model = $tokenModel ?? new UserToken();
        try {
            $model->create([
                'UserId' => $userId,
                'TokenHash' => Security::hashToken($token),
                'TokenExpiration' => $expiration,
                'TokenCreatedAt' => gmdate('Y-m-d H:i:s'),
            ]);
        } finally {
            if ($tokenModel === null) {
                $model->close();
            }
        }
        return [$token, $payload];
    }

    /**
     * Format a login response from the payload already available at generation.
     *
     * The caller always holds the payload (generateToken returns it), so the JWT
     * is never parsed a second time.
     *
     * @param array<string, mixed> $payload
     * @return array<string, mixed>
     */
    public static function buildTokenResponse(string $token, array $payload): array
    {
        $expiresAt = isset($payload['exp']) ? self::isoformatFromTimestamp((int) $payload['exp']) : null;
        return [
            'token' => $token,
            'token_type' => 'Bearer',
            'expires_at' => $expiresAt,
            'persistent' => !isset($payload['exp']),
            'min_remaining_minutes' => $payload['min_remaining_minutes'],
        ];
    }

    /**
     * Validate a token and return its payload.
     *
     * Checks: structure, signature, algorithm, expiration claim (verifyToken),
     * presence in `users_tokens` with a TokenExpiration still in the future (not
     * revoked, not expired in the database) and that the user is Active. The role
     * claim is replaced with the current value in `users`, so a role change
     * applies immediately. Throws UnauthorizedError on any failure.
     *
     * @return array<string, mixed>
     */
    public static function decodeToken(string $token): array
    {
        $payload = Security::verifyToken($token);
        $model = new UserToken();
        try {
            $state = $model->getUserState(Security::hashToken($token));
        } finally {
            $model->close();
        }
        if ($state === null) {
            throw new UnauthorizedError('Token revoked or unknown');
        }
        [$status, $role] = $state;
        if ($status !== 'Active') {
            throw new UnauthorizedError('User inactive or not found');
        }
        // The database is the source of truth for the role: a token issued before
        // a role change must not keep the old privileges
        $payload['role'] = $role;
        return $payload;
    }

    /** Delete the token row. Returns true if it existed. */
    public static function revokeToken(string $token): bool
    {
        $model = new UserToken();
        try {
            return $model->deleteByHash(Security::hashToken($token)) > 0;
        } finally {
            $model->close();
        }
    }

    /** Epoch seconds -> ISO 8601 string in APP_TIMEZONE (same as utils/date_utils.py). */
    public static function isoformatFromTimestamp(int $epoch): string
    {
        $timezone = new DateTimeZone(Settings::instance()->APP_TIMEZONE);
        return (new DateTimeImmutable('@' . $epoch))->setTimezone($timezone)->format('Y-m-d\TH:i:sP');
    }
}
