"""Health routes: liveness and database readiness probe (public)."""
from controllers.health_controller import HealthController


def register_routes(router):
    router.add_route('GET', '/health', HealthController,
                     lambda c, p, body: c.check(), public=True)
