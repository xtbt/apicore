"""Base controller: generic CRUD flow shared by every entity.

Layer: controllers. Entity controllers only set MODEL_CLASS and override
validate(). It must never contain SQL.
"""


class BaseController:
    MODEL_CLASS = None  # Model class of the entity (set by subclasses)

    def __init__(self):
        self.model = self.MODEL_CLASS()

    def close(self):
        """Release the model resources."""
        self.model.close()

    def validate(self, data):
        """Hook for entity rules. Raise ValueError when `data` is invalid."""

    def create(self, data):
        self.validate(data)
        return self.model.create(data)

    def get_all(self):
        return self.model.get_all()

    def get_by_id(self, record_id):
        return self.model.get_by_id(record_id)

    def update(self, record_id, data):
        self.validate(data)
        return self.model.update(record_id, data)

    def delete(self, record_id):
        return self.model.delete(record_id)
