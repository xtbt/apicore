# apicore

API REST sobre MySQL implementada dos veces, una por lenguaje, con el mismo contrato
y la misma base de datos:

| Implementación | Ruta | Documentación | Estado |
| --- | --- | --- | --- |
| Python | `api/v1/py` | [`README.md`](api/v1/py/README.md) | completa y probada |
| PHP | `api/v1/php` | [`README.md`](api/v1/php/README.md) | completa y probada |

Ambas comparten el esquema de `apicore.sql`, en la raíz del repositorio, y exponen los
mismos endpoints, códigos de estado y formato de respuesta, de modo que un cliente
puede apuntar a cualquiera de las dos sin cambios. Los tokens y los hashes de
contraseña son intercambiables: un token emitido por una implementación vale en la
otra, siempre que ambas usen el mismo `JWT_SECRET`.

## Cómo fluye una petición

Esta sección explica el recorrido completo de una petición HTTP. El orden es idéntico en
Python y en PHP; solo cambian los nombres de los archivos, que se indican en cada capa.

```text
Cliente
  │  POST /moods   Authorization: Bearer <token>   {"MoodName": "Happy", ...}
  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 1. Punto de entrada     server.py  /  index.php + Core/Application   │
│    Lee método, ruta, cabeceras y cuerpo. No decide nada del negocio. │
└──────────────────────────────────────────────────────────────────────┘
  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 2. Pipeline de middlewares                                           │
│    CORS  →  Errores  →  Logging  →  Auth                             │
│    Cada uno envuelve al siguiente: ve la petición al entrar y la     │
│    respuesta al salir, en orden inverso.                             │
└──────────────────────────────────────────────────────────────────────┘
  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 3. Router               core/router.py  /  Core/Router.php           │
│    Busca la ruta, extrae {id} de la URL y crea el controlador.       │
└──────────────────────────────────────────────────────────────────────┘
  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 4. Controlador          controllers/mood_controller.py               │
│    validate → prepare → authorize → llama al modelo                  │
└──────────────────────────────────────────────────────────────────────┘
  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 5. Modelo               models/mood.py  /  Models/Mood.php           │
│    Ejecuta SQL parametrizado contra MySQL y devuelve filas.          │
└──────────────────────────────────────────────────────────────────────┘
  ▼
Respuesta JSON  ←  se serializa y se escribe en la conexión
```

### Qué hace cada capa

| Capa | Responsabilidad | Lo que **no** debe hacer |
| --- | --- | --- |
| Punto de entrada | Leer la petición y escribir la respuesta | Decidir reglas de negocio |
| Middlewares | Preocupaciones transversales: CORS, errores, logs, autenticación | Conocer entidades concretas |
| Router | Mapear método + ruta a un controlador | Contener SQL ni validaciones |
| Controlador | Orquestar: validar, autorizar, preparar y llamar al modelo | Escribir SQL |
| Modelo | Traducir entre filas de MySQL y diccionarios/arreglos | Decidir permisos |
| Schema | Validar tipos, rangos y campos obligatorios | Tocar la base de datos |

La regla que sostiene todo: **cada capa solo habla con la de al lado**. El controlador no
sabe qué tabla existe; el modelo no sabe quién es el usuario; el router no sabe validar.
Por eso se pueden probar por separado y por eso agregar una entidad no obliga a tocar las
demás.

### Ejemplo completo: crear un mood

1. El cliente envía `POST /moods` con su token y el cuerpo
   `{"MoodName": "Happy", "MoodStatus": "Active"}`.
2. El **punto de entrada** lee el cuerpo y comprueba que no exceda 1 MB.
3. **CORS** añade las cabeceras `Access-Control-*` a la respuesta que venga después.
4. **Errores** se coloca por dentro: si algo lanza una excepción, la convierte en
   `{"error": "..."}` con el código adecuado.
5. **Logging** anota método, ruta, estado y duración.
6. **Auth** lee `Authorization: Bearer <token>`, verifica la firma HS256, comprueba que el
   token siga vivo en `users_tokens` y deja el usuario en `request.user`. Si falta o es
   inválido, responde `401` y **no se ejecuta nada más**.
7. El **router** encuentra `POST /moods`, crea `MoodController` y le pasa el cuerpo.
8. El **controlador** valida con `MoodSchema` (`MoodName` obligatorio, `MoodStatus` solo
   `Active` o `Inactive`), prepara los datos y llama al modelo.
9. El **modelo** ejecuta el `INSERT` con parámetros y devuelve el `lastrowid`.
10. La respuesta sube por el pipeline, se serializa y sale:

```http
HTTP/1.1 201 Created
Location: /moods/25
Content-Type: application/json

{"status": "ok", "ID": 25}
```

Un `GET /moods` con el mismo token devuelve `200` y `{"status": "ok", "data": [...]}`. Un
`GET /moods/999` que no existe devuelve `404` y `{"error": "Mood not found"}`.

### El camino del error

Las excepciones no se atrapan en cada capa. Cualquier capa lanza un `AppError` (o una
subclase como `ForbiddenError`), y **ErrorMiddleware** la traduce una sola vez:

| Excepción | Código | Cuerpo |
| --- | --- | --- |
| `UnauthorizedError` | 401 | `{"error": "..."}` |
| `ForbiddenError` | 403 | `{"error": "..."}` |
| `PayloadTooLargeError` | 413 | `{"error": "..."}` |
| `TooManyRequestsError` | 429 | `{"error": "..."}` |
| `ServiceUnavailableError` | 503 | `{"error": "..."}` |
| `ValueError` | 400 | `{"error": "..."}` |
| cualquier otra | 500 | `{"error": "Internal server error"}` |

Por eso el orden importa: CORS es la capa **más externa**, así que sus cabeceras llegan
también a las respuestas de error. Si estuviera por dentro, un `401` viajaría sin CORS y
el navegador lo bloquearía sin dejar leer el mensaje.

### El ciclo de vida del controlador

El router crea un controlador **por petición** y lo cierra al terminar, incluso si el
manejador falla. Ese cierre libera la conexión a la base. No hay estado compartido entre
peticiones: dos usuarios simultáneos nunca ven los datos del otro.

### Dónde encaja una entidad nueva

Agregar una entidad son cuatro archivos y un router:

```text
schemas/thing_schema.py       reglas de los campos
models/thing.py               SQL de la tabla
controllers/thing_controller.py   MODEL_CLASS y SCHEMA, nada más si no hay reglas propias
routers/thing_router.py       add_crud_routes('/things', ThingController, 'Thing')
```

El router se descubre solo (`routers/__init__.py` en Python, `Routers/RouterRegistry.php`
en PHP), así que **no se edita el punto de entrada**. Ese es el objetivo del diseño: que
un alumno agregue su tabla sin entender el pipeline completo.

## Base de datos

```bash
mysql -u root -p < apicore.sql
```

Crea la base `apicore` con las tablas `users`, `moods`, `examples` y `users_tokens`, e
incluye las cuentas de prueba `godtest`, `admintest`, `usertest` y `othertest`
(contraseña igual al usuario). Es la única copia del esquema: las dos implementaciones
la usan.

## Arrancar cada API

```bash
# Python (por defecto en el puerto 8000)
cd api/v1/py && python3 main.py

# PHP (por defecto en el puerto 8000)
cd api/v1/php && php -S localhost:8000 index.php
```

Ambas leen un `.env` propio; copia el `.env.example` de cada carpeta. Como las dos usan
el puerto 8000 por defecto, cambia `APP_PORT` en una de ellas si quieres levantarlas a
la vez.

## Frontend de pruebas

`frontend/` es un panel mínimo en HTML, CSS y JavaScript nativo (sin jQuery) que usa
Bootstrap solo para lo visual. Sirve contra cualquiera de las dos implementaciones:

```bash
cd frontend && python3 -m http.server 8080
# abre http://localhost:8080 y ajusta la dirección del API en la cabecera
```

Permite iniciar sesión y, según el rol del token, gestionar `moods` y `examples` (User y
Other), administrar usuarios (Admin) o todo sin restricciones (God). El HTML, el CSS y
el JavaScript viven en archivos separados: `index.html`, `css/styles.css`,
`js/api.js` (cliente HTTP), `js/ui.js` (componentes) y `js/app.js` (estado y eventos).

## Pruebas

Las pruebas de integración viven en `tests/integration`, en la raíz, porque hablan HTTP
y no importan código de ninguna implementación. Se elige el servidor con
`API_LANGUAGE`:

```bash
python3 -m unittest discover -s tests -t .                    # contra Python
API_LANGUAGE=php python3 -m unittest discover -s tests -t .   # contra PHP
```

Las pruebas unitarias son propias de cada lenguaje:

```bash
cd api/v1/py  && python3 -m unittest discover -s tests -t .
cd api/v1/php && php tests/run.php
```

Las de integración necesitan MySQL con `apicore.sql` cargado.

## Colecciones de cliente

`insomnia_apicore.json` es la fuente de verdad y `postman_apicore.json` se genera desde
ella. No dependen del lenguaje:

```bash
python3 generate_postman_collection.py
```

## Diferencias entre las dos implementaciones

El contrato HTTP es el mismo, pero hay tres diferencias que conviene conocer:

- **Serialización JSON.** Python usa `json.dumps` con separadores por defecto, así que
  añade un espacio después de `:` y `,` (`{"status": "ok"}`). PHP usa `json_encode`, que
  no lo hace (`{"status":"ok"}`). El JSON es equivalente y cualquier cliente lo parsea
  igual; solo cambia el espaciado.
- **Cuerpo de la petición.** El servidor CLI de PHP bufferiza el cuerpo antes de ejecutar
  el script, así que un `Content-Length` mayor de 1 MB se rechaza con 413 en cuanto llega
  el cuerpo, no solo con las cabeceras como hace Python. Un `Content-Length` no numérico
  lo rechaza el propio servidor cerrando la conexión, sin respuesta JSON.
- **Concurrencia.** Python usa `ThreadingHTTPServer`; PHP necesita
  `PHP_CLI_SERVER_WORKERS` para atender peticiones en paralelo.

## Integración continua

`.github/workflows/tests.yml` ejecuta las cuatro suites (unitarias de Python, unitarias
de PHP e integración contra cada API) en cada push y pull request, con un servicio
MySQL 8.0 y el esquema de `apicore.sql` cargado desde la raíz.
