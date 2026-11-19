"""Unit tests for core/security.py: password hashing and JWT signing.

No server and no database: pure functions only.
"""
import time
import unittest

from core.exceptions import UnauthorizedError
from core.security import (base64url_decode, base64url_encode, build_token_response,
                           encode_token, generate_payload, hash_password, hash_token,
                           verify_password, verify_token)


class TestPasswordHashing(unittest.TestCase):
    def test_hash_format(self):
        """The stored hash is self-contained: algorithm$iterations$salt$hash."""
        stored = hash_password('Secret123')
        algorithm, iterations, salt, digest = stored.split('$')
        self.assertEqual(algorithm, 'pbkdf2_sha256')
        self.assertEqual(int(iterations), 100000)
        self.assertEqual(len(salt), 32)
        self.assertEqual(len(digest), 64)

    def test_salt_is_random(self):
        """Two hashes of the same password differ (random salt)."""
        self.assertNotEqual(hash_password('Secret123'), hash_password('Secret123'))

    def test_verify_roundtrip(self):
        stored = hash_password('Secret123')
        self.assertTrue(verify_password('Secret123', stored))
        self.assertFalse(verify_password('Secret124', stored))
        self.assertFalse(verify_password('', stored))

    def test_verify_legacy_format(self):
        """The legacy "salt:hash" rows already in the database still verify."""
        import hashlib
        salt = 'ab' * 16
        digest = hashlib.pbkdf2_hmac('sha256', b'Legacy123', bytes.fromhex(salt), 100000).hex()
        self.assertTrue(verify_password('Legacy123', f'{salt}:{digest}'))
        self.assertFalse(verify_password('Legacy124', f'{salt}:{digest}'))

    def test_verify_malformed_hash(self):
        """A malformed stored hash returns False instead of raising."""
        for stored in ('', 'garbage', 'a$b$c', 'nothex:nothex'):
            self.assertFalse(verify_password('Secret123', stored))


class TestBase64Url(unittest.TestCase):
    def test_roundtrip(self):
        for raw in (b'', b'a', b'ab', b'abc', bytes(range(256))):
            self.assertEqual(base64url_decode(base64url_encode(raw)), raw)

    def test_no_padding(self):
        self.assertNotIn('=', base64url_encode(b'abc'))


class TestTokens(unittest.TestCase):
    def test_payload_claims(self):
        payload = generate_payload(7, 'Admin', 60, 10)
        self.assertEqual(payload['sub'], 7)
        self.assertEqual(payload['role'], 'Admin')
        self.assertEqual(payload['min_remaining_minutes'], 10)
        self.assertEqual(payload['exp'] - payload['iat'], 3600)
        self.assertEqual(len(payload['jti']), 32)

    def test_persistent_payload_has_no_exp(self):
        self.assertNotIn('exp', generate_payload(7, 'User', 60, 10, persistent=True))

    def test_extra_claims(self):
        self.assertEqual(generate_payload(1, 'User', 60, 10, extra_claims={'a': 1})['a'], 1)

    def test_encode_verify_roundtrip(self):
        token = encode_token(generate_payload(7, 'Admin', 60, 10))
        self.assertEqual(token.count('.'), 2)
        payload = verify_token(token)
        self.assertEqual((payload['sub'], payload['role']), (7, 'Admin'))

    def test_expired_token(self):
        token = encode_token(generate_payload(7, 'User', -1, 10))
        with self.assertRaises(UnauthorizedError):
            verify_token(token)

    def test_tampered_payload(self):
        """Changing the payload invalidates the signature."""
        header, payload, signature = encode_token(generate_payload(7, 'User', 60, 10)).split('.')
        forged = base64url_encode(b'{"sub":7,"role":"God","iat":0,"exp":9999999999}')
        with self.assertRaises(UnauthorizedError):
            verify_token(f'{header}.{forged}.{signature}')

    def test_tampered_signature(self):
        token = encode_token(generate_payload(7, 'User', 60, 10))
        with self.assertRaises(UnauthorizedError):
            verify_token(token[:-4] + 'AAAA')

    def test_wrong_algorithm(self):
        """A header claiming another algorithm is rejected (no alg confusion)."""
        header = base64url_encode(b'{"alg":"none","typ":"JWT"}')
        payload = base64url_encode(b'{"sub":7,"role":"God"}')
        with self.assertRaises(UnauthorizedError):
            verify_token(f'{header}.{payload}.')

    def test_malformed_token(self):
        for token in ('', 'abc', 'a.b', 'a.b.c.d'):
            with self.assertRaises(UnauthorizedError):
                verify_token(token)

    def test_hash_token(self):
        """The stored hash is a deterministic SHA-256 hex digest."""
        self.assertEqual(hash_token('abc'), hash_token('abc'))
        self.assertNotEqual(hash_token('abc'), hash_token('abd'))
        self.assertEqual(len(hash_token('abc')), 64)

    def test_build_token_response(self):
        token = encode_token(generate_payload(7, 'User', 60, 10))
        response = build_token_response(token)
        self.assertEqual(response['token'], token)
        self.assertEqual(response['token_type'], 'Bearer')
        self.assertEqual(response['min_remaining_minutes'], 10)
        self.assertIsNotNone(response['expires_at'])

    def test_build_token_response_persistent(self):
        token = encode_token(generate_payload(7, 'User', 60, 10, persistent=True))
        self.assertIsNone(build_token_response(token)['expires_at'])


if __name__ == '__main__':
    unittest.main()
