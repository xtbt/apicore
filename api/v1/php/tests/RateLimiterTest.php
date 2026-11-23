<?php
declare(strict_types=1);

namespace Apicore\Tests;

use Apicore\Core\RateLimiter;
use Apicore\Core\TooManyRequestsError;

/** RateLimiter: blocks a key after too many failures inside the window. */
final class RateLimiterTest extends TestCase
{
    private string $directory;

    public function setUp(): void
    {
        $this->directory = sys_get_temp_dir() . '/apicore_ratelimit_test_' . bin2hex(random_bytes(6));
    }

    public function tearDown(): void
    {
        foreach (glob($this->directory . '/*.json') ?: [] as $file) {
            @unlink($file);
        }
        @rmdir($this->directory);
    }

    public function testAllowsBelowTheLimit(): void
    {
        $limiter = new RateLimiter(3, 900, $this->directory);
        $limiter->fail('user');
        $limiter->fail('user');
        $limiter->check('user');
        $this->assertTrue(true);
    }

    public function testBlocksAtTheLimit(): void
    {
        $limiter = new RateLimiter(3, 900, $this->directory);
        $limiter->fail('user');
        $limiter->fail('user');
        $limiter->fail('user');
        $this->assertThrows(TooManyRequestsError::class, static fn () => $limiter->check('user'));
    }

    public function testKeysAreIndependent(): void
    {
        $limiter = new RateLimiter(1, 900, $this->directory);
        $limiter->fail('a');
        $limiter->check('b');
        $this->assertTrue(true);
    }

    public function testResetClearsTheKey(): void
    {
        $limiter = new RateLimiter(1, 900, $this->directory);
        $limiter->fail('user');
        $limiter->reset('user');
        $limiter->check('user');
        $this->assertTrue(true);
    }

    public function testExpiredFailuresAreForgotten(): void
    {
        $limiter = new RateLimiter(1, 0, $this->directory);
        $limiter->fail('user');
        usleep(1000);  // let the window close
        $limiter->check('user');
        $this->assertTrue(true);
    }
}
