"""Integration tests for the `example` reference entity.

Layer: tests (integration). Exercises one column per common MySQL data type,
both the happy path and the validation errors, against the real server.
"""
import unittest
from functools import partial

from tests.integration import support

PORT = 65440 + support.port_offset()
BASE_URL = f'http://localhost:{PORT}'
call = partial(support.call, BASE_URL)
server_process = None

FULL_PAYLOAD = {
    'ExampleName': 'Integration row',
    'ExampleCode': 'ITG',
    'ExampleDescription': 'Every column set by the test.',
    'ExamplePrice': 12.5,
    'ExampleQuantity': 3,
    'ExampleBigNumber': 1234567890123,
    'ExampleRatio': 0.25,
    'ExampleActive': False,
    'ExampleStatus': 'Inactive',
    'ExampleBirthDate': '1999-12-31',
    'ExampleCreatedAt': '2025-06-01 10:00:00',
    'ExampleStartTime': '23:59:59',
    'ExampleYear': 2025,
    'ExampleMetadata': {'tags': ['a', 'b'], 'level': 2},
    'ExamplePicture': 'aGVsbG8=',
}


def setUpModule():
    global server_process
    server_process = support.start_server(PORT, BASE_URL)


def tearDownModule():
    support.stop_server(server_process)


class TestExample(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        status, body = call('POST', '/auth/login',
                            {'Username': 'godtest', 'Password': 'godtest'})
        if status != 200:
            raise RuntimeError(f'could not log in: {status} {body}')
        cls.token = body['data']['token']

    def test_1_seeded_row_returns_every_type(self):
        """The seeded row shows how each column type comes back in JSON."""
        status, body = call('GET', '/examples', token=self.token)
        self.assertEqual(status, 200)
        row = next(item for item in body['data'] if item['ExampleId'] == 1)
        self.assertIsInstance(row['ExamplePrice'], str)
        self.assertEqual(row['ExamplePrice'], '19.99')
        self.assertIs(row['ExampleActive'], True)
        self.assertIsInstance(row['ExampleMetadata'], dict)
        self.assertEqual(row['ExampleBirthDate'], '2000-01-31')
        self.assertEqual(row['ExampleCreatedAt'], '2026-01-31 08:30:00')
        self.assertEqual(row['ExampleStartTime'], '08:30:00')
        self.assertEqual(row['ExampleYear'], 2026)
        self.assertEqual(row['ExamplePicture'], 'iVBORw0KGgo=')

    def test_2_create_read_update_delete(self):
        status, body = call('POST', '/examples', FULL_PAYLOAD, self.token)
        self.assertEqual(status, 201)
        example_id = body['ID']

        status, body = call('GET', f'/examples/{example_id}', token=self.token)
        self.assertEqual(status, 200)
        row = body['data']
        self.assertEqual(row['ExampleMetadata'], FULL_PAYLOAD['ExampleMetadata'])
        self.assertEqual(row['ExamplePicture'], 'aGVsbG8=')
        self.assertIs(row['ExampleActive'], False)
        self.assertEqual(row['ExampleBigNumber'], 1234567890123)

        status, body = call('PATCH', f'/examples/{example_id}',
                            {'ExampleQuantity': 9}, self.token)
        self.assertEqual((status, body['message']), (200, 'Example updated'))

        status, body = call('PATCH', f'/examples/{example_id}',
                            {'ExampleQuantity': 9}, self.token)
        self.assertEqual((status, body['message']), (200, 'No changes to apply'))

        status, _body = call('DELETE', f'/examples/{example_id}', token=self.token)
        self.assertEqual(status, 200)
        status, _body = call('DELETE', f'/examples/{example_id}', token=self.token)
        self.assertEqual(status, 404)

    def test_3_invalid_values_are_rejected(self):
        """Each validator rejects the wrong type with 400, never 500."""
        status, body = call('POST', '/examples', FULL_PAYLOAD, self.token)
        self.assertEqual(status, 201)
        example_id = body['ID']
        try:
            cases = (
                ({'ExampleBirthDate': '31-12-1999'}, 'ExampleBirthDate must be a date'),
                ({'ExampleCreatedAt': '2025-06-01'}, 'ExampleCreatedAt must be a datetime'),
                ({'ExampleStartTime': '25:00:00'}, 'ExampleStartTime must be a time'),
                ({'ExamplePicture': 'no-base64!!'}, 'ExamplePicture must be a base64 string'),
                ({'ExampleActive': 'yes'}, 'ExampleActive must be true or false'),
                ({'ExampleMetadata': 'text'}, 'ExampleMetadata must be a JSON object or array'),
                ({'ExampleYear': 1800}, 'ExampleYear must be a four-digit year between 1901 and 2155'),
                ({'ExamplePicture': 'x' * 87381}, 'ExamplePicture must be 87380 chars max'),
                ({'ExampleQuantity': -1}, 'ExampleQuantity must be 0 or more'),
                ({'ExamplePrice': 'cheap'}, 'ExamplePrice must be a number'),
            )
            for payload, expected in cases:
                with self.subTest(payload=payload):
                    status, body = call('PATCH', f'/examples/{example_id}',
                                        payload, self.token)
                    self.assertEqual(status, 400)
                    self.assertIn(expected, body['error'])
        finally:
            call('DELETE', f'/examples/{example_id}', token=self.token)

    def test_4_unknown_field_is_rejected(self):
        status, body = call('POST', '/examples',
                            {**FULL_PAYLOAD, 'ExampleUnknown': 1}, self.token)
        self.assertEqual(status, 400)
        self.assertIn('Unknown field', body['error'])

    def test_5_requires_authentication(self):
        status, _body = call('GET', '/examples')
        self.assertEqual(status, 401)


if __name__ == '__main__':
    unittest.main()
