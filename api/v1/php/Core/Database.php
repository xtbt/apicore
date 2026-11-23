<?php
declare(strict_types=1);

namespace Apicore\Core;

use PDO;
use PDOException;

/**
 * Database: one PDO connection per request, shared by every model.
 *
 * Layer: core. PHP serves each request in its own process (or worker), so a
 * single connection per request is enough; there is no pool to manage like in
 * a long-running server.
 */
final class Database
{
    private static ?PDO $connection = null;

    public static function connection(): PDO
    {
        if (self::$connection instanceof PDO) {
            return self::$connection;
        }
        $settings = Settings::instance();
        $dsn = sprintf(
            'mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4',
            $settings->DB_HOST,
            $settings->DB_PORT,
            $settings->DB_NAME,
        );
        try {
            $pdo = new PDO($dsn, $settings->DB_USER, $settings->DB_PASSWORD, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                // Real prepared statements: the driver returns native ints and floats
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            ]);
            // Store and compare timestamps in UTC: NOW() then equals UTC_TIMESTAMP()
            // whatever the MySQL server timezone is (named zones need the tz tables)
            $pdo->exec("SET time_zone = '+00:00'");
        } catch (PDOException) {
            // The database is unreachable: answer 503 instead of a generic 500
            throw new ServiceUnavailableError('Database unavailable');
        }
        return self::$connection = $pdo;
    }
}
