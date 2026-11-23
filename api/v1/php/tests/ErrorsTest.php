<?php
declare(strict_types=1);

namespace Apicore\Tests;

use Apicore\Core\AppError;
use Apicore\Core\ForbiddenError;
use Apicore\Core\PayloadTooLargeError;
use Apicore\Core\ServiceUnavailableError;
use Apicore\Core\TooManyRequestsError;
use Apicore\Core\UnauthorizedError;
use RuntimeException;
use ValueError;

/** Errors: every subclass carries its status and statusOf() maps the rest. */
final class ErrorsTest extends TestCase
{
    public function testEachSubclassCarriesItsStatus(): void
    {
        $this->assertSame(401, (new UnauthorizedError())->statusCode());
        $this->assertSame(403, (new ForbiddenError())->statusCode());
        $this->assertSame(413, (new PayloadTooLargeError())->statusCode());
        $this->assertSame(429, (new TooManyRequestsError())->statusCode());
        $this->assertSame(503, (new ServiceUnavailableError())->statusCode());
    }

    public function testDefaultMessages(): void
    {
        $this->assertSame('Unauthorized', (new UnauthorizedError())->getMessage());
        $this->assertSame('Forbidden', (new ForbiddenError())->getMessage());
        $this->assertSame('Payload too large', (new PayloadTooLargeError())->getMessage());
        $this->assertSame('Too many requests', (new TooManyRequestsError())->getMessage());
        $this->assertSame('Service unavailable', (new ServiceUnavailableError())->getMessage());
    }

    public function testCustomMessageIsKept(): void
    {
        $this->assertSame('Token revoked', (new UnauthorizedError('Token revoked'))->getMessage());
    }

    public function testStatusOfKeepsAppErrorStatus(): void
    {
        $this->assertSame(403, AppError::statusOf(new ForbiddenError()));
    }

    public function testStatusOfMapsValueErrorTo400(): void
    {
        $this->assertSame(400, AppError::statusOf(new ValueError('bad input')));
    }

    public function testStatusOfMapsAnythingElseTo500(): void
    {
        $this->assertSame(500, AppError::statusOf(new RuntimeException('boom')));
    }

    public function testBaseErrorDefaultsTo500(): void
    {
        $this->assertSame(500, (new AppError('boom'))->statusCode());
    }
}
