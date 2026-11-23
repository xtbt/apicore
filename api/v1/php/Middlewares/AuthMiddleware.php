<?php
declare(strict_types=1);

namespace Apicore\Middlewares;

use Apicore\Core\Request;
use Apicore\Core\Response;
use Apicore\Core\Router;
use Apicore\Core\UnauthorizedError;
use Closure;

/**
 * Bearer token validation for protected routes.
 *
 * Layer: middlewares (cross-cutting). Sets request->token and request->user, so
 * the Router and the controllers never parse the Authorization header
 * themselves.
 */
final class AuthMiddleware extends Middleware
{
    /**
     * The Router owns the route table, so this layer asks it whether the route
     * is public (routePublic). The token is checked with
     * `authenticator(token): array`, injected from Core\Application so this module has
     * no model dependency.
     *
     * @param Closure(string): array $authenticator
     */
    public function __construct(
        private Router $router,
        private Closure $authenticator,
    ) {
    }

    public function handle(Request $request, Closure $next): Response
    {
        // HEAD reuses the GET route and must have the same authentication policy
        $public = $this->router->routePublic(Request::routeMethod($request->method), $request->path);
        if ($public === false) {
            // Protected route: a missing, malformed, expired or revoked token is a 401
            [$request->token, $request->user] = $this->authenticate($request->headers);
        } elseif ($public === true && isset($request->headers['authorization'])) {
            // Public route that also accepts a token (e.g. POST /users): use it when
            // valid so a privileged caller can assign roles, ignore it otherwise
            try {
                [$request->token, $request->user] = $this->authenticate($request->headers);
            } catch (UnauthorizedError) {
                // An invalid token on a public route is simply ignored
            }
        }
        // $public === null: no route for this method, the Router answers 404/405
        return $next($request);
    }

    /**
     * Validate the bearer token. Returns [raw token, payload].
     *
     * The scheme is compared case-insensitively, as RFC 7235 defines it.
     *
     * @param array<string, string> $headers
     * @return array{0: string, 1: array}
     */
    private function authenticate(array $headers): array
    {
        $header = $headers['authorization'] ?? '';
        $parts = explode(' ', $header, 2);
        $scheme = $parts[0] ?? '';
        $token = $parts[1] ?? '';
        if (strtolower($scheme) !== 'bearer' || $token === '') {
            throw new UnauthorizedError('Missing or malformed Authorization header');
        }
        return [$token, ($this->authenticator)($token)];
    }
}
