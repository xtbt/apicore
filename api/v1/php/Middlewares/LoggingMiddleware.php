<?php
declare(strict_types=1);

namespace Apicore\Middlewares;

use Apicore\Core\AppError;
use Apicore\Core\Logger;
use Apicore\Core\Request;
use Apicore\Core\Response;
use Closure;
use Throwable;

/**
 * Structured request log: IP METHOD ROUTE STATUS DURATIONms.
 *
 * Layer: middlewares (cross-cutting). Sits inside ErrorMiddleware, so it logs
 * the status of a failed request too, before the error is translated into a
 * response.
 */
final class LoggingMiddleware extends Middleware
{
    /** Times every request and logs one line per request, whatever its outcome. */
    public function handle(Request $request, Closure $next): Response
    {
        $start = microtime(true);
        try {
            $response = $next($request);
        } catch (Throwable $error) {
            $this->log($request, AppError::statusOf($error), $start);
            throw $error;
        }
        $this->log($request, $response->status, $start);
        return $response;
    }

    private function log(Request $request, int $status, float $start): void
    {
        $milliseconds = (int) round((microtime(true) - $start) * 1000);
        Logger::info(sprintf(
            '%s %s %s %d %dms',
            $request->clientIp,
            $request->method,
            $request->path,
            $status,
            $milliseconds,
        ));
    }
}
