<?php
declare(strict_types=1);

namespace Apicore\Core;

/** 403: the caller is authenticated but may not touch this record. */
final class ForbiddenError extends AppError
{
    public function __construct(string $message = 'Forbidden')
    {
        parent::__construct($message, 403);
    }
}
