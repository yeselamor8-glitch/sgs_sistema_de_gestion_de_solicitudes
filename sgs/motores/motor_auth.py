"""
Motor de autenticación: hash y verificación de contraseñas.

Usa bcrypt (con salt aleatorio por contraseña, incluido en el hash
resultante). Nunca se almacena ni se compara contraseña en texto
plano (sección 33 del documento funcional — seguridad desde el
principio).

No conoce SQLAlchemy ni la UI: recibe/devuelve strings simples.
"""
from __future__ import annotations

import bcrypt


def hashear_password(password_plano: str) -> str:
    if not password_plano:
        raise ValueError("La contraseña no puede estar vacía.")
    hash_bytes = bcrypt.hashpw(password_plano.encode("utf-8"), bcrypt.gensalt())
    return hash_bytes.decode("utf-8")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    if not password_plano or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password_plano.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # hash con formato inválido/corrupto -> tratar como no coincide,
        # nunca lanzar el error hacia la UI
        return False