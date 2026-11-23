"""Health controller: liveness and database readiness probe. Stateless, no model."""
from controllers.base_controller import BaseController
from core.database import Database


class HealthController(BaseController):
    MODEL_CLASS = None

    def check(self):
        """200 when the database answers, 503 when it does not.

        A probe that ignores the database reports a dead service as healthy, so
        this one runs SELECT 1 and never lets the error escape as a 500.
        """
        database = Database()
        try:
            cursor = database.connect().cursor()
            try:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            finally:
                cursor.close()
        except Exception:
            return 503, {'status': 'error', 'message': 'Database unavailable'}
        finally:
            database.close()
        return 200, {'status': 'ok', 'message': 'Server is running'}
