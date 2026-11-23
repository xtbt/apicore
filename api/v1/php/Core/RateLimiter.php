<?php
declare(strict_types=1);

namespace Apicore\Core;

/**
 * Rate limiter: blocks a key (e.g. a username) after too many failed attempts.
 *
 * Layer: core (cross-cutting). In-memory and per process: counters reset when
 * the server restarts, and with PHP_CLI_SERVER_WORKERS each worker keeps its
 * own counters. Enough for a teaching API, not for a cluster.
 */
final class RateLimiter
{
    private const MAX_KEYS = 1024;  // purge stale keys beyond this, so unknown usernames cannot grow memory

    /** @var array<string, list<float>> key -> failure timestamps */
    private static array $failures = [];

    public function __construct(
        private int $maxFailures = 5,
        private int $windowSeconds = 900,
    ) {
    }

    /**
     * Failures of $key inside the window (stale keys are dropped on the way).
     *
     * @return list<float>
     */
    private function recent(string $key): array
    {
        $limit = microtime(true) - $this->windowSeconds;
        $recent = array_values(array_filter(
            self::$failures[$key] ?? [],
            static fn (float $time): bool => $time > $limit,
        ));
        if ($recent === []) {
            unset(self::$failures[$key]);
        } else {
            self::$failures[$key] = $recent;
        }
        return $recent;
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
        $this->recent($key);
        if (count(self::$failures) >= self::MAX_KEYS) {
            $limit = microtime(true) - $this->windowSeconds;
            foreach (self::$failures as $staleKey => $times) {
                if (array_filter($times, static fn (float $time): bool => $time > $limit) === []) {
                    unset(self::$failures[$staleKey]);
                }
            }
        }
        self::$failures[$key][] = microtime(true);
    }

    public function reset(string $key): void
    {
        unset(self::$failures[$key]);
    }
}
