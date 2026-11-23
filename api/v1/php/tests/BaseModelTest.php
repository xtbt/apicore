<?php
declare(strict_types=1);

namespace Apicore\Tests;

use Apicore\Models\BaseModel;
use ValueError;

/** BaseModel: column whitelist and PDO value binding, without a database. */
final class BaseModelTest extends TestCase
{
    public function testBindableCastsBooleansToInts(): void
    {
        $this->assertSame([1, 0, 'x', 5, null], BaseModelDouble::exposeBindable([true, false, 'x', 5, null]));
    }

    public function testFilterKeepsWritableColumns(): void
    {
        $this->assertSame(
            ['Name' => 'a', 'Status' => 'Active'],
            BaseModelDouble::exposeFilter(['Name' => 'a', 'Status' => 'Active']),
        );
    }

    public function testFilterDropsPrimaryKey(): void
    {
        $this->assertSame(['Name' => 'a'], BaseModelDouble::exposeFilter(['Id' => 9, 'Name' => 'a']));
    }

    public function testFilterRejectsUnknownColumn(): void
    {
        $error = $this->assertThrows(
            ValueError::class,
            static fn () => BaseModelDouble::exposeFilter(['Name' => 'a', 'Evil' => 'x']),
        );
        $this->assertSame('Unknown field(s): Evil', $error->getMessage());
    }

    public function testFilterRejectsEmptyPayload(): void
    {
        $this->assertThrows(ValueError::class, static fn () => BaseModelDouble::exposeFilter([]));
    }
}

/** Test double: skips the database connection and exposes the protected helpers. */
final class BaseModelDouble extends BaseModel
{
    protected const TABLE_NAME = 'double';
    protected const ID_COLUMN = 'Id';
    protected const COLUMNS = ['Name', 'Status'];

    public function __construct()
    {
        // No Database::connection(): these tests never touch SQL
    }

    /** @param list<mixed> $values */
    public static function exposeBindable(array $values): array
    {
        return self::bindable($values);
    }

    /** @param array<string, mixed> $data */
    public static function exposeFilter(array $data): array
    {
        return (new self())->filter($data);
    }
}
