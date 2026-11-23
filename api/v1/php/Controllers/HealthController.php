<?php
declare(strict_types=1);

namespace Apicore\Controllers;

use Apicore\Core\Database;
use Apicore\Core\Response;
use Apicore\Core\ServiceUnavailableError;
use PDOException;

/**
 * Health controller: reports whether the server and its database answer.
 *
 * Layer: controllers. It has no model (MODEL_CLASS = null) because it only
 * needs to prove the connection works.
 */
final class HealthController extends BaseController
{
    protected const MODEL_CLASS = null;

    /** 200 when the database answers, 503 when it does not. */
    public function check(): Response
    {
        try {
            Database::connection()->query('SELECT 1');
        } catch (ServiceUnavailableError | PDOException) {
            throw new ServiceUnavailableError('Database unavailable');
        }
        return new Response(200, ['status' => 'ok', 'message' => 'Server is running']);
    }
}
