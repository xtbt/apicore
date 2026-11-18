"""Auth routes: login (public) and logout (requires token)."""
from controllers.AuthController import AuthController
from core.Router import json_object


def register_routes(router):
    router.add_route('POST', '/auth/login', AuthController,
                     lambda c, p, body: (200, {'status': 'ok', 'data': c.login(json_object(body))}),
                     public=True)

    def logout(c, p, body):
        c.logout()
        return 200, {'status': 'ok', 'message': 'Token revoked'}

    router.add_route('POST', '/auth/logout', AuthController, logout)
