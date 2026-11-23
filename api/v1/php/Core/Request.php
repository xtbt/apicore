<?php
declare(strict_types=1);

namespace Apicore\Core;

use Closure;

/**
 * Everything one request carries while it crosses the pipeline.
 *
 * Layer: core. Request and Response only carry data; neither touches the
 * socket, so middlewares and tests can build and inspect them freely. Only
 * index.php reads the request and writes the response back to the client.
 */
final class Request
{
    public ?string $token = null;  // raw bearer token, set by AuthMiddleware
    public ?array $user = null;    // decoded token payload, set by AuthMiddleware

    /**
     * @param array<string, string> $query
     * @param array<string, string> $headers lowercase header names
     * @param Closure(): string     $readBody reads the body on demand, so a
     *                                        middleware can reject a request
     *                                        (401, 413) before it is read
     */
    public function __construct(
        public string $method,
        public string $path,
        public array $query,
        public array $headers,
        public string $clientIp,
        private Closure $readBody,
    ) {
    }

    public function body(): string
    {
        return ($this->readBody)();
    }

    /** HEAD reuses the GET route: same handler and headers, body suppressed by index.php. */
    public static function routeMethod(string $method): string
    {
        return $method === 'HEAD' ? 'GET' : $method;
    }
}
