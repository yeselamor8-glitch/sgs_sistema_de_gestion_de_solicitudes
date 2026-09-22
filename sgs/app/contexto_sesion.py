"""
Contexto de sesión del usuario actual (proceso único, app de escritorio).

Se fija al iniciar sesión y se limpia al cerrarla. Sirve para que la
auditoría sepa QUIÉN hizo cada acción sin tener que propagar el
usuario_id por la firma de cada caso de uso.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActorSesion:
    usuario_id: int | None
    nombre: str | None
    rol: str | None


_actor: ActorSesion | None = None


def set_actor(usuario_id: int | None, nombre: str | None = None, rol: str | None = None) -> None:
    global _actor
    _actor = ActorSesion(usuario_id=usuario_id, nombre=nombre, rol=rol)


def limpiar() -> None:
    global _actor
    _actor = None


def actor_actual() -> ActorSesion | None:
    return _actor


def usuario_id_actual() -> int | None:
    return _actor.usuario_id if _actor else None
