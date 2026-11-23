<?php
declare(strict_types=1);

/**
 * Unit test runner: discovers *Test.php next to this file and runs every
 * public test* method, printing the same OK/FAILED report as the Python suite.
 *
 * Layer: tests. No composer, no PHPUnit: `php tests/run.php`.
 *
 * Exit code 0 when everything passes, 1 otherwise, so CI can gate on it.
 */

use Apicore\Tests\TestCase;

require dirname(__DIR__) . '/Core/Autoloader.php';

// The tests live in a lowercase directory, so map the namespace explicitly
// instead of relying on PSR-4 case-insensitive matching (macOS only).
spl_autoload_register(static function (string $class): void {
    $prefix = 'Apicore\\Tests\\';
    if (!str_starts_with($class, $prefix)) {
        return;
    }
    $file = __DIR__ . '/' . substr($class, strlen($prefix)) . '.php';
    if (is_file($file)) {
        require_once $file;
    }
});

$files = glob(__DIR__ . '/*Test.php') ?: [];
sort($files);

$tests = 0;
$failures = 0;
$assertions = 0;

foreach ($files as $file) {
    $class = 'Apicore\\Tests\\' . basename($file, '.php');
    if (!class_exists($class)) {
        fwrite(STDERR, "SKIP {$class}: class not found\n");
        continue;
    }
    $instance = new $class();
    if (!$instance instanceof TestCase) {
        fwrite(STDERR, "SKIP {$class}: not a TestCase\n");
        continue;
    }

    foreach (get_class_methods($instance) as $method) {
        if (!str_starts_with($method, 'test')) {
            continue;
        }
        $tests++;
        try {
            $instance->setUp();
            $instance->{$method}();
            echo '.';
        } catch (Throwable $error) {
            $failures++;
            echo 'F';
            fwrite(STDERR, sprintf(
                "\nFAIL %s::%s\n  %s: %s\n",
                basename($file, '.php'),
                $method,
                $error::class,
                $error->getMessage(),
            ));
        } finally {
            $instance->tearDown();
            $assertions += $instance->assertionCount();
        }
    }
}

echo "\n\n";
if ($failures === 0) {
    echo "Ran {$tests} tests, {$assertions} assertions\n\nOK\n";
    exit(0);
}
echo "Ran {$tests} tests, {$assertions} assertions, {$failures} FAILED\n";
exit(1);
