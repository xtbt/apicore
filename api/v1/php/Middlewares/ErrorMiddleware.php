<?php
declare(strict_types=1);

namespace Apicore\Middlewares;

use Apicore\Core\AppError;
use Apicore\Core\Logger;
use Apicore\Core\Request;
use Apicore\Core\Response;
use Closure;
use Throwable;
use ValueError;

/**
 * Translate exceptions into Response objects, the pipeline's response shape.
 *
 * Layer: middlewares (cross-cutting). Sits inside CorsMiddleware, so every
 * error leaves the pipeline as a uniform JSON body that still carries the CORS
 * headers.
 */
final class ErrorMiddleware extends Middleware
{
    /**
     * AppError keeps its status code, ValueError is a 400 and anything else a
     * 500. The traceback is always logged and never returned to the client.
     */
    public function handle(Request $request, Closure $next): Response
    {
        try {
            return $next($request);
        } catch (AppError | ValueError $error) {
            return Response::error(AppError::statusOf($error), $error->getMessage());
        } catch (Throwable) {
            Logger::exception('Unhandled error on ' . $request->method . ' ' . $request->path);
            return Response::error(500, 'Internal server error');
        }
    }
}
