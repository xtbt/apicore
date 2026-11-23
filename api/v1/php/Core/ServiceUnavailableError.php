<?php
declare(strict_types=1);

namespace Apicore\Core;

/** 503: the database is unreachable or the server is saturated. */
final class ServiceUnavailableError extends AppError
{
    public function __construct(string $message = 'Service unavailable')
    {
        parent::__construct($message, 503);
    }
}
