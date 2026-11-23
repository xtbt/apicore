<?php
declare(strict_types=1);

namespace Apicore\Core;

/** 401: the request has no valid bearer token. */
final class UnauthorizedError extends AppError
{
    public function __construct(string $message = 'Unauthorized')
    {
        parent::__construct($message, 401);
    }
}
