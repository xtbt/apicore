<?php
declare(strict_types=1);

namespace Apicore\Models;

/**
 * User model: table definition and queries specific to `users`.
 *
 * Layer: models. The password hash is hidden from every response, but
 * findByUsername() returns it because login needs to verify it.
 */
final class User extends BaseModel
{
    protected const TABLE_NAME = 'users';
    protected const ID_COLUMN = 'UserId';
    protected const COLUMNS = [
        'Username', 'Password', 'Name', 'PaternalSurname', 'MaternalSurname', 'UserStatus', 'UserRole',
    ];
    protected const HIDDEN_COLUMNS = ['Password'];

    /**
     * Return the full row (including the password hash, for login) or null.
     *
     * @return array<string, mixed>|null
     */
    public function findByUsername(string $username): ?array
    {
        $statement = $this->pdo->prepare('SELECT * FROM ' . static::TABLE_NAME . ' WHERE Username = ?');
        $statement->execute([$username]);
        $row = $statement->fetch();
        return $row === false ? null : $row;
    }

    /** Number of users holding $role (used to protect the last God account). */
    public function countByRole(string $role): int
    {
        $statement = $this->pdo->prepare('SELECT COUNT(*) FROM ' . static::TABLE_NAME . ' WHERE UserRole = ?');
        $statement->execute([$role]);
        return (int) $statement->fetchColumn();
    }
}
