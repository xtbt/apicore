<?php
declare(strict_types=1);

namespace Apicore\Models;

use ValueError;

/**
 * Example model: table definition plus the type conversions of `example`.
 *
 * Layer: models. This entity exists as a reference: it has one column per common
 * MySQL data type and shows where each conversion belongs.
 *
 * - JSON and BLOB are stored in a form MySQL understands and returned in a form
 *   JSON understands (object/array and base64 string).
 * - DECIMAL is returned as a string, never as a float: a float would lose the
 *   precision the column exists to keep.
 * - tinyint(1) becomes a bool and the date/time types become ISO strings.
 */
final class Example extends BaseModel
{
    protected const TABLE_NAME = 'example';
    protected const ID_COLUMN = 'ExampleId';
    protected const COLUMNS = [
        'ExampleName', 'ExampleCode', 'ExampleDescription', 'ExamplePrice',
        'ExampleQuantity', 'ExampleBigNumber', 'ExampleRatio', 'ExampleActive',
        'ExampleStatus', 'ExampleBirthDate', 'ExampleCreatedAt', 'ExampleStartTime',
        'ExampleYear', 'ExampleMetadata', 'ExamplePicture',
    ];

    private const JSON_COLUMNS = ['ExampleMetadata'];    // stored as text, returned as object/array
    private const BINARY_COLUMNS = ['ExamplePicture'];   // stored as bytes, returned as base64
    private const DECIMAL_COLUMNS = ['ExamplePrice'];    // Decimal -> string (keeps precision)
    private const BOOLEAN_COLUMNS = ['ExampleActive'];   // tinyint(1) -> bool
    private const DATE_COLUMNS = ['ExampleBirthDate'];   // date -> 'YYYY-MM-DD'
    private const DATETIME_COLUMNS = ['ExampleCreatedAt'];  // datetime -> 'YYYY-MM-DD HH:MM:SS'
    private const TIME_COLUMNS = ['ExampleStartTime'];   // time -> 'HH:MM:SS'
    private const INTEGER_COLUMNS = ['ExampleYear'];     // year -> int

    /**
     * Encode JSON and BLOB values before they reach the database.
     *
     * @param array<string, mixed> $data
     * @return array<string, mixed>
     */
    protected function filter(array $data): array
    {
        foreach (self::JSON_COLUMNS as $column) {
            if (array_key_exists($column, $data) && $data[$column] !== null) {
                $data[$column] = json_encode(
                    $data[$column],
                    JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES,
                );
            }
        }
        foreach (self::BINARY_COLUMNS as $column) {
            if (array_key_exists($column, $data) && $data[$column] !== null) {
                $decoded = base64_decode((string) $data[$column], true);
                if ($decoded === false) {
                    throw new ValueError($column . ' must be a base64 string');
                }
                $data[$column] = $decoded;
            }
        }
        return parent::filter($data);
    }

    /**
     * Decode the columns whose driver type is not JSON friendly.
     *
     * @param array<string, mixed>|null $row
     * @return array<string, mixed>|null
     */
    protected function publicRow(?array $row): ?array
    {
        $row = parent::publicRow($row);
        if ($row === null) {
            return null;
        }
        foreach (self::JSON_COLUMNS as $column) {
            if (isset($row[$column]) && is_string($row[$column])) {
                $row[$column] = json_decode($row[$column], true);
            }
        }
        foreach (self::BINARY_COLUMNS as $column) {
            if (isset($row[$column]) && is_resource($row[$column])) {
                $row[$column] = (string) stream_get_contents($row[$column]);
            }
            if (isset($row[$column]) && is_string($row[$column])) {
                $row[$column] = base64_encode($row[$column]);
            }
        }
        foreach (self::DECIMAL_COLUMNS as $column) {
            if (isset($row[$column])) {
                $row[$column] = (string) $row[$column];
            }
        }
        foreach (self::BOOLEAN_COLUMNS as $column) {
            if (isset($row[$column])) {
                $row[$column] = (bool) (int) $row[$column];
            }
        }
        foreach (self::DATE_COLUMNS as $column) {
            if (isset($row[$column])) {
                $row[$column] = (string) $row[$column];
            }
        }
        foreach (self::DATETIME_COLUMNS as $column) {
            if (isset($row[$column])) {
                $row[$column] = (string) $row[$column];
            }
        }
        foreach (self::TIME_COLUMNS as $column) {
            if (isset($row[$column])) {
                $row[$column] = (string) $row[$column];
            }
        }
        foreach (self::INTEGER_COLUMNS as $column) {
            if (isset($row[$column])) {
                $row[$column] = (int) $row[$column];
            }
        }
        return $row;
    }
}
