<?php
declare(strict_types=1);

namespace Apicore\Controllers;

use Apicore\Models\Mood;
use Apicore\Schemas\MoodSchema;

/**
 * Mood controller: only the model and schema of the `moods` entity.
 *
 * Layer: controllers. The generic CRUD flow lives in BaseController.
 */
final class MoodController extends BaseController
{
    protected const MODEL_CLASS = Mood::class;
    protected const SCHEMA = MoodSchema::class;
}
