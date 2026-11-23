<?php
declare(strict_types=1);

namespace Apicore\Tests;

use Apicore\Core\Response;

/** Response: the value object every layer returns. */
final class ResponseTest extends TestCase
{
    public function testDefaultsTo200WithNoPayload(): void
    {
        $response = new Response();
        $this->assertSame(200, $response->status);
        $this->assertNull($response->payload);
        $this->assertSame([], $response->headers);
    }

    public function testErrorBuildsUniformBody(): void
    {
        $response = Response::error(403, 'Forbidden');
        $this->assertSame(403, $response->status);
        $this->assertSame(['error' => 'Forbidden'], $response->payload);
    }

    public function testCarriesHeaders(): void
    {
        $response = new Response(201, ['ID' => 7], ['Location' => '/moods/7']);
        $this->assertSame('/moods/7', $response->headers['Location']);
    }
}
