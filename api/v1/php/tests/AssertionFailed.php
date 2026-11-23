<?php
declare(strict_types=1);

namespace Apicore\Tests;

use RuntimeException;

/** Raised by a failed assertion; the runner reports it as FAIL. */
final class AssertionFailed extends RuntimeException
{
}
