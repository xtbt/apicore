<?php
declare(strict_types=1);

namespace Apicore\Tests;

use Apicore\Schemas\BaseSchema;
use ValueError;

/** BaseSchema: the eleven validators, with the same messages as Python. */
final class SchemasTest extends TestCase
{
    public function testEnumAcceptsListedValue(): void
    {
        BaseSchema::validateEnum(['Status' => 'Active'], 'Status', ['Active', 'Inactive']);
        $this->assertTrue(true);
    }

    public function testEnumRejectsOtherValue(): void
    {
        $error = $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateEnum(['Status' => 'Nope'], 'Status', ['Active', 'Inactive']),
        );
        $this->assertSame('Status must be "Active" or "Inactive"', $error->getMessage());
    }

    public function testEnumPartialSkipsMissingField(): void
    {
        BaseSchema::validateEnum([], 'Status', ['Active'], true);
        $this->assertTrue(true);
    }

    public function testStringRejectsNonString(): void
    {
        $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateString(['Name' => 5], 'Name'),
        );
    }

    public function testStringRejectsTooLong(): void
    {
        $error = $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateString(['Name' => 'abcd'], 'Name', 3),
        );
        $this->assertSame('Name must be 3 chars max', $error->getMessage());
    }

    public function testStringRequiredRejectsEmpty(): void
    {
        $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateString(['Name' => ''], 'Name', null, true),
        );
    }

    public function testIntegerRejectsBool(): void
    {
        $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateInteger(['Qty' => true], 'Qty'),
        );
    }

    public function testIntegerRejectsFloat(): void
    {
        $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateInteger(['Qty' => 1.5], 'Qty'),
        );
    }

    public function testIntegerRange(): void
    {
        $error = $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateInteger(['Qty' => -1], 'Qty', 0),
        );
        $this->assertSame('Qty must be 0 or more', $error->getMessage());
    }

    public function testNumberAcceptsIntAndFloat(): void
    {
        BaseSchema::validateNumber(['Price' => 1], 'Price');
        BaseSchema::validateNumber(['Price' => 1.5], 'Price');
        $this->assertTrue(true);
    }

    public function testNumberRejectsString(): void
    {
        $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateNumber(['Price' => '1.5'], 'Price'),
        );
    }

    public function testBooleanRejectsInt(): void
    {
        $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateBoolean(['Active' => 1], 'Active'),
        );
    }

    public function testBooleanAcceptsTrueAndFalse(): void
    {
        BaseSchema::validateBoolean(['Active' => true], 'Active');
        BaseSchema::validateBoolean(['Active' => false], 'Active');
        $this->assertTrue(true);
    }

    public function testDateAcceptsIso(): void
    {
        BaseSchema::validateDate(['Born' => '2026-01-31'], 'Born');
        $this->assertTrue(true);
    }

    public function testDateRejectsBadFormat(): void
    {
        $error = $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateDate(['Born' => '31/01/2026'], 'Born'),
        );
        $this->assertSame('Born must be a date like 2026-01-31', $error->getMessage());
    }

    public function testDatetimeRejectsDateOnly(): void
    {
        $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateDatetime(['At' => '2026-01-31'], 'At'),
        );
    }

    public function testTimeAcceptsHms(): void
    {
        BaseSchema::validateTime(['Start' => '08:30:00'], 'Start');
        $this->assertTrue(true);
    }

    public function testTimeRejectsOutOfRange(): void
    {
        $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateTime(['Start' => '25:00:00'], 'Start'),
        );
    }

    public function testYearRange(): void
    {
        $error = $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateYear(['Year' => 1800], 'Year'),
        );
        $this->assertSame('Year must be a four-digit year between 1901 and 2155', $error->getMessage());
    }

    public function testYearAcceptsValid(): void
    {
        BaseSchema::validateYear(['Year' => 2026], 'Year');
        $this->assertTrue(true);
    }

    public function testJsonAcceptsObjectAndArray(): void
    {
        BaseSchema::validateJson(['Meta' => ['a' => 1]], 'Meta');
        BaseSchema::validateJson(['Meta' => [1, 2]], 'Meta');
        $this->assertTrue(true);
    }

    public function testJsonRejectsScalar(): void
    {
        $error = $this->assertThrows(
            ValueError::class,
            static fn () => BaseSchema::validateJson(['Meta' => 'text'], 'Meta'),
        );
        $this->assertSame('Meta must be a JSON object or array', $error->getMessage());
    }
}
