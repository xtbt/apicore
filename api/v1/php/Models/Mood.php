<?php
declare(strict_types=1);

namespace Apicore\Models;

/**
 * Mood model: only the table definition of the `moods` entity.
 *
 * Layer: models. No validation and no HTTP here.
 */
final class Mood extends BaseModel
{
    protected const TABLE_NAME = 'moods';
    protected const ID_COLUMN = 'MoodId';
    protected const COLUMNS = ['MoodName', 'MoodStatus'];
}
