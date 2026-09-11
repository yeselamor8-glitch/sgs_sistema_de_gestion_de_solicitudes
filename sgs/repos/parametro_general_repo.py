from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from sgs.models.orm import ParametroGeneral


class ParametroGeneralRepo:
    def __init__(self, db: Session):
        self.db = db

    def listar(self) -> dict[str, str]:
        return {p.clave: p.valor or "" for p in self.db.execute(select(ParametroGeneral)).scalars()}

    def guardar(self, clave: str, valor: str, descripcion: str = "") -> None:
        fila = self.db.get(ParametroGeneral, clave)
        if fila is None:
            fila = ParametroGeneral(clave=clave, valor=valor, descripcion=descripcion)
            self.db.add(fila)
        else:
            fila.valor = valor
        self.db.flush()