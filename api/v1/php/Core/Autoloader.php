<?php
declare(strict_types=1);

/**
 * PSR-4 autoloader: Apicore\Core\Router -> Core/Router.php
 *
 * Layer: core. Composer is not required: the project has a single namespace
 * root, so twelve lines replace a dependency the students would have to install.
 */
spl_autoload_register(static function (string $class): void {
    $prefix = 'Apicore\\';
    if (!str_starts_with($class, $prefix)) {
        return;
    }
    $relative = substr($class, strlen($prefix));
    $file = dirname(__DIR__) . '/' . str_replace('\\', '/', $relative) . '.php';
    if (is_file($file)) {
        require_once $file;
    }
});
