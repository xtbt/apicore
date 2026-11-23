<?php
declare(strict_types=1);

namespace Apicore\Middlewares;

use Apicore\Core\Request;
use Apicore\Core\Response;
use Closure;

/**
 * Chain middlewares around the endpoint.
 *
 * Layer: middlewares (cross-cutting). The first item of the list is the
 * outermost layer, so it sees the request first and the response last.
 */
final class Pipeline
{
    /**
     * @param list<Middleware>          $middlewares
     * @param Closure(Request): Response $endpoint
     * @return Closure(Request): Response
     */
    public static function build(array $middlewares, Closure $endpoint): Closure
    {
        $next = $endpoint;
        foreach (array_reverse($middlewares) as $middleware) {
            $inner = $next;
            $next = static fn (Request $request): Response => $middleware->handle($request, $inner);
        }
        return $next;
    }
}
