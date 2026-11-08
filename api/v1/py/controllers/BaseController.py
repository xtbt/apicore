from models.BaseModel import BaseModel

class BaseController:
    def __init__(self):
        self.model = BaseModel()

    def create(self, data):
        self._validate(data)
        return self.model.create(data)

    def get_all(self, table):
        return self.model.get_all(self.model, table)

    def get_by_id(self, table, record_id):
        return self.model.get_by_id(self.model, table, record_id)

    def modify(self, mood_id, data):
        self._validate(data)
        self.model.modify(mood_id, data)

    def delete(self, mood_id):
        self.model.delete(mood_id)