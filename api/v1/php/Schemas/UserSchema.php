<?php
declare(strict_types=1);

namespace Apicore\Schemas;

/**
 * User input schema: field rules of the `users` entity.
 *
 * Layer: schemas (cross-cutting). Validation only: no HTTP, no SQL. Business
 * rules (duplicated username, password hashing, role permissions) live in the
 * controller.
 */
final class UserSchema
{
    /** @var array<string, int> */
    public const REQUIRED = ['Username' => 16, 'Name' => 45, 'PaternalSurname' => 25];
    /** @var array<string, int> */
    public const OPTIONAL = ['MaternalSurname' => 25];
    public const STATUSES = ['Active', 'Inactive'];
    public const ROLES = ['God', 'Admin', 'User', 'Other'];

    /**
     * Validate a user payload. $partial (PATCH) checks only the fields sent.
     *
     * @param array<string, mixed> $data
     */
    public static function validate(array $data, bool $partial = false): void
    {
        foreach (self::REQUIRED + self::OPTIONAL as $field => $maxLength) {
            BaseSchema::validateString(
                $data,
                $field,
                $maxLength,
                required: array_key_exists($field, self::REQUIRED),
                partial: $partial,
            );
        }
        BaseSchema::validateEnum($data, 'UserStatus', self::STATUSES, $partial);
        if (array_key_exists('UserRole', $data)) {
            BaseSchema::validateEnum($data, 'UserRole', self::ROLES);
        }
    }
}
