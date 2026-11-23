<?php
declare(strict_types=1);

namespace Apicore\Models;

/**
 * UserToken model: table definition and queries specific to `users_tokens`.
 *
 * Layer: models. A user may own many rows (one per device/session); revoking a
 * token means deleting its row.
 */
final class UserToken extends BaseModel
{
    protected const TABLE_NAME = 'users_tokens';
    protected const ID_COLUMN = 'TokenId';
    protected const COLUMNS = ['UserId', 'TokenHash', 'TokenExpiration', 'TokenCreatedAt'];

    /** Delete rows matching $column = $value. Returns the number of deleted rows. */
    private function deleteWhere(string $column, int|string $value): int
    {
        $statement = $this->pdo->prepare('DELETE FROM ' . static::TABLE_NAME . " WHERE $column = ?");
        $statement->execute([$value]);
        return $statement->rowCount();
    }

    /**
     * Return [UserStatus, UserRole] of the owner of a valid token hash, or null.
     *
     * Null when the token does not exist or its TokenExpiration already passed,
     * so a row edited to an earlier date stops authorizing requests. The role is
     * read from the database on every request, so a role change applies
     * immediately instead of waiting for the token to expire.
     *
     * @return array{0: string, 1: string}|null
     */
    public function getUserState(string $tokenHash): ?array
    {
        $statement = $this->pdo->prepare(
            'SELECT u.UserStatus, u.UserRole FROM ' . static::TABLE_NAME . ' t '
            . 'JOIN users u ON u.UserId = t.UserId '
            . 'WHERE t.TokenHash = ? AND t.TokenExpiration > UTC_TIMESTAMP()'
        );
        $statement->execute([$tokenHash]);
        $row = $statement->fetch();
        return $row === false ? null : [(string) $row['UserStatus'], (string) $row['UserRole']];
    }

    /** Revoke one token. */
    public function deleteByHash(string $tokenHash): int
    {
        return $this->deleteWhere('TokenHash', $tokenHash);
    }

    /**
     * Housekeeping: delete tokens whose expiration date passed. Returns rows deleted.
     *
     * Persistent tokens hold a far-future date (year 9999), so they survive this.
     */
    public function deleteExpired(): int
    {
        $statement = $this->pdo->query(
            'DELETE FROM ' . static::TABLE_NAME . ' WHERE TokenExpiration < UTC_TIMESTAMP()'
        );
        return $statement === false ? 0 : $statement->rowCount();
    }

    /** Revoke every token of a user. */
    public function deleteByUser(int|string $userId): int
    {
        return $this->deleteWhere('UserId', $userId);
    }
}
