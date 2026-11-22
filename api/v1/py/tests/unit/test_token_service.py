"""Unit tests for services/token_service.py: login response formatting.

No server and no database: the payload is built in memory.
"""
import unittest

from core.security import encode_token, generate_payload
from services.token_service import build_token_response


class TestBuildTokenResponse(unittest.TestCase):

    def test_formats_a_token_with_expiration(self):
        payload = generate_payload(7, 'User', 60, 10)
        token = encode_token(payload)
        response = build_token_response(token, payload)
        self.assertEqual(response['token'], token)
        self.assertEqual(response['token_type'], 'Bearer')
        self.assertEqual(response['min_remaining_minutes'], 10)
        self.assertFalse(response['persistent'])
        self.assertIsNotNone(response['expires_at'])

    def test_uses_the_payload_without_decoding_the_token(self):
        payload = {'exp': 1_900_000_000, 'min_remaining_minutes': 10}
        response = build_token_response('header.payload.signature', payload)
        self.assertEqual(response['token'], 'header.payload.signature')
        self.assertIsNotNone(response['expires_at'])

    def test_persistent_token_has_no_expiration(self):
        payload = generate_payload(7, 'User', 60, 10, persistent=True)
        response = build_token_response(encode_token(payload), payload)
        self.assertIsNone(response['expires_at'])
        self.assertTrue(response['persistent'])


if __name__ == '__main__':
    unittest.main()
