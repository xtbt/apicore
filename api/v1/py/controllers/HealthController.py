"""Health controller: liveness probe. Stateless, no model and no database access."""
from controllers.BaseController import BaseController


class HealthController(BaseController):
    MODEL_CLASS = None

    def check(self):
        return {'status': 'ok', 'message': 'Server is running'}
