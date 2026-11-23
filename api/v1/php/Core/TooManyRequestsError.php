<?php
declare(strict_types=1);

namespace Apicore\Core;

/** 429: the caller exceeded its request budget. */
final class TooManyRequestsError extends AppError
{
    public function __construct(string $message = 'Too many requests')
    {
        parent::__construct($message, 429);
    }
}
