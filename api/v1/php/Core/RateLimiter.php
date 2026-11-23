<?php
declare(strict_types=1);

namespace Apicore\Core;

/**
 * Rate limiter: blocks a key (e.g. a username) after too many failed attempts.
 *
 * Layer: core (cross-cutting). PHP resets static state on every request, so the
 * counters live in small files under the system temp directory instead of
 * memory. That keeps them working with any number of workers, and they still
 * reset when the machine reboots. Enough for a teaching API, not for a cluster.
 */
final class RateLimiter
{
    private const MAX_KEYS = 1024;  // purge stale keys beyond this, so unknown usernames cannot grow the directory

    private string $directory;

    public function __construct(
        private int $maxFailures = 5,
        private int $windowSeconds = 900,
        ?string $directory = null,
    ) {
        $this->directory = $directory ?? sys_get_temp_dir() . '/apicore_ratelimit';
        if (!is_dir($this->directory)) {
            @mkdir($this->directory, 0700, true);
        }
    }

    /** Throw TooManyRequestsError (429) if $key is blocked. */
    public function check(string $key): void
    {
        if (count($this->recent($key)) >= $this->maxFailures) {
            throw new TooManyRequestsError('Too many failed attempts, try again later');
        }
    }

    public function fail(string $key): void
    {
        $this->withLock($key, function (array $times): array {
            $times[] = microtime(true);
            return $times;
        });
    }

    public function reset(string $key): void
    {
        $path = $this->path($key);
        if (is_file($path)) {
            @unlink($path);
        }
    }

    /**
     * Failures of $key inside the window, dropping the ones that already expired.
     *
     * @return list<float>
     */
    private function recent(string $key): array
    {
        $path = $this->path($key);
        if (!is_file($path)) {
            return [];
        }
        $handle = @fopen($path, 'r');
        if ($handle === false) {
            return [];
        }
        try {
            flock($handle, LOCK_SH);
            $times = $this->decode((string) stream_get_contents($handle));
        } finally {
            flock($handle, LOCK_UN);
            fclose($handle);
        }
        return $this->fresh($times);
    }

    /**
     * Read, transform and rewrite the counter file under an exclusive lock.
     *
     * @param callable(list<float>): list<float> $change
     */
    private function withLock(string $key, callable $change): void
    {
        $this->purgeWhenFull();
        $handle = @fopen($this->path($key), 'c+');
        if ($handle === false) {
            return;  // a read-only temp directory must not break the login
        }
        try {
            flock($handle, LOCK_EX);
            $times = $this->fresh($this->decode((string) stream_get_contents($handle)));
            $times = $change($times);
            ftruncate($handle, 0);
            rewind($handle);
            fwrite($handle, (string) json_encode($times));
            fflush($handle);
        } finally {
            flock($handle, LOCK_UN);
            fclose($handle);
        }
    }

    /** @return list<float> */
    private function fresh(array $times): array
    {
        $limit = microtime(true) - $this->windowSeconds;
        return array_values(array_filter(
            $times,
            static fn (float $time): bool => $time > $limit,
        ));
    }

    /** @return list<float> */
    private function decode(string $raw): array
    {
        $decoded = json_decode($raw, true);
        if (!is_array($decoded)) {
            return [];
        }
        return array_values(array_filter($decoded, static fn ($time): bool => is_numeric($time)));
    }

    private function path(string $key): string
    {
        return $this->directory . '/' . hash('sha256', $key) . '.json';
    }

    /** Drop expired files when the directory grows past the cap. */
    private function purgeWhenFull(): void
    {
        $files = glob($this->directory . '/*.json') ?: [];
        if (count($files) < self::MAX_KEYS) {
            return;
        }
        $limit = time() - $this->windowSeconds;
        foreach ($files as $file) {
            if (@filemtime($file) < $limit) {
                @unlink($file);
            }
        }
    }
}
