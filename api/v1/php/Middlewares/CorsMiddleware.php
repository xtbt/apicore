<?php
declare(strict_types=1);

namespace Apicore\Middlewares;

use Apicore\Core\Request;
use Apicore\Core\Response;
use Apicore\Core\Settings;
use Closure;

/**
 * CORS headers for browser clients.
 *
 * Layer: middlewares (cross-cutting). Outermost layer, so the headers are added
 * to every response, including the ones produced by ErrorMiddleware. It never
 * rejects a request: the browser is the one that enforces the policy.
 */
final class CorsMiddleware extends Middleware
{
    private const ALLOWED_METHODS = 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS';
    private const ALLOWED_HEADERS = 'Authorization, Content-Type';
    private const MAX_AGE_SECONDS = '600';

    public function __construct(private ?string $allowOrigin = null)
    {
        $this->allowOrigin ??= Settings::instance()->CORS_ALLOW_ORIGIN;
    }

    public function handle(Request $request, Closure $next): Response
    {
        $response = $next($request);
        $response->headers['Access-Control-Allow-Origin'] = $this->allowOrigin;
        $response->headers['Access-Control-Allow-Methods'] = self::ALLOWED_METHODS;
        $response->headers['Access-Control-Allow-Headers'] = self::ALLOWED_HEADERS;
        $response->headers['Access-Control-Max-Age'] = self::MAX_AGE_SECONDS;
        if ($this->allowOrigin !== '*') {
            // The response depends on the caller's Origin, so caches must not share it
            $response->headers['Vary'] = 'Origin';
        }
        return $response;
    }
}
