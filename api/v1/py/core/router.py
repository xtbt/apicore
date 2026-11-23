"""Router: maps HTTP method + URL pattern to a controller action.

Layer: core (cross-cutting). It only resolves routes and builds (status, payload) pairs;
it must never contain business logic, SQL or HTTP server code.
"""
import json
import re

from core.http import Response

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
            record_id = c.create(json_object(body))
            return Response(201, {'status': 'ok', 'ID': record_id},
                            {'Location': f'{path}/{record_id}'})

        def update_with(action):
            def handler(c, p, body):
                return update_result(c, getattr(c, action)(p['id'], json_object(body)))
            return handler

        def update_result(c, result):
            if result == c.NOT_FOUND:
                return not_found
            if result == c.UNCHANGED:
                return 200, {'status': 'ok', 'message': 'No changes to apply'}
            if result == c.UPDATED:
                return 200, {'status': 'ok', 'message': f'{label} updated'}
            raise ValueError(f'Unexpected update result: {result!r}')

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
                       update_with('update'),
                       public or 'PUT' in public_methods)
        self.add_route('PATCH', item, controller_class,
                       update_with('patch'),
                       public or 'PATCH' in public_methods)
        self.add_route('DELETE', item, controller_class, delete,
                       public or 'DELETE' in public_methods)

    def _matching(self, path):
        """Routes whose pattern matches `path` (any method)."""
        return [route for route in self.routes if route[1].match(path)]

    def route_public(self, method, path):
        """Return route visibility, or None if this method/path has no route."""
        for route_method, _regex, _handler, _controller, public in self._matching(path):
            if route_method == method:
                return public
        return None

    def allowed_methods(self, path):
        """HTTP methods registered for `path` (empty list when no pattern matches)."""
        return [route[0] for route in self._matching(path)]

    def allow_header(self, path):
        """Value for the Allow header of `path`, or None when no route matches."""
        allowed = self.allowed_methods(path)
        if not allowed:
            return None
        return ', '.join(sorted(set(allowed) | {'HEAD', 'OPTIONS'}))

    def dispatch(self, method, path, body, query=None, token=None, user=None):
        """Run the matching route with auth context supplied by middleware.

        Returns what the handler returns: a (status, payload) pair, or a Response
        when the handler needs its own headers (POST returns 201 + Location).
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
            controller = controller_class()
            controller.auth_token = token
            controller.auth_user = user
            controller.query = query
            try:
                return handler(controller, match.groupdict(), body)
            finally:
                controller.close()
        if path_found:
            return 405, {'error': 'Method not allowed'}
        return 404, {'error': 'Not found'}
