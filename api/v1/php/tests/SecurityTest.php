<?php
declare(strict_types=1);

namespace Apicore\Tests;

use Apicore\Core\Security;
use Apicore\Core\UnauthorizedError;

/** Security: PBKDF2 hashing, base64url and HS256 signing. */
final class SecurityTest extends TestCase
{
    public function testHashRoundTrips(): void
    {
        $hash = Security::hashPassword('secret');
        $this->assertTrue(Security::verifyPassword('secret', $hash));
    }

    public function testWrongPasswordIsRejected(): void
    {
        $hash = Security::hashPassword('secret');
        $this->assertFalse(Security::verifyPassword('other', $hash));
    }

    public function testHashIsSalted(): void
    {
        $this->assertTrue(Security::hashPassword('secret') !== Security::hashPassword('secret'));
    }

    public function testHashFormatMatchesPython(): void
    {
        $hash = Security::hashPassword('secret');
        $parts = explode('$', $hash);
        $this->assertCount(4, $parts);
        $this->assertSame('pbkdf2_sha256', $parts[0]);
        $this->assertSame('100000', $parts[1]);
    }

    public function testCorruptHashIsRejected(): void
    {
        $this->assertFalse(Security::verifyPassword('secret', 'not-a-hash'));
    }

    public function testBase64UrlRoundTrips(): void
    {
        $encoded = Security::base64UrlEncode("a+b/c\x00\xff");
        $this->assertFalse(str_contains($encoded, '+'));
        $this->assertFalse(str_contains($encoded, '/'));
        $this->assertFalse(str_contains($encoded, '='));
        $this->assertSame("a+b/c\x00\xff", Security::base64UrlDecode($encoded));
    }

    public function testTokenRoundTrips(): void
    {
        $payload = ['sub' => 1, 'role' => 'God', 'exp' => time() + 60];
        $decoded = Security::verifyToken(Security::encodeToken($payload));
        $this->assertSame(1, $decoded['sub']);
        $this->assertSame('God', $decoded['role']);
    }

    public function testExpiredTokenIsRejected(): void
    {
        $token = Security::encodeToken(['sub' => 1, 'exp' => time() - 10]);
        $this->assertThrows(UnauthorizedError::class, static fn () => Security::verifyToken($token));
    }

    public function testTamperedSignatureIsRejected(): void
    {
        $token = Security::encodeToken(['sub' => 1, 'exp' => time() + 60]);
        $tampered = substr($token, 0, -2) . 'xx';
        $this->assertThrows(UnauthorizedError::class, static fn () => Security::verifyToken($tampered));
    }

    public function testMalformedTokenIsRejected(): void
    {
        $this->assertThrows(UnauthorizedError::class, static fn () => Security::verifyToken('not.a.jwt'));
    }

    public function testTokenHashIsStable(): void
    {
        $this->assertSame(Security::hashToken('abc'), Security::hashToken('abc'));
        $this->assertTrue(Security::hashToken('abc') !== Security::hashToken('abd'));
    }
}
