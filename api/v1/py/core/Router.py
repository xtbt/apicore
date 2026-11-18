"""Router: maps HTTP method + URL pattern to a controller action.

Layer: core (cross-cutting). It only resolves routes and builds (status, payload) pairs;
it must never contain business logic, SQL or HTTP server code.
"""
import json
import re

from core.Exceptions import UnauthorizedError

MAX_PAGE_SIZE = 100  # upper bound for ?size= on list endpoints


def json_object(body):
    """Parse the request body: it must be a JSON object (dict)."""
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError('Body must be a JSON object')
    return data


def positive_int(query, name):
    """Parse an optional positive integer query parameter (0 when absent).

    Raises ValueError with a generic message, so no interpreter detail leaks.
    """
    raw = query.get(name)
    if raw is None or raw == '':
        return 0
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f'{name} must be a positive integer')
    if value < 1:
        raise ValueError(f'{name} must be a positive integer')
    return value


class Router:
    def __init__(self, authenticator=None):
        # Each route: (method, compiled regex, handler, controller class, public)
        self.routes = []
        # authenticator(token) -> payload of a verified, non-revoked, Active user;
        # injected from main.py, so this module has no model dependency
        self.authenticator = authenticator

    def add_route(self, method, pattern, controller_class, handler, public=False):
        """Register a route.

        pattern: e.g. '/moods/{id}'; each {name} becomes a path parameter.
        handler: function(controller, params, body) -> (status, payload).
        public: False (default) requires a valid "Authorization: Bearer <token>".
        """
        regex = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern)
        self.routes.append((method, re.compile(f'^{regex}$'), handler, controller_class, public))

    def add_crud_routes(self, path, controller_class, label, public=False, public_methods=()):
        """Register the 6 standard CRUD routes (PUT = full payload, PATCH = partial) of an entity (reusable by any entity).

        public: makes all routes public. public_methods: HTTP methods made public
        individually (e.g. ("POST",) for a self-registration endpoint).
        """
        item = f'{path}/{{id}}'
        not_found = (404, {'error': f'{label} not found'})

        def list_all(c, p, body):
            query = c.query or {}
            page, size = positive_int(query, 'page'), positive_int(query, 'size')
            if size > MAX_PAGE_SIZE:
                raise ValueError(f'size must be {MAX_PAGE_SIZE} or less')
            return 200, {'status': 'ok', 'data': c.get_all(page or None, size or None)}

        def get_one(c, p, body):
            element = c.get_by_id(p['id'])
            return (200, {'status': 'ok', 'data': element}) if element else not_found

        def create(c, p, body):
            return 200, {'status': 'ok', 'ID': c.create(json_object(body))}

        def update_with(action):
            def handler(c, p, body):
                return update_result(c, action(c, p['id'], json_object(body)))
            return handler

        def update_result(c, result):
            if result == c.model.NOT_FOUND:
                return not_found
            if result == c.model.UNCHANGED:
                return 200, {'status': 'ok', 'message': 'No changes to apply'}
            return 200, {'status': 'ok', 'message': f'{label} updated'}

        def delete(c, p, body):
            if c.delete(p['id']):
                return 200, {'status': 'ok', 'message': f'{label} deleted'}
            return not_found

        self.add_route('GET', path, controller_class, list_all,
                       public or 'GET' in public_methods)
        self.add_route('GET', item, controller_class, get_one,
                       public or 'GET' in public_methods)
        self.add_route('POST', path, controller_class, create,
                       public or 'POST' in public_methods)
        self.add_route('PUT', item, controller_class,
                       update_with(lambda c, i, d: c.update(i, d)),
                       public or 'PUT' in public_methods)
        self.add_route('PATCH', item, controller_class,
                       update_with(lambda c, i, d: c.patch(i, d)),
                       public or 'PATCH' in public_methods)
        self.add_route('DELETE', item, controller_class, delete,
                       public or 'DELETE' in public_methods)

    def _authenticate(self, headers):
        """Validate the bearer token of a protected route. Returns (raw_token, payload).

        The scheme is compared case-insensitively, as RFC 7235 defines it.
        """
        scheme, _, token = headers.get('Authorization', '').partition(' ')
        if scheme.lower() != 'bearer' or not token:
            raise UnauthorizedError('Missing or malformed Authorization header')
        return token, self.authenticator(token)

    def allowed_methods(self, path):
        """HTTP methods registered for `path` (empty list when no pattern matches)."""
        return [method for method, regex, _h, _c, _p in self.routes if regex.match(path)]

    def dispatch(self, method, path, body, headers, query=None):
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
            token = payload = None
            if not public:
                token, payload = self._authenticate(headers)
            elif headers.get('Authorization'):
                # Public route that also accepts a token (e.g. POST /users): use it
                # when valid so a privileged caller can assign roles, ignore it otherwise
                try:
                    token, payload = self._authenticate(headers)
                except UnauthorizedError:
                    pass
            controller = controller_class()
            controller.auth_token = token
            controller.auth_user = payload
            controller.query = query
            try:
                return handler(controller, match.groupdict(), body)
            finally:
                controller.close()
        if path_found:
            return 405, {'error': 'Method not allowed'}
        return 404, {'error': 'Not found'}
