<?php
declare(strict_types=1);

namespace Apicore\Core;

use Closure;
use ValueError;

/**
 * Router: maps HTTP method + URL pattern to a controller action.
 *
 * Layer: core (cross-cutting). It only resolves routes and builds Response
 * objects; it must never contain business logic, SQL or HTTP server code.
 */
final class Router
{
    public const MAX_PAGE_SIZE = 100;  // upper bound for ?size= on list endpoints

    /** @var list<array{0: string, 1: string, 2: Closure, 3: class-string, 4: bool}> */
    private array $routes = [];

    /**
     * Register a route.
     *
     * pattern: e.g. '/moods/{id}'; each {name} becomes a path parameter.
     * handler: function(controller, params, body): Response.
     * public: false (default) requires a valid "Authorization: Bearer <token>".
     */
    public function addRoute(
        string $method,
        string $pattern,
        string $controllerClass,
        Closure $handler,
        bool $public = false,
    ): void {
        $regex = preg_replace('/\{(\w+)\}/', '(?P<$1>[^/]+)', $pattern);
        $this->routes[] = [$method, '#^' . $regex . '$#', $handler, $controllerClass, $public];
    }

    /**
     * Register the 6 standard CRUD routes (PUT = full payload, PATCH = partial)
     * of an entity, reusable by any entity.
     *
     * public: makes all routes public. publicMethods: HTTP methods made public
     * individually (e.g. ['POST'] for a self-registration endpoint).
     *
     * @param list<string> $publicMethods
     */
    public function addCrudRoutes(
        string $path,
        string $controllerClass,
        string $label,
        bool $public = false,
        array $publicMethods = [],
    ): void {
        $item = $path . '/{id}';
        $notFound = static fn (): Response => Response::error(404, $label . ' not found');

        $listAll = static function ($controller, array $params, string $body): Response {
            $query = $controller->query ?? [];
            $page = self::positiveInt($query, 'page');
            $size = self::positiveInt($query, 'size');
            if ($size > self::MAX_PAGE_SIZE) {
                throw new ValueError('size must be ' . self::MAX_PAGE_SIZE . ' or less');
            }
            return new Response(200, [
                'status' => 'ok',
                'data' => $controller->getAll($page ?: null, $size ?: null),
            ]);
        };

        $getOne = static function ($controller, array $params, string $body) use ($notFound): Response {
            $element = $controller->getById($params['id']);
            return $element ? new Response(200, ['status' => 'ok', 'data' => $element]) : $notFound();
        };

        $create = static function ($controller, array $params, string $body) use ($path): Response {
            $recordId = $controller->create(self::jsonObject($body));
            return new Response(
                201,
                ['status' => 'ok', 'ID' => $recordId],
                ['Location' => $path . '/' . $recordId],
            );
        };

        $updateWith = static function (string $action) use ($label, $notFound): Closure {
            return static function ($controller, array $params, string $body) use ($action, $label, $notFound): Response {
                $result = $controller->{$action}($params['id'], self::jsonObject($body));
                if ($result === $controller::NOT_FOUND) {
                    return $notFound();
                }
                if ($result === $controller::UNCHANGED) {
                    return new Response(200, ['status' => 'ok', 'message' => 'No changes to apply']);
                }
                if ($result === $controller::UPDATED) {
                    return new Response(200, ['status' => 'ok', 'message' => $label . ' updated']);
                }
                throw new ValueError('Unexpected update result: ' . var_export($result, true));
            };
        };

        $delete = static function ($controller, array $params, string $body) use ($label, $notFound): Response {
            if ($controller->delete($params['id'])) {
                return new Response(200, ['status' => 'ok', 'message' => $label . ' deleted']);
            }
            return $notFound();
        };

        $this->addRoute('GET', $path, $controllerClass, $listAll, $public || in_array('GET', $publicMethods, true));
        $this->addRoute('GET', $item, $controllerClass, $getOne, $public || in_array('GET', $publicMethods, true));
        $this->addRoute('POST', $path, $controllerClass, $create, $public || in_array('POST', $publicMethods, true));
        $this->addRoute('PUT', $item, $controllerClass, $updateWith('update'), $public || in_array('PUT', $publicMethods, true));
        $this->addRoute('PATCH', $item, $controllerClass, $updateWith('patch'), $public || in_array('PATCH', $publicMethods, true));
        $this->addRoute('DELETE', $item, $controllerClass, $delete, $public || in_array('DELETE', $publicMethods, true));
    }

    /** Parse the request body: it must be a JSON object. */
    public static function jsonObject(string $body): array
    {
        $decoded = json_decode($body, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new ValueError('Body must be valid JSON');
        }
        if (!is_array($decoded) || !str_starts_with(ltrim($body), '{')) {
            throw new ValueError('Body must be a JSON object');
        }
        return $decoded;
    }

    /**
     * Parse an optional positive integer query parameter (0 when absent).
     *
     * Raises ValueError with a generic message, so no interpreter detail leaks.
     *
     * @param array<string, mixed> $query
     */
    public static function positiveInt(array $query, string $name): int
    {
        $raw = $query[$name] ?? null;
        if (is_array($raw)) {
            $raw = $raw[0] ?? null;
        }
        if ($raw === null || $raw === '') {
            return 0;
        }
        $trimmed = trim((string) $raw);
        if (!preg_match('/^[+-]?\d+$/', $trimmed)) {
            throw new ValueError($name . ' must be a positive integer');
        }
        $value = (int) $trimmed;
        if ($value < 1) {
            throw new ValueError($name . ' must be a positive integer');
        }
        return $value;
    }

    /**
     * Routes whose pattern matches $path (any method).
     *
     * @return list<array{0: string, 1: string, 2: Closure, 3: class-string, 4: bool}>
     */
    private function matching(string $path): array
    {
        return array_values(array_filter(
            $this->routes,
            static fn (array $route): bool => preg_match($route[1], $path) === 1,
        ));
    }

    /** Return route visibility, or null if this method/path has no route. */
    public function routePublic(string $method, string $path): ?bool
    {
        foreach ($this->matching($path) as $route) {
            if ($route[0] === $method) {
                return $route[4];
            }
        }
        return null;
    }

    /**
     * HTTP methods registered for $path (empty list when no pattern matches).
     *
     * @return list<string>
     */
    public function allowedMethods(string $path): array
    {
        return array_map(static fn (array $route): string => $route[0], $this->matching($path));
    }

    /** Value for the Allow header of $path, or null when no route matches. */
    public function allowHeader(string $path): ?string
    {
        $allowed = $this->allowedMethods($path);
        if ($allowed === []) {
            return null;
        }
        $methods = array_unique([...$allowed, 'HEAD', 'OPTIONS']);
        sort($methods);
        return implode(', ', $methods);
    }

    /**
     * Run the matching route with auth context supplied by middleware.
     *
     * 404 if no pattern matches the path; 405 if the path exists but not for
     * that method. A controller (and its DB connection) is created per request.
     *
     * @param array<string, mixed> $query
     */
    public function dispatch(
        string $method,
        string $path,
        string $body,
        array $query = [],
        ?string $token = null,
        ?array $user = null,
    ): Response {
        $pathFound = false;
        foreach ($this->routes as [$routeMethod, $regex, $handler, $controllerClass, $public]) {
            if (preg_match($regex, $path, $matches) !== 1) {
                continue;
            }
            $pathFound = true;
            if ($routeMethod !== $method) {
                continue;
            }
            $controller = new $controllerClass();
            $controller->authToken = $token;
            $controller->authUser = $user;
            $controller->query = $query;
            try {
                $params = array_filter($matches, 'is_string', ARRAY_FILTER_USE_KEY);
                return $handler($controller, $params, $body);
            } finally {
                $controller->close();
            }
        }
        if ($pathFound) {
            return Response::error(405, 'Method not allowed');
        }
        return Response::error(404, 'Not found');
    }
}
