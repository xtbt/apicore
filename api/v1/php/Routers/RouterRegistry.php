<?php
declare(strict_types=1);

namespace Apicore\Routers;

use Apicore\Core\Router;
use RuntimeException;

/**
 * Discover and register route classes without editing the entry point.
 *
 * Layer: routers. Convention: every *Router.php file in this directory exposes
 * a static register(Router $router). Adding an entity router then requires only
 * adding that file to this package, the counterpart of routers/__init__.py.
 */
final class RouterRegistry
{
    public static function registerAll(Router $router): void
    {
        $files = glob(__DIR__ . '/*Router.php') ?: [];
        sort($files);  // stable alphabetical order, like sorted() in Python

        foreach ($files as $file) {
            $class = __NAMESPACE__ . '\\' . basename($file, '.php');
            if (!is_callable([$class, 'register'])) {
                throw new RuntimeException($class . ' must define register(Router $router)');
            }
            $class::register($router);
        }
    }
}
