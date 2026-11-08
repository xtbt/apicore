# Persistent Agent Instructions — Python REST API (5-Layer Architecture)

## Project Purpose

This project is a **didactic REST API** built in pure Python (no external frameworks),
designed for university students. Its goal is for students to understand how a real
REST API works and is composed, building it layer by layer throughout the semester.

The agent must read this file at the start of every session and follow all rules
defined here before proposing or generating any code.

---

## Technical Constraints (always mandatory)

- **Python 3.10+ standard library only**, with one exception: `mysql-connector-python`
  is the only allowed third-party library, used exclusively for MySQL connectivity.
  Flask, FastAPI, Django, Pydantic, PyJWT, python-dotenv, requests and any other
  external package are strictly forbidden.
- **HTTP server:** `http.server.ThreadingHTTPServer` with a custom `BaseHTTPRequestHandler`.
- **JWT:** implemented manually using `hmac`, `hashlib`, `base64`, `json` and `time` (HS256 algorithm).
- **Password hashing:** `hashlib.pbkdf2_hmac` + random salt (`secrets`),
  comparison with `hmac.compare_digest`.
- **Database:** MySQL via `mysql-connector-python`. The database layer must be designed
  with an **abstract adapter interface** (`core/database.py`) so that switching to another
  DBMS (PostgreSQL, SQLite, etc.) requires changes only in `core/database.py` and a new
  adapter class — no changes in repositories or any other layer.
- **Configuration:** custom `.env` file reader (no libraries); feeds a `Settings` object.
- **Typing:** basic type hints on function signatures. Strict type validation is not required yet.
- **Language:** all code, comments, docstrings, and documentation must be written in **English**.
  No Spanish anywhere in the codebase.
- **Comments:** every relevant instruction or logic block must be commented to aid
  understanding by external developers. This includes inline comments on non-obvious
  operations, module-level docstrings explaining purpose and layer rules, and
  function/class docstrings (parameters, return values, exceptions raised).

When in doubt, **prioritize clarity and readability over brevity.**

---

## Architecture: 5 Layers

### Request flow

```
Client → Middlewares → Router → Controller → Service → Repository → Database
Client ← Middlewares ← Router ← Controller ← Service ← Repository ←──────────┘
```

### Dependency rule (never violate)

```
routers → controllers → services → repositories → models
```

`core`, `config`, `schemas`, `utils` and `middlewares` are cross-cutting:
they may be used by any layer, but **they never import from the layers above**
(exception: `auth_middleware` may use `core.security` and `core.database`).

Dependencies are **injected by constructor**: the service receives the repository;
the controller receives the service. All wiring happens exclusively in `app/container.py`.

### Layer responsibilities

| Layer | Does | Must never do |
|---|---|---|
| **routers** | Map HTTP method + URL to a controller method | Business logic, SQL |
| **controllers** | Read params/body, call the service, return HTTP status + JSON | Business rules, SQL |
| **services** | Business rules and orchestration across repositories | Know HTTP (request, status codes) |
| **repositories** | Only layer that runs SQL queries and returns models | Business rules |
| **models** | Represent the entity and its fields | Access the DB or handle HTTP |

---

## Folder Structure

```text
my_api/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Entry point: wires dependencies, middlewares, and starts ThreadingHTTPServer
│   ├── container.py                # Dependency composition (repositories → services → controllers)
│   ├── server.py                   # HTTP handler: parses request, runs middleware pipeline, dispatches to router
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py             # Reads .env and exposes the Settings object (HOST, PORT, JWT_SECRET, DB_*, etc.)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py             # Abstract DatabaseAdapter interface + MySQLAdapter implementation.
│   │   │                           # To switch DBMS: implement the adapter interface and update settings.
│   │   │                           # No other file should reference mysql-connector-python directly.
│   │   ├── exceptions.py           # AppError base + NotFoundError, ConflictError, UnauthorizedError,
│   │   │                           # ForbiddenError, BadRequestError — each carries its HTTP status_code
│   │   ├── http.py                 # Custom Request and Response classes (method, path, query,
│   │   │                           # headers, body, params, user)
│   │   ├── responses.py            # Standard response helpers: success(data, status) and error(message, status)
│   │   ├── logger.py               # Logging configuration (console + optional file output)
│   │   └── security.py            # Password hashing + JWT token generation and validation (see section below)
│   │
│   ├── middlewares/
│   │   ├── __init__.py             # Exports all middlewares and defines the default pipeline order
│   │   ├── base.py                 # Middleware contract and pipeline chain builder
│   │   ├── error_middleware.py     # Catches AppError/Exception and returns a uniform JSON response
│   │   ├── logging_middleware.py   # Logs method, route, status, duration (ms) and client IP
│   │   └── auth_middleware.py      # Validates JWT on protected routes; sets decoded payload in request.user
│   │
│   ├── routers/
│   │   ├── __init__.py             # Central registry: build_router(controllers)
│   │   ├── base_router.py          # Router class: add_route(method, pattern, handler, public=False),
│   │   │                           # supports /users/{id} path parameters and API prefix versioning
│   │   ├── health_router.py
│   │   ├── auth_router.py          # POST /auth/login
│   │   └── user_router.py          # Reference entity — template for all future entities
│   │
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── health_controller.py
│   │   ├── auth_controller.py
│   │   └── user_controller.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py         # Login: validates credentials, calls generate_token, persists token record
│   │   └── user_service.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── token_repository.py     # CRUD for the tokens table (store, lookup by jti, revoke)
│   │   └── user_repository.py      # Definitive method signatures with TODO where real SQL will go
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── token.py                # Token dataclass (id, user_id, jti, token_hash, expires_at,
│   │   │                           # is_persistent, created_at, is_revoked)
│   │   └── user.py                 # User dataclass (id, name, email, password_hash, role, created_at)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── base_schema.py          # serialize() and serialize_list() helpers
│   │   ├── token_schema.py         # Login response format (token, token_type, expires_at or null if persistent)
│   │   └── user_schema.py          # Output schema (never exposes password_hash); input schema skeleton (TODO)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── date_utils.py           # utc_now(), ISO 8601 formatting
│       ├── pagination.py           # calculate_offset(page, size), build_page_meta(...)
│       └── string_utils.py         # String cleanup, email normalization
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_security.py        # Password hashing and JWT (generate, verify, expired, invalid signature,
│   │   │                           # persistent token, min_remaining logic)
│   │   └── test_router.py          # Route matching with path parameters
│   └── integration/
│       └── __init__.py
│
├── migrations/                     # Versioned SQL scripts (001_create_users.sql, 002_create_tokens.sql, ...)
├── scripts/                        # Utilities: seed data, maintenance tasks
├── docs/                           # Endpoint documentation and design decisions
├── .env                            # Development values (never commit to the repository)
├── .env.example                    # Template without real sensitive values
├── .gitignore
├── requirements.txt                # Only: mysql-connector-python (pinned version)
└── README.md
```

---

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Environment: `development`, `production` |
| `DEBUG` | `false` | Expose tracebacks to client when `true` |
| `HOST` | `localhost` | Server host |
| `PORT` | `8000` | Server port |
| `API_PREFIX` | `/api/v1` | Route prefix (enables future versioning) |
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_NAME` | — | Database name |
| `DB_USER` | — | Database user |
| `DB_PASSWORD` | — | Database password |
| `DB_POOL_SIZE` | `5` | Connection pool size |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `JWT_SECRET` | — | Token signing secret (server refuses to start if missing) |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm |
| `TOKEN_LIFETIME_MINUTES` | `60` | Default token lifetime in minutes |
| `TOKEN_MIN_REMAINING_MINUTES` | `10` | Minutes left before client should request a new token |

---

## Database Abstraction Layer (`core/database.py`)

The file must define:

1. **`DatabaseAdapter` (abstract base class):** declares the interface every adapter must implement:
   `connect()`, `disconnect()`, `execute(query, params)`, `fetchone()`, `fetchall()`,
   `commit()`, `rollback()`. No DBMS-specific code here.

2. **`MySQLAdapter(DatabaseAdapter)`:** concrete implementation using `mysql-connector-python`.
   Manages a thread-safe connection pool (`DB_POOL_SIZE` connections). This is the
   **only file** that imports `mysql.connector`.

3. **`get_db() -> DatabaseAdapter`:** factory function that returns the configured adapter
   instance. Called by repositories — they never instantiate an adapter directly.

> **To switch DBMS:** implement a new adapter class (e.g. `PostgreSQLAdapter`) in this same
> file (or a new file in `core/`), update `get_db()` to return it, and update `.env`.
> No other file changes are required.

---

## Security: mandatory functions in `core/security.py`

The agent must preserve these exact signatures at all times and must not alter
them without explicit instruction:

```python
# --- Password hashing ---
# Produces a self-contained string: "algorithm$iterations$salt$hash"
# so the verifier needs no extra parameters
hash_password(password: str) -> str
verify_password(password: str, stored_hash: str) -> bool

# --- Base64 URL encoding (used internally for JWT) ---
base64url_encode(data: bytes) -> str
base64url_decode(data: str) -> bytes

# --- Token generation ---
# lifetime_minutes   : how long the token is valid; ignored when persistent=True
# min_remaining_minutes : minimum remaining lifetime the client should check before
#                         requesting a new token; stored as a claim so the client
#                         can decide when to call /auth/login again
# persistent         : if True, the token has no expiration (expires_at = None in DB)
# extra_claims       : additional key/value pairs merged into the JWT payload
# Returns the signed JWT string AND persists a record in the tokens table via token_repository
generate_token(
    user_id: int,
    role: str,
    lifetime_minutes: int,
    min_remaining_minutes: int,
    persistent: bool = False,
    extra_claims: dict = None
) -> str

# --- Token validation ---
# Verifies signature, expiration (skipped for persistent tokens) and that the
# jti exists in the tokens table and is not revoked
decode_token(token: str) -> dict

# --- Convenience helper used by auth_service ---
# Builds and returns: {"token": <str>, "token_type": "Bearer",
#                      "expires_at": <ISO8601 or null>, "min_remaining_minutes": <int>}
build_token_response(token: str) -> dict
```

> **Multiple tokens per user:** the `tokens` table links to `users` via `user_id`.
> A user may hold any number of active tokens (e.g. different devices or sessions).
> `decode_token` always looks up the `jti` in the tokens table to confirm the token
> is active and not revoked. Revocation is performed by setting `is_revoked = TRUE`
> for the matching row.

**Tokens table schema (reference for migrations):**

```sql
CREATE TABLE tokens (
    id            INT          PRIMARY KEY AUTO_INCREMENT,
    user_id       INT          NOT NULL,         -- FK → users.id
    jti           VARCHAR(64)  NOT NULL UNIQUE,  -- JWT ID, used for lookup and revocation
    token_hash    VARCHAR(128) NOT NULL,          -- SHA-256 of the raw token (for fast lookup)
    expires_at    DATETIME     DEFAULT NULL,      -- NULL means persistent (no expiration)
    is_persistent TINYINT(1)   NOT NULL DEFAULT 0,
    min_remaining_minutes INT  NOT NULL DEFAULT 0,
    created_at    DATETIME     NOT NULL,
    is_revoked    TINYINT(1)   NOT NULL DEFAULT 0
);
```

---

## Middleware Pipeline

Execution order (outermost to innermost):

```
error_middleware → logging_middleware → auth_middleware → router
```

- **error_middleware:** converts `AppError` to its `status_code`; any other exception
  becomes a 500. Never exposes the traceback to the client unless `DEBUG=true`;
  always logs it.
- **logging_middleware:** records `IP METHOD ROUTE STATUS DURATIONms` on every request.
- **auth_middleware:** on protected routes, requires `Authorization: Bearer <token>`,
  calls `decode_token()`, and sets the decoded payload on `request.user`.
  Returns 401 on any failure. The hook `require_role(*roles)` is left prepared
  (commented and documented) for when role-based authorization is implemented.

---

## Initial Endpoints

| Method | Route | Public | Description |
|---|---|---|---|
| GET | `/health` | Yes | Service status |
| POST | `/auth/login` | Yes | Validates credentials and returns a token |
| GET | `/users` | No | Paginated user list (params: page, size) |
| GET | `/users/{id}` | No | User detail |
| POST | `/users` | No | Create user |
| PUT | `/users/{id}` | No | Update user |
| DELETE | `/users/{id}` | No | Delete user |

---

## Verification Checklist (run after every change)

Before marking a task complete, the agent must confirm:

1. `python -m app.main` starts with no errors and without installing anything beyond `mysql-connector-python`.
2. `GET /health` returns 200 with JSON.
3. `POST /auth/login` with the seed user returns a valid token; a record is inserted in the `tokens` table.
4. `GET /users` without token returns 401; with valid token returns 200; with expired or tampered token returns 401.
5. Using a revoked token returns 401.
6. A persistent token (`persistent=True`) never expires.
7. An unknown route returns 404 (JSON); a known route with wrong method returns 405 (JSON).
8. Every request is logged by the logging middleware.
9. `python -m unittest discover tests/unit` passes.
10. No layer violates the dependency rule.

---

## Comment Conventions

- Every file opens with a **module docstring** stating: what it is, which layer it belongs
  to, and what it must never contain.
- Every class and function has a docstring: what it does, parameters, return value,
  exceptions raised.
- Inline comments on every non-obvious block or operation (HMAC signing, route parsing,
  middleware chaining, pool management, etc.).
- Pending items are marked `# TODO: <description>` with a note on when they will be addressed.
- `__init__.py` files carry a short comment explaining the package's purpose.

---

## How to Add a New Entity

When instructed to add an entity (e.g. `Product`), the agent must create
**exactly these files**, in this order, without modifying files of other entities:

1. `app/models/product.py` — dataclass with the entity fields.
2. `app/repositories/product_repository.py` — definitive method signatures with `TODO` for SQL.
3. `app/services/product_service.py` — business rules; receives the repository by constructor.
4. `app/schemas/product_schema.py` — output schema and input schema skeleton (TODO for validation).
5. `app/controllers/product_controller.py` — HTTP layer; receives the service by constructor.
6. `app/routers/product_router.py` — entity routes with the correct `public` flag.
7. Register the router in `app/routers/__init__.py`.
8. Register dependencies in `app/container.py`.

---

## Roadmap (incremental implementation)

This project is built incrementally. Each stage adds a well-defined set of functionality
on top of the previous one. The agent must implement only what corresponds to the current
stage and must not anticipate future stages.

| Stage | What is added |
|---|---|
| **1 — Skeleton** | Full folder structure, all empty files with module docstrings, `.env.example`, `README.md` |
| **2 — Core infrastructure** | `Settings`, `DatabaseAdapter` + `MySQLAdapter`, custom `Request`/`Response`, `AppError` hierarchy, `Logger` |
| **3 — Middleware pipeline** | `error_middleware`, `logging_middleware`, `auth_middleware`, pipeline builder in `base.py` |
| **4 — Router and server** | `Router` with path parameters and `public` flag, `ThreadingHTTPServer` handler, `main.py` startup |
| **5 — Security and tokens** | `hash_password`, `verify_password`, `generate_token`, `decode_token`, `build_token_response`; `Token` model + `token_repository` |
| **6 — Auth endpoint** | `auth_service`, `auth_controller`, `auth_router`; seed user; full login → token → protected route flow working end to end |
| **7 — User entity** | `User` model, `user_repository` (SQL stubs), `user_service`, `user_schema`, `user_controller`, `user_router`; all 5 CRUD endpoints |
| **8 — Real SQL** | Actual MySQL queries in repositories once the table design is provided; migrations in `migrations/` |
| **9 — Input validation** | Input schemas with field-level validation rules |
| **10 — Roles and permissions** | `require_role` middleware hook, role column in users, route-level authorization |
| **11 — Integration tests** | End-to-end tests per entity in `tests/integration/` |
| **12 — Advanced features** | Pagination, filters, token revocation audit log, additional entities as defined by the project |
