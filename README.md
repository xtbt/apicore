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
