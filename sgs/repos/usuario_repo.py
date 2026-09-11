from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from sgs.models.orm import FuncionarioProceso, Usuario


class UsuarioRepo:
    def __init__(self, db: Session):
        self.db = db

    def obtener_por_username(self, username: str) -> Optional[Usuario]:
        stmt = select(Usuario).where(Usuario.username == username, Usuario.activo.is_(True))
        return self.db.execute(stmt).scalar_one_or_none()

    def obtener_por_id(self, usuario_id: int) -> Optional[Usuario]:
        return self.db.get(Usuario, usuario_id)

    def listar(self) -> list[Usuario]:
        return list(self.db.execute(select(Usuario).order_by(Usuario.nombre)).scalars())

    def listar_funcionarios_por_proceso(self, proceso_id: int) -> list[Usuario]:
        stmt = (
            select(Usuario)
            .join(FuncionarioProceso, FuncionarioProceso.usuario_id == Usuario.id)
            .where(
                FuncionarioProceso.proceso_id == proceso_id,
                Usuario.rol == "FUNCIONARIO",
                Usuario.activo.is_(True),
            )
            .order_by(Usuario.nombre)
        )
        return list(self.db.execute(stmt).scalars())

    def guardar(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.flush()
        return usuario