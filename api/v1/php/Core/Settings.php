<?php
declare(strict_types=1);

namespace Apicore\Core;

use DateTimeZone;
use Exception;
use ValueError;

/**
 * Settings: custom .env reader exposed as a single instance.
 *
 * Layer: core (cross-cutting). Real environment variables override the .env
 * file. It must never import from Controllers, Models or Routers.
 */
final class Settings
{
    private const REQUIRED = ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'JWT_SECRET'];

    public string $APP_HOST;
    public int $APP_PORT;
    public string $APP_TIMEZONE;
    public string $DB_HOST;
    public int $DB_PORT;
    public string $DB_NAME;
    public string $DB_USER;
    public string $DB_PASSWORD;
    public string $JWT_SECRET;
    public string $JWT_ALGORITHM;
    public int $TOKEN_LIFETIME_MINUTES;
    public int $TOKEN_MIN_REMAINING_MINUTES;
    public string $CORS_ALLOW_ORIGIN;

    private static ?self $instance = null;

    public function __construct(?string $envPath = null)
    {
        $values = self::readEnvFile($envPath ?? dirname(__DIR__) . '/.env');

        // Real environment variable first, then the .env file, then the default
        $get = static function (string $key, ?string $default = null) use ($values): ?string {
            $env = getenv($key);
            if ($env !== false) {
                return $env;
            }
            return $values[$key] ?? $default;
        };

        $this->APP_HOST = $get('APP_HOST', 'localhost');
        $this->APP_PORT = (int) $get('APP_PORT', '8000');
        $this->APP_TIMEZONE = $get('APP_TIMEZONE', 'America/Tijuana');
        try {
            new DateTimeZone($this->APP_TIMEZONE);
        } catch (Exception) {
            throw new ValueError('APP_TIMEZONE is not a valid IANA timezone: ' . $this->APP_TIMEZONE);
        }
        $this->DB_HOST = $get('DB_HOST', 'localhost');
        $this->DB_PORT = (int) $get('DB_PORT', '3306');
        $this->DB_NAME = (string) $get('DB_NAME', '');
        $this->DB_USER = (string) $get('DB_USER', '');
        $this->DB_PASSWORD = (string) $get('DB_PASSWORD', '');
        $this->JWT_SECRET = (string) $get('JWT_SECRET', '');
        $this->JWT_ALGORITHM = $get('JWT_ALGORITHM', 'HS256');
        $this->TOKEN_LIFETIME_MINUTES = (int) $get('TOKEN_LIFETIME_MINUTES', '60');
        $this->TOKEN_MIN_REMAINING_MINUTES = (int) $get('TOKEN_MIN_REMAINING_MINUTES', '10');
        // '*' allows any origin (fine for a classroom API); set a URL to restrict it
        $this->CORS_ALLOW_ORIGIN = $get('CORS_ALLOW_ORIGIN', '*');
    }

    public static function instance(): self
    {
        return self::$instance ??= new self();
    }

    /**
     * Raise ValueError listing every required setting that is missing.
     *
     * Called at startup, so a misconfigured server fails immediately instead of
     * on the first request.
     */
    public function validate(): void
    {
        $missing = [];
        foreach (self::REQUIRED as $name) {
            if ($this->{$name} === '') {
                $missing[] = $name;
            }
        }
        if ($missing !== []) {
            throw new ValueError('Missing required setting(s): ' . implode(', ', $missing));
        }
    }

    /**
     * Parse KEY=VALUE lines (ignores blank lines and # comments). Missing file -> [].
     *
     * @return array<string, string>
     */
    private static function readEnvFile(string $path): array
    {
        if (!is_file($path)) {
            return [];
        }
        $values = [];
        foreach (file($path, FILE_IGNORE_NEW_LINES) ?: [] as $line) {
            $line = trim($line);
            if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) {
                continue;
            }
            [$key, $value] = explode('=', $line, 2);
            $values[trim($key)] = trim(trim($value), '"\'');
        }
        return $values;
    }
}
