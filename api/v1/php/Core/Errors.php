<?php
declare(strict_types=1);

namespace Apicore\Core;

use RuntimeException;
use Throwable;
use ValueError;

/**
 * Application errors that carry their own HTTP status code.
 *
 * Layer: core (cross-cutting). Raised by any layer, translated to JSON by
 * Middlewares\ErrorMiddleware. The whole hierarchy lives in this one file, the
 * counterpart of core/exceptions.py, so the status codes are read together.
 *
 * Core\Autoloader maps these class names to this file: PSR-4 assumes one class
 * per file, and grouping them is worth the one explicit map entry each.
 */

/** Base error: any layer may raise it with an explicit status code. */
class AppError extends RuntimeException
{
    public function __construct(string $message, private int $statusCode = 500)
    {
        parent::__construct($message);
    }

    public function statusCode(): int
    {
        return $this->statusCode;
    }

    /**
     * HTTP status an exception maps to: AppError keeps its own, ValueError is a
     * 400, the rest a 500.
     */
    public static function statusOf(Throwable $error): int
    {
        if ($error instanceof self) {
            return $error->statusCode();
        }
        if ($error instanceof ValueError) {
            return 400;
        }
        return 500;
    }
}

/** 401: the request has no valid bearer token. */
final class UnauthorizedError extends AppError
{
    public function __construct(string $message = 'Unauthorized')
    {
        parent::__construct($message, 401);
    }
}

/** 403: the caller is authenticated but may not touch this record. */
final class ForbiddenError extends AppError
{
    public function __construct(string $message = 'Forbidden')
    {
        parent::__construct($message, 403);
    }
}

/** 413: the request body exceeds the 1 MB cap. */
final class PayloadTooLargeError extends AppError
{
    public function __construct(string $message = 'Payload too large')
    {
        parent::__construct($message, 413);
    }
}

/** 429: the caller exceeded its request budget. */
final class TooManyRequestsError extends AppError
{
    public function __construct(string $message = 'Too many requests')
    {
        parent::__construct($message, 429);
    }
}

/** 503: the database is unreachable or the server is saturated. */
final class ServiceUnavailableError extends AppError
{
    public function __construct(string $message = 'Service unavailable')
    {
        parent::__construct($message, 503);
    }
}
