<?php
declare(strict_types=1);

namespace Apicore\Core;

/**
 * What an endpoint or middleware returns: status code, payload and headers.
 *
 * Layer: core. It never writes to the socket; Core\Application serializes the
 * payload and sends it.
 */
final class Response
{
    /**
     * @param mixed                $payload dict/list serialized as JSON, or null for no body
     * @param array<string, string> $headers
     */
    public function __construct(
        public int $status = 200,
        public mixed $payload = null,
        public array $headers = [],
    ) {
    }

    /** Uniform error body: {"error": message}. */
    public static function error(int $status, string $message): self
    {
        return new self($status, ['error' => $message]);
    }
}
