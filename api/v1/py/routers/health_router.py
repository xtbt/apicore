"""Health routes: liveness probe (public, no database access)."""
from controllers.health_controller import HealthController


def register_routes(router):
    router.add_route('GET', '/health', HealthController,
                     lambda c, p, body: (200, c.check()), public=True)
