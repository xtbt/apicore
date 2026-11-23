<?php
declare(strict_types=1);

namespace Apicore\Tests;

use Throwable;

/**
 * Minimal assertion base class for the PHP unit tests.
 *
 * Layer: tests. It replaces PHPUnit so the project needs no composer install:
 * a student runs `php tests/run.php` and gets the same OK/FAILED report the
 * Python suite prints.
 */
abstract class TestCase
{
    private int $assertions = 0;

    /** Hook run before each test method. */
    public function setUp(): void
    {
    }

    /** Hook run after each test method, even when it fails. */
    public function tearDown(): void
    {
    }

    public function assertionCount(): int
    {
        return $this->assertions;
    }

    protected function assertSame(mixed $expected, mixed $actual, string $message = ''): void
    {
        $this->assertions++;
        if ($expected !== $actual) {
            throw new AssertionFailed(sprintf(
                '%sexpected %s, got %s',
                $message === '' ? '' : $message . ': ',
                $this->describe($expected),
                $this->describe($actual),
            ));
        }
    }

    protected function assertTrue(mixed $actual, string $message = ''): void
    {
        $this->assertSame(true, $actual, $message);
    }

    protected function assertFalse(mixed $actual, string $message = ''): void
    {
        $this->assertSame(false, $actual, $message);
    }

    protected function assertNull(mixed $actual, string $message = ''): void
    {
        $this->assertSame(null, $actual, $message);
    }

    protected function assertCount(int $expected, array $actual, string $message = ''): void
    {
        $this->assertSame($expected, count($actual), $message);
    }

    protected function assertContains(mixed $needle, array $haystack, string $message = ''): void
    {
        $this->assertions++;
        if (!in_array($needle, $haystack, true)) {
            throw new AssertionFailed(sprintf(
                '%s%s not found in %s',
                $message === '' ? '' : $message . ': ',
                $this->describe($needle),
                $this->describe($haystack),
            ));
        }
    }

    /**
     * Assert that $callable throws $class (or a subclass) and return the error.
     *
     * @param class-string<Throwable> $class
     */
    protected function assertThrows(string $class, callable $callable, string $message = ''): Throwable
    {
        $this->assertions++;
        try {
            $callable();
        } catch (Throwable $error) {
            if (!$error instanceof $class) {
                throw new AssertionFailed(sprintf(
                    '%sexpected %s, got %s: %s',
                    $message === '' ? '' : $message . ': ',
                    $class,
                    $error::class,
                    $error->getMessage(),
                ));
            }
            return $error;
        }
        throw new AssertionFailed(sprintf(
            '%sexpected %s, nothing was thrown',
            $message === '' ? '' : $message . ': ',
            $class,
        ));
    }

    private function describe(mixed $value): string
    {
        return match (true) {
            is_string($value) => '"' . $value . '"',
            is_bool($value) => $value ? 'true' : 'false',
            is_null($value) => 'null',
            is_array($value) => json_encode($value) ?: 'array',
            is_object($value) => $value::class,
            default => (string) $value,
        };
    }
}
