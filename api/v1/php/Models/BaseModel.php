<?php
declare(strict_types=1);

namespace Apicore\Models;

use Apicore\Core\Database;
use PDO;
use PDOException;
use ValueError;

/**
 * Base model: generic CRUD data access shared by every entity.
 *
 * Layer: models. Entity models only declare TABLE_NAME, ID_COLUMN and COLUMNS
 * (plus any query that is specific to that entity). It must never handle HTTP.
 */
abstract class BaseModel
{
    protected const TABLE_NAME = '';      // Table of the entity (set by subclasses)
    protected const ID_COLUMN = 'Id';     // Primary key column (override if different)
    protected const COLUMNS = [];         // Writable columns (whitelist, excludes the primary key)

    protected const HIDDEN_COLUMNS = [];  // Columns never returned by getAll/getById (e.g. passwords)

    // Results of update()
    public const NOT_FOUND = 'not_found';
    public const UNCHANGED = 'unchanged';
    public const UPDATED = 'updated';

    protected PDO $pdo;

    public function __construct()
    {
        // One connection per request, shared by every model instance
        $this->pdo = Database::connection();
    }

    public function close(): void
    {
        // The connection belongs to the request, so there is nothing to release
    }

    /**
     * Return only the writable columns of $data (primary key removed).
     *
     * Column names are interpolated into SQL, so unknown keys are rejected
     * (raises ValueError) to prevent SQL injection through the JSON body.
     *
     * @param array<string, mixed> $data
     * @return array<string, mixed>
     */
    protected function filter(array $data): array
    {
        // The primary key is auto-increment: never written by the client, so drop it
        unset($data[static::ID_COLUMN]);
        $unknown = array_diff(array_keys($data), static::COLUMNS);
        if ($unknown !== []) {
            throw new ValueError('Unknown field(s): ' . implode(', ', $unknown));
        }
        if ($data === []) {
            throw new ValueError('No data provided');
        }
        return $data;
    }

    /**
     * Insert a record. Returns the new id.
     *
     * @param array<string, mixed> $data
     */
    public function create(array $data): int
    {
        $data = $this->filter($data);
        $columns = implode(', ', array_keys($data));
        $placeholders = implode(', ', array_fill(0, count($data), '?'));
        try {
            $statement = $this->pdo->prepare(
                'INSERT INTO ' . static::TABLE_NAME . " ($columns) VALUES ($placeholders)"
            );
            $statement->execute(self::bindable(array_values($data)));
            return (int) $this->pdo->lastInsertId();
        } catch (PDOException $error) {
            if (self::isIntegrityViolation($error)) {
                throw new ValueError('Record already exists');  // UNIQUE key violated
            }
            throw $error;
        }
    }

    /**
     * Values ready to bind: PDO sends a bool as '' unless it is cast, and MySQL
     * rejects that for a tinyint column, so booleans become 1/0.
     *
     * @param list<mixed> $values
     * @return list<mixed>
     */
    protected static function bindable(array $values): array
    {
        return array_map(
            static fn ($value) => is_bool($value) ? (int) $value : $value,
            $values,
        );
    }

    /**
     * Remove HIDDEN_COLUMNS from a row (null passes through).
     *
     * @param array<string, mixed>|null $row
     * @return array<string, mixed>|null
     */
    protected function publicRow(?array $row): ?array
    {
        if ($row === null) {
            return null;
        }
        return array_diff_key($row, array_flip(static::HIDDEN_COLUMNS));
    }

    /**
     * Return records of the table, optionally paginated (page starts at 1).
     *
     * @return list<array<string, mixed>>
     */
    public function getAll(?int $page = null, ?int $size = null): array
    {
        $sql = 'SELECT * FROM ' . static::TABLE_NAME;
        $params = [];
        if ($size) {
            $sql .= ' LIMIT ? OFFSET ?';
            $params = [$size, (max($page ?? 1, 1) - 1) * $size];
        }
        $statement = $this->pdo->prepare($sql);
        foreach ($params as $index => $value) {
            $statement->bindValue($index + 1, $value, PDO::PARAM_INT);
        }
        $statement->execute();
        return array_map([$this, 'publicRow'], $statement->fetchAll());
    }

    /**
     * Return one record, or null when it does not exist.
     *
     * @return array<string, mixed>|null
     */
    public function getById(int|string $recordId): ?array
    {
        $statement = $this->pdo->prepare(
            'SELECT * FROM ' . static::TABLE_NAME . ' WHERE ' . static::ID_COLUMN . ' = ?'
        );
        $statement->execute([$recordId]);
        $row = $statement->fetch();
        return $this->publicRow($row === false ? null : $row);
    }

    /**
     * Update a record by id.
     *
     * Returns 'not_found' if the id does not exist, 'unchanged' if the sent
     * values equal the stored ones, or 'updated' after writing the changes.
     *
     * @param array<string, mixed> $data
     */
    public function update(int|string $recordId, array $data): string
    {
        $data = $this->filter($data);
        $columns = array_keys($data);
        try {
            // Read the current values (as a dict) of only the columns being modified
            $statement = $this->pdo->prepare(
                'SELECT ' . implode(', ', $columns) . ' FROM ' . static::TABLE_NAME
                . ' WHERE ' . static::ID_COLUMN . ' = ?'
            );
            $statement->execute([$recordId]);
            $current = $statement->fetch();
            if ($current === false) {
                return self::NOT_FOUND;
            }
            // Loose comparison: the driver may return "1" where the body sent 1
            if ($current == $data) {
                return self::UNCHANGED;
            }

            $setClause = implode(', ', array_map(static fn (string $key): string => "$key = ?", $columns));
            $statement = $this->pdo->prepare(
                'UPDATE ' . static::TABLE_NAME . ' SET ' . $setClause
                . ' WHERE ' . static::ID_COLUMN . ' = ?'
            );
            $statement->execute([...self::bindable(array_values($data)), $recordId]);
            return self::UPDATED;
        } catch (PDOException $error) {
            if (self::isIntegrityViolation($error)) {
                throw new ValueError('Record already exists');
            }
            throw $error;
        }
    }

    /**
     * Delete a record by id. Returns true if a row was deleted, false if the id
     * does not exist.
     */
    public function delete(int|string $recordId): bool
    {
        $statement = $this->pdo->prepare(
            'DELETE FROM ' . static::TABLE_NAME . ' WHERE ' . static::ID_COLUMN . ' = ?'
        );
        $statement->execute([$recordId]);
        return $statement->rowCount() > 0;
    }

    /** SQLSTATE 23000 is a constraint violation (duplicate key, foreign key). */
    private static function isIntegrityViolation(PDOException $error): bool
    {
        return $error->getCode() === '23000' || ($error->errorInfo[1] ?? null) === 1062;
    }
}
