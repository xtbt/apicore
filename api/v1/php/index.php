<?php
declare(strict_types=1);

/**
 * Front controller: the only file the PHP built-in server executes.
 *
 * Layer: entry point (the counterpart of server.py + main.py in Python). It
 * reads the request, runs the middleware pipeline and writes the JSON response;
 * the pipeline and the router stay transport-agnostic.
 *
 * Start it with:  php -S localhost:8000 index.php
 */

use Apicore\Core\AppError;
use Apicore\Core\Logger;
use Apicore\Core\PayloadTooLargeError;
use Apicore\Core\Request;
use Apicore\Core\Response;
use Apicore\Core\Router;
use Apicore\Core\Settings;
use Apicore\Middlewares\AuthMiddleware;
use Apicore\Middlewares\CorsMiddleware;
use Apicore\Middlewares\ErrorMiddleware;
use Apicore\Middlewares\LoggingMiddleware;
use Apicore\Middlewares\Pipeline;
use Apicore\Routers\AuthRouter;
use Apicore\Routers\HealthRouter;
use Apicore\Services\TokenService;

require __DIR__ . '/Core/Autoloader.php';

const MAX_BODY_BYTES = 1024 * 1024;  // 1 MB cap for request bodies

// Written by emit() itself: a Response must not set them again.
const RESERVED_HEADERS = ['content-type', 'content-length'];

Logger::configure();

try {
    $settings = Settings::instance();
    $settings->validate();
} catch (ValueError $error) {
    // A misconfigured server fails immediately instead of on the first request
    http_response_code(500);
    header('Content-Type: application/json');
    echo json_encode(['error' => $error->getMessage()]);
    exit(1);
}

/** Request headers with lowercase names (the pipeline never guesses the case). */
$headers = static function (): array {
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
};

/**
 * Read the request body, rejecting an invalid or oversized Content-Length.
 *
 * It is a closure so a middleware can reject a request (401, 413) before the
 * body is read.
 */
$readBody = static function (): string {
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
    if ($length > MAX_BODY_BYTES) {
        throw new PayloadTooLargeError('Request body too large');
    }
    $body = (string) file_get_contents('php://input');
    if ($body !== '' && !mb_check_encoding($body, 'UTF-8')) {
        throw new AppError('Request body must be UTF-8', 400);
    }
    return $body;
};

/** Serialize a Response and send it, mirroring the Python server's rules. */
$emit = static function (Response $response, bool $sendBody): void {
    http_response_code($response->status);
    header_remove('X-Powered-By');

    $body = '';
    if ($response->status !== 204 && $response->payload !== null) {
        $body = (string) json_encode(
            $response->payload,
            JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE,
        );
    }

    if ($response->status === 204) {
        // A 204 carries no body, so RFC 7230 forbids Content-Length and Content-Type
        ini_set('default_mimetype', '');
        header_remove('Content-Type');
    } else {
        header('Content-Type: application/json');
        header('Content-Length: ' . strlen($body));
    }

    foreach ($response->headers as $name => $value) {
        if (in_array(strtolower($name), RESERVED_HEADERS, true)) {
            continue;
        }
        header($name . ': ' . $value);
    }

    if ($sendBody && $body !== '') {
        echo $body;
    }
};

// Route table shared by all requests; routers are discovered from the package.
$router = new Router();
HealthRouter::register($router);
AuthRouter::register($router);

/**
 * Handle protocol-specific routes and delegate application routes to Router.
 */
$dispatch = static function (Request $request) use ($router): Response {
    if ($request->method === 'OPTIONS') {
        $allow = $router->allowHeader($request->path);
        if ($allow === null) {
            throw new AppError('Not found', 404);
        }
        return new Response(204, null, ['Allow' => $allow]);
    }

    // HEAD uses GET's route and headers, but $emit suppresses its body
    return $router->dispatch(
        Request::routeMethod($request->method),
        $request->path,
        $request->body(),
        $request->query,
        $request->token,
        $request->user,
    );
};

// The authenticator is the only place the pipeline learns how a token is decoded
$authenticator = static fn (string $token): array => TokenService::decodeToken($token);

$pipeline = Pipeline::build(
    [
        new CorsMiddleware($settings->CORS_ALLOW_ORIGIN),
        new ErrorMiddleware(),
        new LoggingMiddleware(),
        new AuthMiddleware($router, $authenticator),
    ],
    $dispatch,
);

$request = new Request(
    (string) ($_SERVER['REQUEST_METHOD'] ?? 'GET'),
    (string) (parse_url((string) ($_SERVER['REQUEST_URI'] ?? '/'), PHP_URL_PATH) ?: '/'),
    $_GET,
    $headers(),
    (string) ($_SERVER['REMOTE_ADDR'] ?? '0.0.0.0'),
    $readBody,
);

$emit($pipeline($request), $request->method !== 'HEAD');
