<?php
declare(strict_types=1);

namespace Apicore\Core;

use Apicore\Middlewares\AuthMiddleware;
use Apicore\Middlewares\CorsMiddleware;
use Apicore\Middlewares\ErrorMiddleware;
use Apicore\Middlewares\LoggingMiddleware;
use Apicore\Middlewares\Pipeline;
use Apicore\Routers\RouterRegistry;
use Apicore\Services\TokenService;
use Closure;
use ValueError;

/**
 * Composition root: settings, route table, pipeline and response emission.
 *
 * Layer: entry point (the counterpart of server.py + main.py in Python). It is
 * the only place that reads the request and writes the response; the pipeline
 * and the router stay transport-agnostic.
 */
final class Application
{
    // Written by emit() itself: a Response must not set them again.
    private const RESERVED_HEADERS = ['content-type', 'content-length'];

    private Router $router;
    /** @var Closure(Request): Response */
    private Closure $pipeline;

    public function __construct(private Settings $settings)
    {
        $this->router = new Router();
        RouterRegistry::registerAll($this->router);

        // The authenticator is the only place the pipeline learns how a token is decoded
        $authenticator = static fn (string $token): array => TokenService::decodeToken($token);

        $this->pipeline = Pipeline::build(
            [
                new CorsMiddleware($settings->CORS_ALLOW_ORIGIN),
                new ErrorMiddleware(),
                new LoggingMiddleware(),
                new AuthMiddleware($this->router, $authenticator),
            ],
            fn (Request $request): Response => $this->dispatch($request),
        );
    }

    /**
     * Configure logging and validate settings before serving.
     *
     * A misconfigured server fails immediately instead of on the first request.
     */
    public static function boot(): self
    {
        Logger::configure();
        try {
            $settings = Settings::instance();
            $settings->validate();
        } catch (ValueError $error) {
            http_response_code(500);
            header('Content-Type: application/json');
            echo json_encode(['error' => $error->getMessage()]);
            exit(1);
        }
        return new self($settings);
    }

    public function run(): void
    {
        $request = Request::fromGlobals();
        $this->emit(($this->pipeline)($request), $request->method !== 'HEAD');
    }

    /** Handle protocol-specific routes and delegate application routes to Router. */
    private function dispatch(Request $request): Response
    {
        if ($request->method === 'OPTIONS') {
            $allow = $this->router->allowHeader($request->path);
            if ($allow === null) {
                throw new AppError('Not found', 404);
            }
            return new Response(204, null, ['Allow' => $allow]);
        }

        // HEAD uses GET's route and headers, but emit() suppresses its body
        return $this->router->dispatch(
            Request::routeMethod($request->method),
            $request->path,
            $request->body(),
            $request->query,
            $request->token,
            $request->user,
        );
    }

    /** Serialize a Response and send it, mirroring the Python server's rules. */
    private function emit(Response $response, bool $sendBody): void
    {
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
            if (in_array(strtolower($name), self::RESERVED_HEADERS, true)) {
                continue;
            }
            header($name . ': ' . $value);
        }

        if ($sendBody && $body !== '') {
            echo $body;
        }
    }
}
