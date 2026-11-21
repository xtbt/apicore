"""Unit tests for generic controller-to-schema delegation."""
import unittest
from unittest.mock import Mock

from controllers.base_controller import BaseController


class TestBaseControllerSchema(unittest.TestCase):
    def test_validate_delegates_payload_and_partial_flag_to_schema(self):
        schema = Mock()

        class EntityController(BaseController):
            SCHEMA = schema

        controller = EntityController()
        data = {'Name': 'Example'}
        controller.validate(data, partial=True)
        schema.validate.assert_called_once_with(data, True)

    def test_validate_without_schema_is_a_noop(self):
        controller = BaseController()
        controller.validate({'anything': True})


if __name__ == '__main__':
    unittest.main()
