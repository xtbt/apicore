<?php
declare(strict_types=1);

namespace Apicore\Middlewares;

use Apicore\Core\Request;
use Apicore\Core\Response;
use Closure;

/**
 * Middleware contract: subclasses override handle() and call $next($request).
 *
 * Layer: middlewares (cross-cutting). A middleware wraps the next handler, so
 * the pipeline is read outermost to innermost: cors -> error -> logging ->
 * auth -> endpoint. Every middleware and the endpoint share one signature:
 *
 *     handler(Request): Response
 *
 * Request and Response (Core\Request, Core\Response) only carry data, so no
 * middleware needs to know about sockets: only Core\Application reads the
 * request and writes the response.
 */
abstract class Middleware
{
    /** @param Closure(Request): Response $next */
    abstract public function handle(Request $request, Closure $next): Response;
}
