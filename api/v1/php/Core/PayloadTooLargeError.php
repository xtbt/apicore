<?php
declare(strict_types=1);

namespace Apicore\Core;

/** 413: the request body exceeds the 1 MB cap. */
final class PayloadTooLargeError extends AppError
{
    public function __construct(string $message = 'Payload too large')
    {
        parent::__construct($message, 413);
    }
}
