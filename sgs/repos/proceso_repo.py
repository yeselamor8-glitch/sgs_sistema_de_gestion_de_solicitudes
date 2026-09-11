from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from sgs.models.orm import Proceso


class ProcesoRepo:
    def __init__(self, db: Session):
        self.db = db

    def listar(self) -> list[Proceso]:
        return list(self.db.execute(select(Proceso).order_by(Proceso.nombre)).scalars())

    def obtener_por_id(self, proceso_id: int) -> Proceso | None:
        return self.db.get(Proceso, proceso_id)

    def crear(self, nombre: str, descripcion: str) -> Proceso:
        proceso = Proceso(nombre=nombre, descripcion=descripcion, activo=True)
        self.db.add(proceso)
        self.db.flush()
        return proceso

    def cambiar_estado(self, proceso_id: int, activo: bool) -> None:
        proceso = self.obtener_por_id(proceso_id)
        if proceso is None:
            raise ValueError(f"No existe el proceso {proceso_id}")
        proceso.activo = activo