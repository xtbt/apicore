"""Bearer token validation for protected routes.

Layer: middlewares (cross-cutting). Sets request.token and request.user, so the
Router and the controllers never parse the Authorization header themselves.
"""
from core.exceptions import UnauthorizedError
from middlewares.base import Middleware


class AuthMiddleware(Middleware):
    """Requires a valid token on protected routes and ignores it on public ones.

    The Router owns the route table, so this layer asks it whether the route is
    public (route_public) and delegates the token check (authenticate).
    """

    def __init__(self, router):
        self.router = router

    def handle(self, request, call_next):
        # HEAD reuses the GET route and must have the same authentication policy.
        method = 'GET' if request.method == 'HEAD' else request.method
        public = self.router.route_public(method, request.path)
        if public is False:
            # Protected route: a missing, malformed, expired or revoked token is a 401
            request.token, request.user = self.router.authenticate(request.headers)
        elif public is True and request.headers.get('Authorization'):
            # Public route that also accepts a token (e.g. POST /users): use it when
            # valid so a privileged caller can assign roles, ignore it otherwise
            try:
                request.token, request.user = self.router.authenticate(request.headers)
            except UnauthorizedError:
                pass
        # public is None: no route for this method, the Router answers 404/405
        # TODO: require_role(*roles) hook for role-based authorization (stage 10).
        return call_next(request)
