"""Router: maps HTTP method + URL pattern to a controller action.

Layer: core (cross-cutting). It only resolves routes and builds (status, payload) pairs;
it must never contain business logic, SQL or HTTP server code.
"""
import json
import re

from core.Exceptions import UnauthorizedError
from core.Security import decode_token


class Router:
    def __init__(self):
        # Each route: (method, compiled regex, handler, controller class, public)
        self.routes = []

    def add_route(self, method, pattern, controller_class, handler, public=False):
        """Register a route.

        pattern: e.g. '/moods/{id}'; each {name} becomes a path parameter.
        handler: function(controller, params, body) -> (status, payload).
        public: False (default) requires a valid "Authorization: Bearer <token>".
        """
        regex = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern)
        self.routes.append((method, re.compile(f'^{regex}$'), handler, controller_class, public))

    def add_crud_routes(self, path, controller_class, label, public=False, public_methods=()):
        """Register the 5 standard CRUD routes of an entity (reusable by any entity).

        public: makes all 5 routes public. public_methods: HTTP methods made public
        individually (e.g. ("POST",) for a self-registration endpoint).
        """
        item = f'{path}/{{id}}'
        not_found = (404, {'error': f'{label} not found'})

        def list_all(c, p, body):
            return 200, {'status': 'ok', 'data': c.get_all()}

        def get_one(c, p, body):
            element = c.get_by_id(p['id'])
            return (200, {'status': 'ok', 'data': element}) if element else not_found

        def create(c, p, body):
            return 200, {'status': 'ok', 'ID': c.create(json.loads(body))}

        def update(c, p, body):
            result = c.update(p['id'], json.loads(body))
            if result == c.model.NOT_FOUND:
                return not_found
            if result == c.model.UNCHANGED:
                return 200, {'status': 'ok', 'message': 'No changes to apply'}
            return 200, {'status': 'ok', 'message': f'{label} updated'}

        def delete(c, p, body):
            if c.delete(p['id']):
                return 200, {'status': 'ok', 'message': f'{label} deleted'}
            return not_found

        self.add_route('GET', path, controller_class, list_all, public or 'GET' in public_methods)
        self.add_route('GET', item, controller_class, get_one, public or 'GET' in public_methods)
        self.add_route('POST', path, controller_class, create, public or 'POST' in public_methods)
        self.add_route('PUT', item, controller_class, update, public or 'PUT' in public_methods)
        self.add_route('DELETE', item, controller_class, delete, public or 'DELETE' in public_methods)

    @staticmethod
    def _authenticate(headers):
        """Validate the bearer token of a protected route and return it (401 otherwise)."""
        scheme, _, token = headers.get('Authorization', '').partition(' ')
        if scheme != 'Bearer' or not token:
            raise UnauthorizedError('Missing or malformed Authorization header')
        decode_token(token)
        return token

    def dispatch(self, method, path, body, headers):
        """Run the matching route. Returns (status, payload).

        404 if no pattern matches the path; 405 if the path exists but not for
        that method. A controller (and its DB connection) is created per request.
        """
        path_found = False
        for route_method, regex, handler, controller_class, public in self.routes:
            match = regex.match(path)
            if not match:
                continue
            path_found = True
            if route_method != method:
                continue
            token = None if public else self._authenticate(headers)
            controller = controller_class()
            controller.auth_token = token
            try:
                return handler(controller, match.groupdict(), body)
            finally:
                controller.close()
        if path_found:
            return 405, {'error': 'Method not allowed'}
        return 404, {'error': 'Not found'}
