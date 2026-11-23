<?php
declare(strict_types=1);

namespace Apicore\Routers;

use Apicore\Controllers\AuthController;
use Apicore\Core\Response;
use Apicore\Core\Router;

/**
 * Auth routes: login (public) and logout (requires token).
 *
 * Layer: routers. One file per entity; Routers\registerAll() discovers them.
 */
final class AuthRouter
{
    public static function register(Router $router): void
    {
        $router->addRoute(
            'POST',
            '/auth/login',
            AuthController::class,
            static fn (AuthController $controller, array $params, string $body): Response => new Response(
                200,
                ['status' => 'ok', 'data' => $controller->login(Router::jsonObject($body))],
            ),
            public: true,
        );

        $router->addRoute(
            'POST',
            '/auth/logout',
            AuthController::class,
            static function (AuthController $controller): Response {
                $controller->logout();
                return new Response(200, ['status' => 'ok', 'message' => 'Token revoked']);
            },
        );
    }
}
