from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from sgs.models.orm import VistaColumnasUsuario


class VistaColumnasRepo:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self, usuario_id: int, pantalla: str) -> Optional[list[dict]]:
        stmt = select(VistaColumnasUsuario).where(
            VistaColumnasUsuario.usuario_id == usuario_id, VistaColumnasUsuario.pantalla == pantalla
        )
        fila = self.db.execute(stmt).scalar_one_or_none()
        return fila.configuracion if fila else None

    def guardar(self, usuario_id: int, pantalla: str, configuracion: list[dict]) -> None:
        existente = self.db.get(VistaColumnasUsuario, {"usuario_id": usuario_id, "pantalla": pantalla})
        if existente:
            existente.configuracion = configuracion
        else:
            self.db.add(
                VistaColumnasUsuario(usuario_id=usuario_id, pantalla=pantalla, configuracion=configuracion)
            )
        self.db.flush()