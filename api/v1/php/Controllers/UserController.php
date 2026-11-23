<?php
declare(strict_types=1);

namespace Apicore\Controllers;

use Apicore\Core\ForbiddenError;
use Apicore\Core\Security;
use Apicore\Models\User;
use Apicore\Models\UserToken;
use Apicore\Schemas\UserSchema;
use ValueError;

/**
 * User controller: validation rules and password handling of the `users` entity.
 *
 * Layer: controllers. The generic CRUD flow lives in BaseController; this class
 * adds the ownership rules, the role permissions and the password hashing.
 */
final class UserController extends BaseController
{
    protected const MODEL_CLASS = User::class;
    protected const SCHEMA = UserSchema::class;

    /** The only roles allowed to assign UserRole. */
    private const PRIVILEGED_ROLES = ['Admin', 'God'];
    // 'Other' is deliberately absent: it has exactly the same privileges as
    // 'User', so a student project can map its own extra roles onto it.

    /** The caller holds Admin or God (the roles that manage other users). */
    private function isPrivileged(): bool
    {
        return in_array($this->authUser['role'] ?? null, self::PRIVILEGED_ROLES, true);
    }

    /** The caller's token `sub` matches the record id being accessed. */
    private function ownsRecord(int|string $recordId): bool
    {
        return (string) $recordId === (string) ($this->authUser['sub'] ?? '');
    }

    /**
     * The user list is restricted to Admin and God.
     *
     * @return list<array<string, mixed>>
     */
    public function getAll(?int $page = null, ?int $size = null): array
    {
        if (!$this->isPrivileged()) {
            throw new ForbiddenError('Only Admin or God can list users');
        }
        return parent::getAll($page, $size);
    }

    /**
     * A user may read its own account; any other account is Admin/God only.
     *
     * @return array<string, mixed>|null
     */
    public function getById(int|string $recordId): ?array
    {
        if (!$this->isPrivileged() && !$this->ownsRecord($recordId)) {
            throw new ForbiddenError('You can only read your own account');
        }
        return parent::getById($recordId);
    }

    /**
     * Ownership rules for /users/{id}: own account, or Admin/God over others.
     *
     * - A plain User may only touch its own account (403 otherwise, without
     *   revealing whether the record exists).
     * - An Admin may not touch a God account.
     * - The last God account cannot be deleted nor lose its role.
     *
     * @param array<string, mixed>|null $data
     */
    public function authorize(int|string $recordId, string $action, ?array $data = null): void
    {
        if (!$this->isPrivileged() && !$this->ownsRecord($recordId)) {
            throw new ForbiddenError('You can only modify your own account');
        }
        $target = $this->model->getById($recordId);
        if ($target === null) {
            return;  // the model reports 404
        }
        $callerRole = $this->authUser['role'] ?? null;
        if ($callerRole === 'Admin' && $target['UserRole'] === 'God') {
            throw new ForbiddenError('Only God can modify a God account');
        }
        if ($target['UserRole'] !== 'God' || $this->model->countByRole('God') > 1) {
            return;
        }
        // Last God account: deleting it or changing its role would leave no God
        if ($action === 'delete') {
            throw new ForbiddenError('The last God account cannot be deleted');
        }
        if (($data['UserRole'] ?? 'God') !== 'God') {
            throw new ForbiddenError('The last God account cannot lose its role');
        }
    }

    /** Revoke every token of the user being deleted. */
    public function beforeDelete(int|string $recordId): void
    {
        $tokens = new UserToken();
        try {
            $tokens->deleteByUser($recordId);
        } finally {
            $tokens->close();
        }
    }

    /**
     * Reject duplicated usernames, enforce role permissions and store the
     * password hashed.
     *
     * The password is required on create and optional on update (omitted =
     * unchanged). Only Admin or God may assign a role other than 'User';
     * self-registration (public POST /users) always creates a plain 'User'.
     *
     * @param array<string, mixed> $data
     * @return array<string, mixed>
     */
    public function prepare(array $data, int|string|null $recordId = null, bool $partial = false): array
    {
        if (!$partial && !array_key_exists('UserRole', $data)) {
            $data['UserRole'] = 'User';  // self-registration and a PUT without a role default to User
        }
        if (array_key_exists('Username', $data)) {
            $existing = $this->model->findByUsername((string) $data['Username']);
            if ($existing !== null && (string) $existing['UserId'] !== (string) $recordId) {
                throw new ValueError('Username already exists');
            }
        }
        $role = $data['UserRole'] ?? null;
        $caller = $this->authUser['role'] ?? null;
        if ($role !== null && $role !== 'User') {
            if (!$this->isPrivileged()) {
                throw new ForbiddenError('Only Admin or God can assign roles');
            }
            if ($role === 'God' && $caller !== 'God') {
                throw new ForbiddenError('Only God can assign the God role');
            }
        }
        if (array_key_exists('Password', $data) && $data['Password'] !== null && !is_string($data['Password'])) {
            throw new ValueError('Password must be a string');
        }
        if (!empty($data['Password'])) {
            $data['Password'] = Security::hashPassword($data['Password']);
        } elseif ($recordId === null) {
            throw new ValueError('Password is required');
        } else {
            unset($data['Password']);
        }
        return $data;
    }
}
