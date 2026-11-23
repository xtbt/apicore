<?php
declare(strict_types=1);

namespace Apicore\Controllers;

use Apicore\Models\BaseModel;

/**
 * Base controller: generic CRUD flow shared by every entity.
 *
 * Layer: controllers. Entity controllers set MODEL_CLASS and SCHEMA, then
 * override prepare() or business hooks only when needed. It must never contain
 * SQL.
 */
abstract class BaseController
{
    protected const MODEL_CLASS = null;  // Model class of the entity (set by subclasses)
    protected const SCHEMA = null;       // Schema class exposing validate(array, bool)

    // Update results the Router maps to HTTP responses (see BaseModel::update)
    public const NOT_FOUND = BaseModel::NOT_FOUND;
    public const UNCHANGED = BaseModel::UNCHANGED;
    public const UPDATED = BaseModel::UPDATED;

    public ?string $authToken = null;  // Raw bearer token of the current request
    public ?array $authUser = null;    // Decoded payload of that token (null on public routes)
    public ?array $query = null;       // Query-string parameters (?page=1&size=10)

    protected ?BaseModel $model = null;

    public function __construct()
    {
        // A stateless controller (e.g. health check) declares MODEL_CLASS = null
        $this->model = static::MODEL_CLASS === null ? null : new (static::MODEL_CLASS)();
    }

    public function close(): void
    {
        $this->model?->close();
    }

    /**
     * Delegate field validation to SCHEMA, if the entity declares one.
     *
     * A schema class exposes validate(array $data, bool $partial = false).
     * Subclasses may override this hook when validation also needs
     * controller-level rules.
     *
     * @param array<string, mixed> $data
     */
    public function validate(array $data, bool $partial = false): void
    {
        if (static::SCHEMA !== null) {
            (static::SCHEMA)::validate($data, $partial);
        }
    }

    /**
     * Hook run after validate(): transform $data before it is stored.
     *
     * $recordId is null on create; $partial is true on PATCH, so a hook can tell
     * a full write (PUT) from a partial one.
     *
     * @param array<string, mixed> $data
     * @return array<string, mixed>
     */
    public function prepare(array $data, int|string|null $recordId = null, bool $partial = false): array
    {
        return $data;
    }

    /**
     * Hook for ownership rules. Throw ForbiddenError when the caller may not
     * touch the record.
     *
     * $action is 'update' (PUT/PATCH) or 'delete'; $data holds the fields being
     * written on update. Runs before any write, so a refused request never
     * changes data.
     *
     * @param array<string, mixed>|null $data
     */
    public function authorize(int|string $recordId, string $action, ?array $data = null): void
    {
    }

    /**
     * Hook run after authorize() and before the row is deleted.
     *
     * Use it for side effects that must happen only when the delete is allowed
     * (e.g. revoking the deleted user's tokens). A thrown exception aborts the
     * delete.
     */
    public function beforeDelete(int|string $recordId): void
    {
    }

    /** @param array<string, mixed> $data */
    public function create(array $data): int
    {
        $this->validate($data);
        return $this->model->create($this->prepare($data));
    }

    /** @return list<array<string, mixed>> */
    public function getAll(?int $page = null, ?int $size = null): array
    {
        return $this->model->getAll($page, $size);
    }

    /** @return array<string, mixed>|null */
    public function getById(int|string $recordId): ?array
    {
        return $this->model->getById($recordId);
    }

    /** Full update (PUT): every field rule is enforced. */
    public function update(int|string $recordId, array $data): string
    {
        return $this->write($recordId, $data, false);
    }

    /** Partial update (PATCH): only the fields sent are validated and written. */
    public function patch(int|string $recordId, array $data): string
    {
        return $this->write($recordId, $data, true);
    }

    /**
     * Shared PUT/PATCH flow: authorize, validate, prepare and persist.
     *
     * @param array<string, mixed> $data
     */
    private function write(int|string $recordId, array $data, bool $partial): string
    {
        $this->authorize($recordId, 'update', $data);
        $this->validate($data, $partial);
        return $this->model->update($recordId, $this->prepare($data, $recordId, $partial));
    }

    public function delete(int|string $recordId): bool
    {
        $this->authorize($recordId, 'delete');
        $this->beforeDelete($recordId);
        return $this->model->delete($recordId);
    }
}
