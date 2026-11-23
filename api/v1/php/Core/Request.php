<?php
declare(strict_types=1);

namespace Apicore\Core;

use Closure;

/**
 * Everything one request carries while it crosses the pipeline.
 *
 * Layer: core. Request and Response only carry data; neither touches the
 * socket, so middlewares and tests can build and inspect them freely. Only
 * Core\Application reads the request and writes the response back to the client.
 */
final class Request
{
    /** 1 MB cap for request bodies, the same limit as the Python server. */
    public const MAX_BODY_BYTES = 1024 * 1024;

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

    /**
     * Build the request from the PHP superglobals.
     *
     * The body is passed as a closure, so a middleware can reject a request
     * (401, 413) before it is read.
     */
    public static function fromGlobals(): self
    {
        return new self(
            (string) ($_SERVER['REQUEST_METHOD'] ?? 'GET'),
            (string) (parse_url((string) ($_SERVER['REQUEST_URI'] ?? '/'), PHP_URL_PATH) ?: '/'),
            $_GET,
            self::headersFromGlobals(),
            (string) ($_SERVER['REMOTE_ADDR'] ?? '0.0.0.0'),
            static fn (): string => self::readBodyFromGlobals(),
        );
    }

    /** Request headers with lowercase names (the pipeline never guesses the case). */
    private static function headersFromGlobals(): array
    {
        $collected = [];
        foreach ($_SERVER as $key => $value) {
            if (str_starts_with($key, 'HTTP_')) {
                $collected[strtolower(str_replace('_', '-', substr($key, 5)))] = (string) $value;
            }
        }
        if (isset($_SERVER['CONTENT_TYPE'])) {
            $collected['content-type'] = (string) $_SERVER['CONTENT_TYPE'];
        }
        if (isset($_SERVER['CONTENT_LENGTH'])) {
            $collected['content-length'] = (string) $_SERVER['CONTENT_LENGTH'];
        }
        return $collected;
    }

    /** Read the body, rejecting an invalid or oversized Content-Length. */
    private static function readBodyFromGlobals(): string
    {
        $raw = (string) ($_SERVER['CONTENT_LENGTH'] ?? '');
        if ($raw === '') {
            $length = 0;
        } elseif (preg_match('/^-?\d+$/', $raw) !== 1) {
            throw new AppError('Invalid Content-Length header', 400);
        } else {
            $length = (int) $raw;
        }
        if ($length < 0) {
            throw new AppError('Invalid Content-Length header', 400);
        }
        if ($length > self::MAX_BODY_BYTES) {
            throw new PayloadTooLargeError('Request body too large');
        }
        $body = (string) file_get_contents('php://input');
        if ($body !== '' && !mb_check_encoding($body, 'UTF-8')) {
            throw new AppError('Request body must be UTF-8', 400);
        }
        return $body;
    }

    /** HEAD reuses the GET route: same handler and headers, body suppressed by Core\Application. */
    public static function routeMethod(string $method): string
    {
        return $method === 'HEAD' ? 'GET' : $method;
    }
}
