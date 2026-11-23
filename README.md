# apicore

API REST sobre MySQL implementada dos veces, una por lenguaje, con el mismo contrato
y la misma base de datos:

| Implementación | Ruta | Estado |
| --- | --- | --- |
| Python | `api/v1/py` | completa y probada |
| PHP | `api/v1/php` | pendiente |

Ambas comparten el esquema de `apicore.sql`, en la raíz del repositorio, y exponen los
mismos endpoints, códigos de estado y formato de respuesta, de modo que un cliente
puede apuntar a cualquiera de las dos sin cambios.

Por ahora el desarrollo se centra en la implementación en Python; su documentación
completa está en [`api/v1/py/README.md`](api/v1/py/README.md).

## Base de datos

```bash
mysql -u root -p < apicore.sql
```

Crea la base `apicore` con las tablas `users`, `moods` y `users_tokens`, e incluye las
cuentas de prueba `godtest`, `admintest` y `usertest` (contraseña igual al usuario).
Es la única copia del esquema: las dos implementaciones la usan.
