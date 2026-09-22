from __future__ import annotations

from sqlalchemy.orm import Session

from sgs.models.orm import ParametrosSemaforizacion


class ParametrosSemaforizacionRepo:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self) -> ParametrosSemaforizacion:
        fila = self.db.get(ParametrosSemaforizacion, 1)
        if fila is None:
            fila = ParametrosSemaforizacion(id=1, dias_habiles_verde_hasta=1, dias_habiles_amarillo_hasta=2)
            self.db.add(fila)
            self.db.flush()
        return fila

    def guardar(self, dias_verde_hasta: int, dias_amarillo_cerca: int) -> None:
        fila = self.obtener()
        fila.dias_habiles_verde_hasta = dias_verde_hasta
        fila.dias_habiles_amarillo_hasta = dias_amarillo_cerca
        self.db.flush()