<?php
declare(strict_types=1);

namespace Apicore\Schemas;

use DateTimeImmutable;
use ValueError;

/**
 * Reusable field validators shared by every entity schema.
 *
 * Layer: schemas (cross-cutting). Pure functions over an array: no HTTP, no SQL,
 * no database access. Each entity schema composes these helpers.
 *
 * Every message matches the Python API word for word, so a client sees the same
 * error from either implementation.
 */
final class BaseSchema
{
    /**
     * Throw unless $data[$field] is one of $options.
     *
     * $partial (PATCH) skips the check when the field is absent.
     *
     * @param array<string, mixed> $data
     * @param list<string>         $options
     */
    public static function validateEnum(array $data, string $field, array $options, bool $partial = false): void
    {
        if ($partial && !array_key_exists($field, $data)) {
            return;
        }
        if (!in_array($data[$field] ?? null, $options, true)) {
            $quoted = array_map(static fn (string $option): string => '"' . $option . '"', $options);
            throw new ValueError($field . ' must be ' . implode(' or ', $quoted));
        }
    }

    /**
     * Throw unless $data[$field] is a string within $maxLength.
     *
     * $required rejects a missing or empty value. $partial (PATCH) skips the
     * check when the field is absent.
     *
     * @param array<string, mixed> $data
     */
    public static function validateString(
        array $data,
        string $field,
        ?int $maxLength = null,
        bool $required = false,
        bool $partial = false,
    ): void {
        if ($partial && !array_key_exists($field, $data)) {
            return;
        }
        $value = $data[$field] ?? null;
        if ($value !== null && !is_string($value)) {
            throw new ValueError($field . ' must be a string');
        }
        if ($required && ($value === null || $value === '')) {
            throw new ValueError($field . ' is required');
        }
        if ($value !== null && $value !== '' && $maxLength !== null && mb_strlen($value) > $maxLength) {
            throw new ValueError($field . ' must be ' . $maxLength . ' chars max');
        }
    }

    /**
     * Throw unless $data[$field] is a string of any length (TEXT column).
     *
     * @param array<string, mixed> $data
     */
    public static function validateText(
        array $data,
        string $field,
        bool $required = false,
        bool $partial = false,
    ): void {
        if ($partial && !array_key_exists($field, $data)) {
            return;
        }
        $value = $data[$field] ?? null;
        if ($value !== null && !is_string($value)) {
            throw new ValueError($field . ' must be a string');
        }
        if ($required && ($value === null || $value === '')) {
            throw new ValueError($field . ' is required');
        }
    }

    /**
     * Throw unless $data[$field] is an int inside the given range.
     *
     * bool is rejected on purpose: in PHP a bool is not a number a client should
     * send for an INT column.
     *
     * @param array<string, mixed> $data
     */
    public static function validateInteger(
        array $data,
        string $field,
        ?int $minimum = null,
        ?int $maximum = null,
        bool $required = false,
        bool $partial = false,
    ): void {
        if ($partial && !array_key_exists($field, $data)) {
            return;
        }
        $value = $data[$field] ?? null;
        if ($value === null) {
            if ($required) {
                throw new ValueError($field . ' is required');
            }
            return;
        }
        if (is_bool($value) || !is_int($value)) {
            throw new ValueError($field . ' must be an integer');
        }
        if ($minimum !== null && $value < $minimum) {
            throw new ValueError($field . ' must be ' . $minimum . ' or more');
        }
        if ($maximum !== null && $value > $maximum) {
            throw new ValueError($field . ' must be ' . $maximum . ' or less');
        }
    }

    /**
     * Throw unless $data[$field] is an int or float inside the given range.
     *
     * DECIMAL and FLOAT columns accept both; the database rounds to the column
     * scale.
     *
     * @param array<string, mixed> $data
     */
    public static function validateNumber(
        array $data,
        string $field,
        int|float|null $minimum = null,
        int|float|null $maximum = null,
        bool $required = false,
        bool $partial = false,
    ): void {
        if ($partial && !array_key_exists($field, $data)) {
            return;
        }
        $value = $data[$field] ?? null;
        if ($value === null) {
            if ($required) {
                throw new ValueError($field . ' is required');
            }
            return;
        }
        if (is_bool($value) || (!is_int($value) && !is_float($value))) {
            throw new ValueError($field . ' must be a number');
        }
        if ($minimum !== null && $value < $minimum) {
            throw new ValueError($field . ' must be ' . $minimum . ' or more');
        }
        if ($maximum !== null && $value > $maximum) {
            throw new ValueError($field . ' must be ' . $maximum . ' or less');
        }
    }

    /**
     * Throw unless $data[$field] is true or false (tinyint(1) column).
     *
     * @param array<string, mixed> $data
     */
    public static function validateBoolean(
        array $data,
        string $field,
        bool $required = false,
        bool $partial = false,
    ): void {
        if ($partial && !array_key_exists($field, $data)) {
            return;
        }
        $value = $data[$field] ?? null;
        if ($value === null) {
            if ($required) {
                throw new ValueError($field . ' is required');
            }
            return;
        }
        if (!is_bool($value)) {
            throw new ValueError($field . ' must be true or false');
        }
    }

    /**
     * Shared check for the date, datetime and time validators.
     *
     * @param array<string, mixed> $data
     */
    private static function validateIso(
        array $data,
        string $field,
        string $format,
        string $label,
        string $example,
        bool $required,
        bool $partial,
    ): void {
        if ($partial && !array_key_exists($field, $data)) {
            return;
        }
        $value = $data[$field] ?? null;
        if ($value === null) {
            if ($required) {
                throw new ValueError($field . ' is required');
            }
            return;
        }
        if (!is_string($value)) {
            throw new ValueError($field . ' must be a string');
        }
        $parsed = DateTimeImmutable::createFromFormat('!' . $format, $value);
        $errors = DateTimeImmutable::getLastErrors();
        $valid = $parsed !== false
            && ($errors === false || ($errors['warning_count'] === 0 && $errors['error_count'] === 0))
            && $parsed->format($format) === $value;
        if (!$valid) {
            throw new ValueError($field . ' must be a ' . $label . ' like ' . $example);
        }
    }

    /** Throw unless $data[$field] is a 'YYYY-MM-DD' string (DATE column). */
    public static function validateDate(
        array $data,
        string $field,
        bool $required = false,
        bool $partial = false,
    ): void {
        self::validateIso($data, $field, 'Y-m-d', 'date', '2026-01-31', $required, $partial);
    }

    /** Throw unless $data[$field] is 'YYYY-MM-DD HH:MM:SS' (DATETIME column). */
    public static function validateDatetime(
        array $data,
        string $field,
        bool $required = false,
        bool $partial = false,
    ): void {
        self::validateIso(
            $data,
            $field,
            'Y-m-d H:i:s',
            'datetime',
            '2026-01-31 08:30:00',
            $required,
            $partial,
        );
    }

    /** Throw unless $data[$field] is a 'HH:MM:SS' string (TIME column). */
    public static function validateTime(
        array $data,
        string $field,
        bool $required = false,
        bool $partial = false,
    ): void {
        self::validateIso($data, $field, 'H:i:s', 'time', '08:30:00', $required, $partial);
    }

    /** Throw unless $data[$field] is a four-digit year (YEAR column). */
    public static function validateYear(
        array $data,
        string $field,
        int $minimum = 1901,
        int $maximum = 2155,
        bool $required = false,
        bool $partial = false,
    ): void {
        if ($partial && !array_key_exists($field, $data)) {
            return;
        }
        $value = $data[$field] ?? null;
        if ($value === null) {
            if ($required) {
                throw new ValueError($field . ' is required');
            }
            return;
        }
        if (is_bool($value) || !is_int($value)) {
            throw new ValueError($field . ' must be an integer');
        }
        if ($value < $minimum || $value > $maximum) {
            throw new ValueError(
                $field . ' must be a four-digit year between ' . $minimum . ' and ' . $maximum
            );
        }
    }

    /**
     * Throw unless $data[$field] is an object or an array (JSON column).
     *
     * @param array<string, mixed> $data
     */
    public static function validateJson(
        array $data,
        string $field,
        bool $required = false,
        bool $partial = false,
    ): void {
        if ($partial && !array_key_exists($field, $data)) {
            return;
        }
        $value = $data[$field] ?? null;
        if ($value === null) {
            if ($required) {
                throw new ValueError($field . ' is required');
            }
            return;
        }
        if (!is_array($value)) {
            throw new ValueError($field . ' must be a JSON object or array');
        }
    }
}
