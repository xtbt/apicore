"""Deriva una clave de 32 bytes a partir de una frase usando PBKDF2-HMAC-SHA256.

Uso: python3 generate_jwt_secret.py
La frase se solicita sin mostrarla ni pasarla como argumento de terminal.

Advertencia: derivar una clave no añade entropía a una frase débil. Para JWT
es más seguro generar una clave aleatoria con `python3 -c "import secrets; print(secrets.token_hex(32))"`.
"""
import getpass
import hashlib
import secrets

ITERATIONS = 600_000
KEY_BYTES = 32
SALT_BYTES = 16


def derive_secret(passphrase: str, salt: bytes) -> bytes:
    """Deriva 32 bytes con PBKDF2 según PKCS #5 (RFC 8018)."""
    return hashlib.pbkdf2_hmac(
        'sha256',
        passphrase.encode('utf-8'),
        salt,
        ITERATIONS,
        dklen=KEY_BYTES,
    )


def main() -> None:
    passphrase = getpass.getpass('Frase para derivar el secret (entrada oculta): ')
    if not passphrase:
        raise SystemExit('La frase no puede estar vacía.')

    # Sal aleatoria para que la misma frase no produzca siempre la misma clave.
    salt = secrets.token_bytes(SALT_BYTES)
    key = derive_secret(passphrase, salt)

    print('\nJWT_SECRET=' + key.hex())
    print('KDF_SALT=' + salt.hex())
    print(f'KDF=PBKDF2-HMAC-SHA256; iteraciones={ITERATIONS}; longitud={KEY_BYTES} bytes')
    print('\nGuarda JWT_SECRET en el gestor de secretos o .env (sin subirlo a git).')
    print('Guarda también KDF_SALT si necesitas volver a derivar exactamente la misma clave.')
    print('La sal no es secreta. Una frase común sigue siendo vulnerable a ataques de diccionario;')
    print('para producción, prefiere una clave aleatoria de 32 bytes.')


if __name__ == '__main__':
    main()
