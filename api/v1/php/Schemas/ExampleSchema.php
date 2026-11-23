<?php
declare(strict_types=1);

namespace Apicore\Schemas;

/**
 * Example input schema: field rules of the `example` entity.
 *
 * Layer: schemas (cross-cutting). Validation only: no HTTP, no SQL.
 *
 * Each field shows the validator that matches its column type, so a student can
 * copy the pair (column type -> validator) into their own schema.
 */
final class ExampleSchema
{
    public const STATUSES = ['Active', 'Inactive'];

    /**
     * Largest base64 payload that fits a BLOB column: 4 * ceil(65535 / 3).
     *
     * Validating here turns an oversized picture into a 400 instead of letting
     * MySQL reject it with a 500.
     */
    public const PICTURE_MAX_LENGTH = 87380;

    /**
     * Validate an example payload. $partial (PATCH) checks only the fields sent.
     *
     * @param array<string, mixed> $data
     */
    public static function validate(array $data, bool $partial = false): void
    {
        BaseSchema::validateString($data, 'ExampleName', 45, required: true, partial: $partial);
        BaseSchema::validateString($data, 'ExampleCode', 3, partial: $partial);
        BaseSchema::validateText($data, 'ExampleDescription', partial: $partial);
        BaseSchema::validateNumber($data, 'ExamplePrice', minimum: 0, partial: $partial);
        BaseSchema::validateInteger($data, 'ExampleQuantity', minimum: 0, partial: $partial);
        BaseSchema::validateInteger($data, 'ExampleBigNumber', partial: $partial);
        BaseSchema::validateNumber($data, 'ExampleRatio', partial: $partial);
        BaseSchema::validateBoolean($data, 'ExampleActive', partial: $partial);
        BaseSchema::validateEnum($data, 'ExampleStatus', self::STATUSES, $partial);
        BaseSchema::validateDate($data, 'ExampleBirthDate', partial: $partial);
        BaseSchema::validateDatetime($data, 'ExampleCreatedAt', partial: $partial);
        BaseSchema::validateTime($data, 'ExampleStartTime', partial: $partial);
        BaseSchema::validateYear($data, 'ExampleYear', partial: $partial);
        BaseSchema::validateJson($data, 'ExampleMetadata', partial: $partial);
        BaseSchema::validateString(
            $data,
            'ExamplePicture',
            self::PICTURE_MAX_LENGTH,
            partial: $partial,
        );
    }
}
