<?php
declare(strict_types=1);

namespace Apicore\Controllers;

use Apicore\Models\Example;
use Apicore\Schemas\ExampleSchema;

/**
 * Example controller: only the model and schema of the `example` entity.
 *
 * Layer: controllers. It is the smallest possible entity controller: two
 * constants and no methods, which is what a student needs to copy.
 */
final class ExampleController extends BaseController
{
    protected const MODEL_CLASS = Example::class;
    protected const SCHEMA = ExampleSchema::class;
}
