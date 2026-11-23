<?php
declare(strict_types=1);

namespace Apicore\Tests;

use Apicore\Core\Request;
use Apicore\Core\Response;
use Apicore\Core\Router;
use Apicore\Core\UnauthorizedError;
use Apicore\Middlewares\AuthMiddleware;
use Apicore\Middlewares\CorsMiddleware;
use Apicore\Middlewares\LoggingMiddleware;

/** Middlewares: CORS headers, bearer parsing and the logging pass-through. */
final class MiddlewaresTest extends TestCase
{
    /** @param array<string, string> $headers */
    private function request(string $method, string $path, array $headers = []): Request
    {
        return new Request($method, $path, [], $headers, '127.0.0.1', static fn (): string => '');
    }

    private function router(): Router
    {
        $router = new Router();
        $router->addRoute('GET', '/private', RouterTestController::class, static fn () => new Response(200, ['ok' => true]));
        $router->addRoute('POST', '/public', RouterTestController::class, static fn () => new Response(201, ['ok' => true]), true);
        return $router;
    }

    public function testCorsAddsHeaders(): void
    {
        $middleware = new CorsMiddleware('*');
        $response = $middleware->handle($this->request('GET', '/x'), static fn () => new Response(200, []));
        $this->assertSame('*', $response->headers['Access-Control-Allow-Origin']);
        $this->assertContains('Authorization', explode(', ', $response->headers['Access-Control-Allow-Headers']));
        $this->assertFalse(isset($response->headers['Vary']));
    }

    public function testCorsAddsVaryForFixedOrigin(): void
    {
        $middleware = new CorsMiddleware('https://app.test');
        $response = $middleware->handle($this->request('GET', '/x'), static fn () => new Response(200, []));
        $this->assertSame('Origin', $response->headers['Vary']);
    }

    public function testAuthRejectsMissingHeader(): void
    {
        $middleware = new AuthMiddleware($this->router(), static fn (string $t): array => ['sub' => 1]);
        $this->assertThrows(
            UnauthorizedError::class,
            fn () => $middleware->handle($this->request('GET', '/private'), static fn () => new Response(200, [])),
        );
    }

    public function testAuthRejectsMalformedHeader(): void
    {
        $middleware = new AuthMiddleware($this->router(), static fn (string $t): array => ['sub' => 1]);
        $this->assertThrows(
            UnauthorizedError::class,
            fn () => $middleware->handle(
                $this->request('GET', '/private', ['authorization' => 'Token abc']),
                static fn () => new Response(200, []),
            ),
        );
    }

    public function testAuthAcceptsBearerCaseInsensitively(): void
    {
        $middleware = new AuthMiddleware($this->router(), static fn (string $t): array => ['sub' => 7]);
        $request = $this->request('GET', '/private', ['authorization' => 'bearer abc']);
        $response = $middleware->handle($request, static fn () => new Response(200, []));
        $this->assertSame(200, $response->status);
        $this->assertSame('abc', $request->token);
        $this->assertSame(['sub' => 7], $request->user);
    }

    public function testAuthIgnoresInvalidTokenOnPublicRoute(): void
    {
        $middleware = new AuthMiddleware($this->router(), static function (string $t): array {
            throw new UnauthorizedError('bad token');
        });
        $request = $this->request('POST', '/public', ['authorization' => 'Bearer bad']);
        $response = $middleware->handle($request, static fn () => new Response(201, []));
        $this->assertSame(201, $response->status);
        $this->assertNull($request->user);
    }

    public function testAuthLetsUnknownRouteThrough(): void
    {
        $middleware = new AuthMiddleware($this->router(), static fn (string $t): array => ['sub' => 1]);
        $response = $middleware->handle($this->request('GET', '/nope'), static fn () => new Response(404, []));
        $this->assertSame(404, $response->status);
    }

    public function testLoggingReturnsTheInnerResponse(): void
    {
        $middleware = new LoggingMiddleware();
        $response = $middleware->handle($this->request('GET', '/x'), static fn () => new Response(204, null));
        $this->assertSame(204, $response->status);
    }

    public function testLoggingRethrowsAndKeepsStatus(): void
    {
        $middleware = new LoggingMiddleware();
        $this->assertThrows(
            UnauthorizedError::class,
            fn () => $middleware->handle(
                $this->request('GET', '/x'),
                static function (): Response {
                    throw new UnauthorizedError('nope');
                },
            ),
        );
    }
}
