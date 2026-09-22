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

    @staticmethod
    def cargar() -> "Settings":
        db_url = os.environ.get(
            "SGS_DB_URL",
            "postgresql+psycopg://sgs_user:sgs_pass@localhost:5432/sgs_local",
        )
        entorno = os.environ.get("SGS_ENTORNO", "local")
        return Settings(
            db_url=db_url,
            entorno=entorno,
        )


settings = Settings.cargar()