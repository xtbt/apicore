<?php
declare(strict_types=1);

namespace Apicore\Routers;

use Apicore\Controllers\UserController;
use Apicore\Core\Router;

/**
 * User routes: the CRUD of `users`, with POST public for self-registration.
 *
 * Layer: routers. One file per entity; Routers\registerAll() discovers them.
 */
final class UserRouter
{
    public static function register(Router $router): void
    {
        $router->addCrudRoutes('/users', UserController::class, 'User', publicMethods: ['POST']);
    }
}
