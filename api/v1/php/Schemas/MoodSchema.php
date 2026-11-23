<?php
declare(strict_types=1);

namespace Apicore\Schemas;

/**
 * Mood input schema: field rules of the `moods` entity.
 *
 * Layer: schemas (cross-cutting). Validation only: no HTTP, no SQL.
 */
final class MoodSchema
{
    public const STATUSES = ['Active', 'Inactive'];

    /**
     * Validate a mood payload. $partial (PATCH) checks only the fields sent.
     *
     * @param array<string, mixed> $data
     */
    public static function validate(array $data, bool $partial = false): void
    {
        BaseSchema::validateString($data, 'MoodName', 16, required: true, partial: $partial);
        BaseSchema::validateEnum($data, 'MoodStatus', self::STATUSES, $partial);
    }
}
