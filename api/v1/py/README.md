# apicore — API en Python

API REST en Python (solo biblioteca estándar + `mysql-connector-python`) sobre MySQL.
Pensada para que un alumno añada una entidad nueva escribiendo tres archivos cortos,
sin tocar el servidor, el router ni los middlewares.

Esta es la implementación en Python; la base de datos es compartida con la
implementación en PHP y su esquema vive en la raíz del repositorio.

## Requisitos

- Python 3.10 o superior
- MySQL 5.7 u 8.0 (MAMP, XAMPP o un servidor propio)
- Las dependencias de `requirements.txt`

```bash
python3 -m pip install -r requirements.txt
```

## Base de datos

El esquema completo está en `../../apicore.sql`, en la raíz del repositorio (crea la
base `apicore` y las tablas `users`, `moods` y `users_tokens`):

```bash
mysql -u root -p < ../../apicore.sql
```

## Configuración

El API lee `.env`. Las variables de entorno reales tienen prioridad sobre
ese archivo, así que en producción no hace falta el `.env`.

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

Para generar `JWT_SECRET`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

`generate_jwt_secret.py` es una alternativa que deriva la clave de una frase, pero
una frase débil no gana entropía: para producción, usa el comando de arriba.

Si falta una variable obligatoria, el servidor no arranca y dice cuál falta.

## Ejecutar

```bash
python3 main.py
```

El servidor es multi-hilo (`ThreadingHTTPServer`), habla HTTP/1.1 con keep-alive y
cierra el puerto limpiamente con Ctrl+C o `SIGTERM`.

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

La conversión vive en `models/example.py` (`_filter` al escribir, `_public` al leer) y la
validación en `schemas/example_schema.py`. Es el archivo que conviene copiar cuando una
entidad propia necesite JSON, binarios o fechas.

`ExamplePrice` se devuelve como **string** a propósito: `DECIMAL` existe para no perder
precisión en dinero, y convertir a `float` la perdería. Si tu entidad maneja importes,
haz lo mismo y deja el redondeo al cliente.

### Alcance y límites conocidos

Decisiones conscientes de esta BETA, para que no sorprendan a quien la use como base:

- **`/examples` no tiene regla de propiedad.** Cualquier usuario autenticado ve todas las
  filas, igual que en `/moods`. Es lo deseable para una tabla de referencia; si tu entidad
  necesita aislamiento por usuario, sobrescribe `authorize()` en el controlador.
- **El rate limiter vive en memoria y por proceso.** Se reinicia con el servidor y no se
  comparte entre instancias; con varios procesos cada uno lleva su propia cuenta.
- **`/health` consulta la base** con `SELECT 1` y responde 503 si no está disponible.
- **Sin migraciones.** `apicore.sql` es el esquema inicial; al añadir columnas hay que
  alterar la tabla a mano.
- **`http.server` no es para producción.** Sirve para enseñar y para desarrollo local;
  un despliegue real necesita un servidor WSGI/ASGI delante.

### CORS

Toda respuesta incluye `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`,
`Access-Control-Allow-Headers` y `Access-Control-Max-Age`, así que un frontend en otro
origen puede llamar al API sin proxy. Por defecto el origen permitido es `*`; para
restringirlo, define `CORS_ALLOW_ORIGIN` en el `.env` (por ejemplo
`CORS_ALLOW_ORIGIN=http://localhost:5173`).

### Colecciones de cliente

`insomnia_apicore.json` es la fuente de verdad: 32 solicitudes que cubren las 15 rutas,
más `HEAD`, `OPTIONS` y el preflight CORS. `postman_apicore.json` se genera desde ella:

```bash
python3 generate_postman_collection.py
```

Edita la colección de Insomnia y vuelve a ejecutar el script para mantener ambas sincronizadas.

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
inmediato y no hay que esperar a que caduque el token. Cinco intentos fallidos con el
mismo usuario bloquean ese usuario durante 15 minutos (429).

### Formato de las respuestas

```json
{"status": "ok", "data": {...}}
{"status": "ok", "ID": 12}
{"status": "ok", "message": "Mood updated"}
{"error": "Mood not found"}
```

Los errores usan siempre `{"error": "..."}` con el código HTTP correspondiente
(400 validación, 401 token, 403 permisos, 404 no existe, 405 método, 413 cuerpo
demasiado grande, 429 demasiados intentos, 503 servidor ocupado).

## Estructura

```
.
├── main.py              arranque y cableado del pipeline
├── server.py            adaptador HTTP: lee la petición y escribe la respuesta
├── core/                settings, logger, base de datos, router, seguridad, errores
│   └── http.py          Request y Response (solo datos, sin sockets)
├── middlewares/         error -> logging -> auth -> endpoint
├── controllers/         flujo CRUD genérico y reglas por entidad
├── models/              acceso a datos (SQL)
├── schemas/             validación de campos
├── services/            tokens
├── routers/             rutas, descubiertas automáticamente
├── utils/               fechas y zonas horarias
└── tests/unit           pruebas unitarias de esta implementación
```

Cada capa solo habla con la de al lado: los controladores no escriben SQL, los modelos
no conocen HTTP y los esquemas no tocan la base de datos.

## Añadir una entidad nueva

Con `notes` como ejemplo:

1. `models/note.py`: `TABLE_NAME`, `ID_COLUMN` y `COLUMNS`.
2. `schemas/note_schema.py`: `validate(data, partial=False)` con los helpers de
   `schemas/base_schema.py`.
3. `controllers/note_controller.py`: `MODEL_CLASS` y `SCHEMA`. Sobrescribe
   `prepare`, `authorize` o `before_delete` solo si hace falta.
4. `routers/note_router.py`: `register_routes(router)` con
   `router.add_crud_routes('/notes', NoteController, 'Note')`.

El router se descubre solo: no hay que registrar nada en `main.py`. Las seis rutas
CRUD quedan creadas y protegidas por token.

## Pruebas

Las pruebas de integración viven en la raíz (`../../tests/integration`) y son las mismas
para las dos implementaciones: hablan HTTP y no importan código de ninguna de las dos.
Se elige el servidor con `API_LANGUAGE`.

```bash
# Unitarias de esta implementación (no necesitan MySQL ni red)
python3 -m unittest discover -s tests -t .

# Integración contra el API en Python
cd ../.. && python3 -m unittest discover -s tests -t .

# Integración contra el API en PHP
cd ../.. && API_LANGUAGE=php python3 -m unittest discover -s tests -t .
```

- `tests/unit`: funciones puras, router, middlewares, controladores y el escritor de
  respuestas.
- `../../tests/integration`: arrancan el servidor en un puerto propio (65432, 65433,
  65434, 65438, 65439, 65440 para Python; +50 para PHP) y hablan HTTP real.
  **Necesitan MySQL con el esquema cargado**, que incluye las cuentas `godtest`,
  `admintest`, `usertest` y `othertest` (contraseña igual al usuario).

Las pruebas de integración crean usuarios y moods temporales y los borran al terminar.
Si un puerto queda ocupado por una corrida anterior, el módulo falla al arrancar:
localízalo con `lsof -nP -iTCP:65433 -sTCP:LISTEN` y ciérralo.

## Integración continua

`../../.github/workflows/tests.yml` ejecuta la suite completa en cada push y pull
request, con un servicio MySQL 8.0 y el esquema de `apicore.sql` cargado desde la raíz.
