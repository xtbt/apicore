"""Auth routes: login (public) and logout (requires token)."""
from controllers.AuthController import AuthController
import json


def register_auth_routes(router):
    router.add_route('POST', '/auth/login', AuthController,
                     lambda c, p, body: (200, {'status': 'ok', 'data': c.login(json.loads(body))}),
                     public=True)

    def logout(c, p, body):
        c.logout()
        return 200, {'status': 'ok', 'message': 'Token revoked'}

    router.add_route('POST', '/auth/logout', AuthController, logout)
