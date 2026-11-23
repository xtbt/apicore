<?php
declare(strict_types=1);

namespace Apicore\Routers;

use Apicore\Controllers\MoodController;
use Apicore\Core\Router;

/**
 * Mood routes: only wires the `moods` URLs to MoodController (all protected).
 *
 * Layer: routers. One file per entity; Routers\registerAll() discovers them.
 */
final class MoodRouter
{
    public static function register(Router $router): void
    {
        $router->addCrudRoutes('/moods', MoodController::class, 'Mood');
    }
}
