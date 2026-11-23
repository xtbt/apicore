<?php
declare(strict_types=1);

namespace Apicore\Core;

/**
 * Logging configuration: one console stream shared by every module.
 *
 * Layer: core (cross-cutting). Core\Application calls configure() once at startup;
 * everywhere else uses info()/exception(). The line format matches the Python
 * implementation: "2026-11-23 03:20:00,123 INFO 127.0.0.1 GET /health 200 5ms".
 */
final class Logger
{
    public static function configure(): void
    {
        $settings = Settings::instance();
        // Log timestamps in APP_TIMEZONE (America/Tijuana), not the machine clock
        date_default_timezone_set($settings->APP_TIMEZONE);
        ini_set('log_errors', '1');
        ini_set('error_log', 'php://stderr');
        // Errors are logged, never printed into the JSON response
        ini_set('display_errors', '0');
    }

    public static function info(string $message): void
    {
        error_log(self::timestamp() . ' INFO ' . $message);
    }

    public static function exception(string $message): void
    {
        error_log(self::timestamp() . ' ERROR ' . $message);
    }

    private static function timestamp(): string
    {
        $now = microtime(true);
        return date('Y-m-d H:i:s', (int) $now) . ',' . sprintf('%03d', (int) (($now - (int) $now) * 1000));
    }
}
