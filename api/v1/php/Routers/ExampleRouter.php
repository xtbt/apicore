<?php
declare(strict_types=1);

namespace Apicore\Routers;

use Apicore\Controllers\ExampleController;
use Apicore\Core\Router;

/**
 * Example routes: only wires the `examples` URLs to ExampleController.
 *
 * Layer: routers. One file per entity; Routers\registerAll() discovers them.
 */
final class ExampleRouter
{
    public static function register(Router $router): void
    {
        $router->addCrudRoutes('/examples', ExampleController::class, 'Example');
    }
}
