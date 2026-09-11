"""
Configuración central del sistema.

El cambio de PostgreSQL local a PostgreSQL de servidor institucional
se hace SOLO cambiando la variable de entorno SGS_DB_URL (o el archivo
.env) — ningún otro módulo del sistema debe conocer si la base está
en local o en el servidor.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_url: str
    entorno: str  # 'local' | 'servidor'
    dias_verde_hasta: int
    dias_amarillo_hasta: int

    @staticmethod
    def cargar() -> "Settings":
        db_url = os.environ.get(
            "SGS_DB_URL",
            "postgresql+psycopg://sgs_user:sgs_pass@localhost:5432/sgs_local",
        )
        entorno = os.environ.get("SGS_ENTORNO", "local")
        # Los umbrales de semaforización también se pueden sobreescribir
        # por variable de entorno para pruebas, pero su fuente de verdad
        # real en producción es la tabla parametros_semaforizacion.
        dias_verde = int(os.environ.get("SGS_DIAS_VERDE", "1"))
        dias_amarillo = int(os.environ.get("SGS_DIAS_AMARILLO", "2"))
        return Settings(
            db_url=db_url,
            entorno=entorno,
            dias_verde_hasta=dias_verde,
            dias_amarillo_hasta=dias_amarillo,
        )


settings = Settings.cargar()