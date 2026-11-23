<?php
declare(strict_types=1);

/**
 * PSR-4 autoloader: Apicore\Core\Router -> Core/Router.php
 *
 * Layer: core. Composer is not required: the project has a single namespace
 * root, so a dozen lines replace a dependency the students would have to install.
 */
spl_autoload_register(static function (string $class): void {
    $prefix = 'Apicore\\';
    if (!str_starts_with($class, $prefix)) {
        return;
    }
    $relative = substr($class, strlen($prefix));

    // PSR-4 assumes one class per file. The error hierarchy is grouped in
    // Core/Errors.php (like core/exceptions.py), so it declares its file here.
    $grouped = [
        'Core\\AppError' => 'Core/Errors.php',
        'Core\\UnauthorizedError' => 'Core/Errors.php',
        'Core\\ForbiddenError' => 'Core/Errors.php',
        'Core\\PayloadTooLargeError' => 'Core/Errors.php',
        'Core\\TooManyRequestsError' => 'Core/Errors.php',
        'Core\\ServiceUnavailableError' => 'Core/Errors.php',
    ];
    if (isset($grouped[$relative])) {
        require_once dirname(__DIR__) . '/' . $grouped[$relative];
        return;
    }

    $file = dirname(__DIR__) . '/' . str_replace('\\', '/', $relative) . '.php';
    if (is_file($file)) {
        require_once $file;
    }
});
