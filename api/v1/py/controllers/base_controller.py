"""Base controller: generic CRUD flow shared by every entity.

Layer: controllers. Entity controllers only set MODEL_CLASS and override
validate() / prepare(). It must never contain SQL.
"""


class BaseController:
    MODEL_CLASS = None  # Model class of the entity (set by subclasses)
    auth_token = None   # Raw bearer token of the current request (set by the Router on protected routes)
    auth_user = None    # Decoded payload of that token (None on public routes)
    query = None        # Query-string parameters of the current request (?page=1&size=10)

    def __init__(self):
        # A stateless controller (e.g. health check) declares MODEL_CLASS = None
        self.model = self.MODEL_CLASS() if self.MODEL_CLASS else None

    def close(self):
        """Release the model resources."""
        if self.model is not None:
            self.model.close()

    def validate(self, data, partial=False):
        """Hook for entity rules. Raise ValueError when `data` is invalid.

        partial=True (PATCH): only the fields present in `data` are checked.
        Entity controllers delegate to their schema in schemas/.
        """

    def prepare(self, data, record_id=None):
        """Hook run after validate(): transform `data` before it is stored (record_id is None on create)."""
        return data

    def authorize(self, record_id, action, data=None):
        """Hook for ownership rules. Raise ForbiddenError when the caller may not touch the record.

        action is 'update' (PUT/PATCH) or 'delete'; `data` holds the fields being
        written on update. Runs before any write, so a refused request never
        changes data.
        """

    def create(self, data):
        self.validate(data)
        return self.model.create(self.prepare(data))

    def get_all(self, page=None, size=None):
        return self.model.get_all(page, size)

    def get_by_id(self, record_id):
        return self.model.get_by_id(record_id)

    def update(self, record_id, data):
        self.authorize(record_id, 'update', data)
        self.validate(data)
        return self.model.update(record_id, self.prepare(data, record_id))

    def patch(self, record_id, data):
        """Partial update: only the fields sent are validated and written."""
        self.authorize(record_id, 'update', data)
        self.validate(data, partial=True)
        return self.model.update(record_id, self.prepare(data, record_id))

    def delete(self, record_id):
        self.authorize(record_id, 'delete')
        return self.model.delete(record_id)
