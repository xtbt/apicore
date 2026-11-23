<?php
declare(strict_types=1);

namespace Apicore\Routers;

use Apicore\Controllers\HealthController;
use Apicore\Core\Response;
use Apicore\Core\Router;

/**
 * Health route: only wires GET /health to HealthController (public).
 *
 * Layer: routers. One file per entity; Routers\registerAll() discovers them.
 */
final class HealthRouter
{
    public static function register(Router $router): void
    {
        $router->addRoute(
            'GET',
            '/health',
            HealthController::class,
            static fn (HealthController $controller): Response => $controller->check(),
            public: true,
        );
    }
}
