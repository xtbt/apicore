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
 * Middlewares\ErrorMiddleware.
 */
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
