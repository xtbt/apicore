<?php
declare(strict_types=1);

namespace Apicore\Controllers;

use Apicore\Core\RateLimiter;
use Apicore\Core\Security;
use Apicore\Core\Settings;
use Apicore\Core\UnauthorizedError;
use Apicore\Models\User;
use Apicore\Models\UserToken;
use Apicore\Services\TokenService;
use ValueError;

/**
 * Auth controller: login (token generation) and logout (token revocation).
 *
 * Layer: controllers. It orchestrates the user model, the token service and the
 * rate limiter; it never touches SQL or the socket.
 */
final class AuthController extends BaseController
{
    protected const MODEL_CLASS = User::class;

    // Shared by all requests of this worker: failed logins per username
    private static ?RateLimiter $limiter = null;

    // Verified against a dummy hash when the username does not exist, so the
    // response time matches a real check and users cannot be enumerated by timing
    private static ?string $dummyHash = null;

    /**
     * Validate credentials and return a new token (a user may hold many at once).
     *
     * `Persistent: true` issues a token without expiration ("keep me signed in");
     * it stays valid until it is revoked (logout) or the user is deleted.
     *
     * @param array<string, mixed> $data
     * @return array<string, mixed>
     */
    public function login(array $data): array
    {
        $username = $data['Username'] ?? null;
        $password = $data['Password'] ?? null;
        if (!$username || !$password) {
            throw new ValueError('Username and Password are required');
        }
        if (!is_string($username) || !is_string($password)) {
            throw new ValueError('Username and Password must be strings');
        }
        $persistent = $data['Persistent'] ?? false;
        if (!is_bool($persistent)) {
            throw new ValueError('Persistent must be a boolean');
        }

        $key = strtolower($username);
        $limiter = self::limiter();
        $limiter->check($key);
        $user = $this->model->findByUsername($username);
        // Same error for unknown user / wrong password / inactive user: do not reveal which
        if ($user === null || $user['UserStatus'] !== 'Active'
            || !Security::verifyPassword($password, (string) $user['Password'])) {
            if ($user === null) {
                Security::verifyPassword($password, self::dummyHash());  // uniform response time
            }
            $limiter->fail($key);
            throw new UnauthorizedError('Invalid credentials');
        }
        $limiter->reset($key);

        $settings = Settings::instance();
        $tokens = new UserToken();
        try {
            $tokens->deleteExpired();  // housekeeping: drop tokens whose expiration passed
            [$token, $payload] = TokenService::generateToken(
                (int) $user['UserId'],
                (string) $user['UserRole'],
                $settings->TOKEN_LIFETIME_MINUTES,
                $settings->TOKEN_MIN_REMAINING_MINUTES,
                $persistent,
                $tokens,
            );
        } finally {
            $tokens->close();
        }
        return TokenService::buildTokenResponse($token, $payload);
    }

    /** Revoke the token used in the current request. */
    public function logout(): void
    {
        TokenService::revokeToken((string) $this->authToken);
    }

    private static function limiter(): RateLimiter
    {
        return self::$limiter ??= new RateLimiter();
    }

    private static function dummyHash(): string
    {
        return self::$dummyHash ??= Security::hashPassword('timing-equalizer');
    }
}
