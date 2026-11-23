<?php
declare(strict_types=1);

namespace Apicore\Tests;

use Apicore\Core\Security;
use Apicore\Core\UnauthorizedError;
use Apicore\Services\TokenService;

/** TokenService: claims, login response shape and rejection without a database. */
final class TokenServiceTest extends TestCase
{
    public function testPayloadCarriesTheExpectedClaims(): void
    {
        $payload = Security::generatePayload(3, 'User', 60, 10);
        $this->assertSame(3, $payload['sub']);
        $this->assertSame('User', $payload['role']);
        $this->assertSame(10, $payload['min_remaining_minutes']);
        $this->assertTrue(isset($payload['iat'], $payload['jti'], $payload['exp']));
    }

    public function testPersistentPayloadHasNoExpiration(): void
    {
        $payload = Security::generatePayload(3, 'User', 60, 10, true);
        $this->assertFalse(isset($payload['exp']));
    }

    public function testJtiIsUnique(): void
    {
        $a = Security::generatePayload(1, 'God', 60, 10);
        $b = Security::generatePayload(1, 'God', 60, 10);
        $this->assertTrue($a['jti'] !== $b['jti']);
    }

    public function testResponseShapeForTemporaryToken(): void
    {
        $payload = Security::generatePayload(1, 'God', 60, 10);
        $response = TokenService::buildTokenResponse('tok', $payload);
        $this->assertSame('tok', $response['token']);
        $this->assertSame('Bearer', $response['token_type']);
        $this->assertFalse($response['persistent']);
        $this->assertSame(10, $response['min_remaining_minutes']);
        $this->assertTrue(is_string($response['expires_at']));
    }

    public function testResponseShapeForPersistentToken(): void
    {
        $payload = Security::generatePayload(1, 'God', 60, 10, true);
        $response = TokenService::buildTokenResponse('tok', $payload);
        $this->assertTrue($response['persistent']);
        $this->assertNull($response['expires_at']);
    }

    public function testIsoformatUsesTheConfiguredTimezone(): void
    {
        $formatted = TokenService::isoformatFromTimestamp(0);
        $this->assertTrue((bool) preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/', $formatted));
    }

    public function testDecodeRejectsMalformedTokenBeforeTouchingTheDatabase(): void
    {
        $this->assertThrows(UnauthorizedError::class, static fn () => TokenService::decodeToken('not.a.jwt'));
    }
}
