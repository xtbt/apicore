<?php
declare(strict_types=1);

/**
 * Front controller: the only file the PHP built-in server executes.
 *
 * Layer: entry point. Everything else lives in Core\Application, so this file
 * only wires the autoloader and starts the application.
 *
 * Start it with:  php -S localhost:8000 index.php
 */

use Apicore\Core\Application;

require __DIR__ . '/Core/Autoloader.php';

Application::boot()->run();
