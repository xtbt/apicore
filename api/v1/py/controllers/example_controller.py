"""Example controller: only the validation rules of the `example` entity."""
from controllers.base_controller import BaseController
from models.example import Example
from schemas import example_schema


class ExampleController(BaseController):
    MODEL_CLASS = Example
    SCHEMA = example_schema
