# apicore — API en PHP

API REST en PHP 8 sobre MySQL, sin dependencias externas: ni Composer ni frameworks.
Es la contraparte exacta de la implementación en Python: mismo contrato, mismos códigos
de estado, mismos mensajes de error y la misma base de datos, así que un cliente puede
apuntar a cualquiera de las dos sin cambios.

Pensada para que un alumno añada una entidad nueva escribiendo tres archivos cortos,
sin tocar el arranque, el router ni los middlewares.

## Requisitos

- PHP 8.0 o superior con las extensiones `pdo_mysql`, `json` y `mbstring`
- MySQL 5.7 u 8.0 (MAMP, XAMPP o un servidor propio)

Comprueba las extensiones con:

```bash
php -m | grep -E 'pdo_mysql|json|mbstring'
```

No hace falta Composer: `Core/Autoloader.php` resuelve el espacio de nombres
`Apicore\` en una docena de líneas.

## Base de datos

El esquema completo está en `../../apicore.sql`, en la raíz del repositorio (crea la
base `apicore` y las tablas `users`, `moods`, `examples` y `users_tokens`):

```bash
mysql -u root -p < ../../apicore.sql
```

Es la misma base que usa la implementación en Python, incluidas las cuentas de prueba
`godtest`, `admintest`, `usertest` y `othertest` (contraseña igual al usuario).

## Configuración

El API lee `.env`. Las variables de entorno reales tienen prioridad sobre ese archivo,
así que en producción no hace falta el `.env`. Copia `.env.example` y ajusta los valores.

| Variable | Por defecto | Obligatoria | Uso |
| --- | --- | --- | --- |
| `APP_HOST` | `localhost` | no | Interfaz donde escucha el servidor |
| `APP_PORT` | `8000` | no | Puerto donde escucha el servidor |
| `APP_TIMEZONE` | `America/Tijuana` | no | Zona con la que se muestran las fechas |
| `DB_HOST` | `localhost` | no | Host de MySQL |
| `DB_PORT` | `3306` | no | Puerto de MySQL |
| `DB_NAME` | — | sí | Nombre de la base |
| `DB_USER` | — | sí | Usuario de MySQL |
| `DB_PASSWORD` | — | sí | Contraseña de MySQL |
| `JWT_SECRET` | — | sí | Clave con la que se firman los tokens |
| `JWT_ALGORITHM` | `HS256` | no | Algoritmo de firma |
| `TOKEN_LIFETIME_MINUTES` | `60` | no | Vida del token |
| `TOKEN_MIN_REMAINING_MINUTES` | `10` | no | Minutos restantes que el cliente usa para renovar |
| `CORS_ALLOW_ORIGIN` | `*` | no | Origen permitido por CORS |

`JWT_SECRET` debe ser **el mismo valor** que usa la implementación en Python: así un
token emitido por una vale en la otra. Los hashes de contraseña también son
intercambiables, porque ambos usan PBKDF2-SHA256 con el mismo formato.

Si falta una variable obligatoria, el servidor no arranca y dice cuál falta.

## Ejecutar

```bash
php -S localhost:8000 index.php
```

`index.php` es el único archivo que ejecuta el servidor: carga el autoloader y arranca
`Core\Application`. Para atender peticiones en paralelo, arranca varios workers:

```bash
PHP_CLI_SERVER_WORKERS=8 php -S localhost:8000 index.php
```

Sin `PHP_CLI_SERVER_WORKERS` el servidor CLI atiende una petición a la vez.

## Endpoints

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/health` | público | Vida y base de datos: 200 si responde, 503 si no |
| POST | `/auth/login` | público | Devuelve un token |
| POST | `/auth/logout` | token | Revoca el token usado |
| GET | `/users` | Admin, God | Lista paginada |
| GET | `/users/{id}` | propio, Admin, God | Lee una cuenta |
| POST | `/users` | público | Autorregistro (siempre rol `User`) |
| PUT | `/users/{id}` | propio, Admin, God | Actualización completa |
| PATCH | `/users/{id}` | propio, Admin, God | Actualización parcial |
| DELETE | `/users/{id}` | propio, Admin, God | Borra la cuenta y sus tokens |
| GET | `/moods` | token | Lista paginada |
| GET | `/moods/{id}` | token | Lee un registro |
| POST | `/moods` | token | Crea |
| PUT | `/moods/{id}` | token | Actualización completa |
| PATCH | `/moods/{id}` | token | Actualización parcial |
| DELETE | `/moods/{id}` | token | Borra |
| GET | `/examples` | token | Lista paginada |
| GET | `/examples/{id}` | token | Lee un registro |
| POST | `/examples` | token | Crea |
| PUT | `/examples/{id}` | token | Actualización completa |
| PATCH | `/examples/{id}` | token | Actualización parcial |
| DELETE | `/examples/{id}` | token | Borra |

Todas las rutas aceptan `OPTIONS` (204 con la cabecera `Allow`) y `HEAD` donde hay `GET`.
`POST` sobre una colección devuelve `201` con la cabecera `Location` apuntando al registro creado.

### Roles

`God`, `Admin`, `User` y `Other`. `Other` tiene exactamente los mismos privilegios que
`User`: existe para que un proyecto de curso pueda mapear sus propios roles sin tocar el
`enum` de la base. Solo `Admin` y `God` pueden asignar un rol, y solo `God` puede asignar
`God`.

### La entidad `example`

`/examples` es una tabla de referencia con una columna por tipo de dato común, para que
veas cómo viaja cada tipo de extremo a extremo:

| Columna | Tipo MySQL | En el JSON |
| --- | --- | --- |
| `ExampleName` | `varchar(45)` | string, obligatorio |
| `ExampleCode` | `char(3)` | string de 3 caracteres |
| `ExampleDescription` | `text` | string sin límite |
| `ExamplePrice` | `decimal(10,2)` | string `"19.99"`, nunca float |
| `ExampleQuantity` | `int` | entero |
| `ExampleBigNumber` | `bigint` | entero grande |
| `ExampleRatio` | `float` | número |
| `ExampleActive` | `tinyint(1)` | `true` / `false` |
| `ExampleStatus` | `enum` | `"Active"` / `"Inactive"` |
| `ExampleBirthDate` | `date` | `"YYYY-MM-DD"` |
| `ExampleCreatedAt` | `datetime` | `"YYYY-MM-DD HH:MM:SS"` |
| `ExampleStartTime` | `time` | `"HH:MM:SS"` |
| `ExampleYear` | `year` | entero entre 1901 y 2155 |
| `ExampleMetadata` | `json` | objeto o arreglo |
| `ExamplePicture` | `blob` | string base64, 87380 caracteres máximo |

La conversión vive en `Models/Example.php` (`filter` al escribir, `publicRow` al leer) y
la validación en `Schemas/ExampleSchema.php`. Es el archivo que conviene copiar cuando una
entidad propia necesite JSON, binarios o fechas.

`ExamplePrice` se devuelve como **string** a propósito: `DECIMAL` existe para no perder
precisión en dinero, y convertir a `float` la perdería.

### Alcance y límites conocidos

- **`/examples` no tiene regla de propiedad.** Cualquier usuario autenticado ve todas las
  filas, igual que en `/moods`. Si tu entidad necesita aislamiento por usuario, sobrescribe
  `authorize()` en el controlador.
- **El rate limiter vive en memoria y por proceso.** Se reinicia con el servidor y no se
  comparte entre workers.
- **`/health` consulta la base** con `SELECT 1` y responde 503 si no está disponible.
- **Sin migraciones.** `apicore.sql` es el esquema inicial; al añadir columnas hay que
  alterar la tabla a mano.
- **`php -S` no es para producción.** Es el servidor de desarrollo de PHP; un despliegue
  real necesita PHP-FPM detrás de Nginx o Apache.
- **El servidor CLI bufferiza el cuerpo antes de ejecutar el script.** Un `Content-Length`
  mayor de 1 MB se rechaza con 413 en cuanto llega el cuerpo, pero no solo con las
  cabeceras como hace Python. Un `Content-Length` no numérico lo rechaza el propio
  servidor cerrando la conexión, sin respuesta JSON.

### CORS

Toda respuesta incluye `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`,
`Access-Control-Allow-Headers` y `Access-Control-Max-Age`, así que un frontend en otro
origen puede llamar al API sin proxy. Por defecto el origen permitido es `*`; para
restringirlo, define `CORS_ALLOW_ORIGIN` en el `.env`.

### Colecciones de cliente

Las colecciones viven en la raíz del repositorio porque no dependen del lenguaje:
`insomnia_apicore.json` es la fuente de verdad y `postman_apicore.json` se genera desde
ella. Ambas apuntan a `http://localhost:8000` por defecto; cambia la variable `base_url`
si tu servidor escucha en otro puerto.

```bash
python3 generate_postman_collection.py
```

### Paginación

`GET /moods?page=1&size=20`. `page` empieza en 1 y `size` no puede pasar de 100.
Sin `size`, se devuelven todos los registros.

### Autenticación

```http
Authorization: Bearer <token>
```

`POST /auth/login` recibe `Username` y `Password`, y opcionalmente `Persistent: true`
para un token sin caducidad. La respuesta incluye `token`, `token_type`, `expires_at`,
`persistent` y `min_remaining_minutes`.

El rol se lee de la base en cada petición, así que un cambio de rol se aplica de
inmediato. Cinco intentos fallidos con el mismo usuario bloquean ese usuario durante
15 minutos (429).

### Formato de las respuestas

```json
{"status": "ok", "data": {...}}
{"status": "ok", "ID": 12}
{"status": "ok", "message": "Mood updated"}
{"error": "Mood not found"}
```

Los errores usan siempre `{"error": "..."}` con el código HTTP correspondiente
(400 validación, 401 token, 403 permisos, 404 no existe, 405 método, 413 cuerpo
demasiado grande, 429 demasiados intentos, 503 base no disponible).

## Estructura

```
.
├── index.php            arranque: autoloader y Application::boot()->run()
├── Core/                settings, logger, base de datos, router, seguridad, errores
│   ├── Application.php  raíz de composición: router, pipeline y emisión
│   ├── Errors.php       AppError y sus subclases con su código HTTP
│   ├── Request.php      datos de la petición, sin sockets
│   └── Response.php     datos de la respuesta, sin sockets
├── Middlewares/         cors -> error -> logging -> auth -> endpoint
├── Controllers/         flujo CRUD genérico y reglas por entidad
├── Models/              acceso a datos (SQL)
├── Schemas/             validación de campos
├── Services/            tokens
├── Routers/             rutas, descubiertas automáticamente
└── tests/               pruebas unitarias de esta implementación
```

Cada capa solo habla con la de al lado: los controladores no escriben SQL, los modelos
no conocen HTTP y los esquemas no tocan la base de datos.

## Añadir una entidad nueva

Con `notes` como ejemplo:

1. `Models/Note.php`: `TABLE_NAME`, `ID_COLUMN` y `COLUMNS`.
2. `Schemas/NoteSchema.php`: `validate(array $data, bool $partial = false)` con los
   helpers de `Schemas/BaseSchema.php`.
3. `Controllers/NoteController.php`: `MODEL_CLASS` y `SCHEMA`. Sobrescribe `prepare`,
   `authorize` o `beforeDelete` solo si hace falta.
4. `Routers/NoteRouter.php`: `register(Router $router)` con
   `$router->addCrudRoutes('/notes', NoteController::class, 'Note')`.

El router se descubre solo: no hay que registrar nada en `index.php`. Las seis rutas
CRUD quedan creadas y protegidas por token.

## Pruebas

Las pruebas de integración viven en la raíz (`../../tests/integration`) y son las mismas
para las dos implementaciones: hablan HTTP y no importan código de ninguna de las dos.
Se elige el servidor con `API_LANGUAGE`.

```bash
# Unitarias de esta implementación (no necesitan MySQL ni red)
php tests/run.php

# Integración contra el API en PHP
cd ../.. && API_LANGUAGE=php python3 -m unittest discover -s tests -t .
```

- `tests/`: router, respuesta, errores, seguridad, esquemas, modelo base, rate limiter,
  middlewares y tokens. El runner es propio (`tests/run.php`), sin Composer ni PHPUnit,
  e imprime el mismo informe que `unittest`. Sale con código 1 si algo falla.
- `../../tests/integration`: arrancan el servidor en un puerto propio y hablan HTTP real.
  **Necesitan MySQL con el esquema cargado.**

No hay equivalente a `test_server.py` de Python: en PHP el socket lo posee `php -S`, así
que la emisión de la respuesta se verifica con las pruebas de integración.

## Integración continua

`../../.github/workflows/tests.yml` ejecuta las dos suites en cada push y pull request,
con un servicio MySQL 8.0 y el esquema de `apicore.sql` cargado desde la raíz.
