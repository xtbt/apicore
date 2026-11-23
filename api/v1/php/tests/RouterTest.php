<?php
declare(strict_types=1);

namespace Apicore\Tests;

use Apicore\Core\Request;
use Apicore\Core\Response;
use Apicore\Core\Router;

/** Router: route matching, path parameters, Allow header and 404/405. */
final class RouterTest extends TestCase
{
    private function router(): Router
    {
        $router = new Router();
        $router->addRoute('GET', '/ping', RouterTestController::class, static fn ($c, $p, $b) => new Response(200, ['pong' => true]));
        $router->addRoute('GET', '/items/{id}', RouterTestController::class, static fn ($c, $p, $b) => new Response(200, ['id' => $p['id']]));
        $router->addRoute('POST', '/items', RouterTestController::class, static fn ($c, $p, $b) => new Response(201, ['body' => $b]), true);
        return $router;
    }

    public function testMatchesExactPath(): void
    {
        $response = $this->router()->dispatch('GET', '/ping', '', []);
        $this->assertSame(200, $response->status);
        $this->assertSame(['pong' => true], $response->payload);
    }

    public function testCapturesPathParameter(): void
    {
        $response = $this->router()->dispatch('GET', '/items/42', '', []);
        $this->assertSame(['id' => '42'], $response->payload);
    }

    public function testUnknownPathIs404(): void
    {
        $response = $this->router()->dispatch('GET', '/nope', '', []);
        $this->assertSame(404, $response->status);
        $this->assertSame(['error' => 'Not found'], $response->payload);
    }

    public function testKnownPathWrongMethodIs405(): void
    {
        $response = $this->router()->dispatch('DELETE', '/ping', '', []);
        $this->assertSame(405, $response->status);
        $this->assertSame(['error' => 'Method not allowed'], $response->payload);
    }

    public function testAllowHeaderListsMethods(): void
    {
        $allow = $this->router()->allowHeader('/items');
        $this->assertSame('HEAD, OPTIONS, POST', $allow);
    }

    public function testAllowHeaderIsNullForUnknownPath(): void
    {
        $this->assertNull($this->router()->allowHeader('/nope'));
    }

    public function testRoutePublicReportsPolicy(): void
    {
        $router = $this->router();
        $this->assertSame(true, $router->routePublic('POST', '/items'));
        $this->assertSame(false, $router->routePublic('GET', '/ping'));
        $this->assertNull($router->routePublic('GET', '/nope'));
    }
}

/** Controller stand-in: the router only needs the class name and close(). */
final class RouterTestController
{
    public function close(): void
    {
    }
}
