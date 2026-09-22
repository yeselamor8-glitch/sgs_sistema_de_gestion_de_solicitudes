"""
Repositorio de Solicitud. Los motores nunca hablan con SQLAlchemy
directamente — solo los repositorios lo hacen, y solo la capa de
aplicación llama a los repositorios.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from sgs.models.orm import Ciudadano, EnteControl, Proceso, Respuesta, Solicitud, Traslado, Usuario


class SolicitudRepo:
    def __init__(self, db: Session):
        self.db = db

    def obtener_por_numero_sac(self, numero_solicitud_sac: str) -> Optional[Solicitud]:
        stmt = select(Solicitud).where(Solicitud.numero_solicitud_sac == numero_solicitud_sac)
        return self.db.execute(stmt).scalar_one_or_none()

    def listar_por_proceso(self, proceso_id: int, limit: int = 100, offset: int = 0) -> list[Solicitud]:
        stmt = (
            select(Solicitud)
            .where(Solicitud.proceso_id == proceso_id)
            .order_by(Solicitud.sac_fecha_ingreso.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars())

    def listar_por_funcionario(self, funcionario_id: int, limit: int = 100, offset: int = 0) -> list[Solicitud]:
        stmt = (
            select(Solicitud)
            .where(Solicitud.funcionario_id == funcionario_id)
            .order_by(Solicitud.sac_fecha_ingreso.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars())

    def listar_sin_clasificar(self, limit: int = 100) -> list[Solicitud]:
        stmt = (
            select(Solicitud)
            .where(Solicitud.clasificacion_estado == "sin_clasificar")
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars())

    def listar_con_filtros(self, filtros: dict | None = None, limit: int = 5000, offset: int = 0) -> list[dict]:
        stmt = (
            select(Solicitud, Ciudadano, Proceso, Usuario, Traslado, Respuesta, EnteControl)
            .outerjoin(Ciudadano, Ciudadano.id == Solicitud.ciudadano_id)
            .outerjoin(Proceso, Proceso.id == Solicitud.proceso_id)
            .outerjoin(Usuario, Usuario.id == Solicitud.funcionario_id)
            .outerjoin(Traslado, Traslado.solicitud_id == Solicitud.id)
            .outerjoin(Respuesta, Respuesta.solicitud_id == Solicitud.id)
            .outerjoin(EnteControl, EnteControl.solicitud_id == Solicitud.id)
            .order_by(Solicitud.sac_fecha_ingreso.desc(), Solicitud.id.desc())
            .limit(limit)
            .offset(offset)
        )
        stmt = self._aplicar_filtros(stmt, filtros)

        filas = []
        for solicitud, ciudadano, proceso, funcionario, traslado, respuesta, ente in self.db.execute(stmt):
            filas.append({
                "id": solicitud.id,
                "numero_solicitud_sac": solicitud.numero_solicitud_sac,
                "ciudadano": ciudadano,
                "proceso": proceso,
                "funcionario": funcionario,
                "traslado": traslado,
                "respuesta": respuesta,
                "ente_control": ente,
                "solicitud": solicitud,
            })
        return filas

    def contar(self, filtros: dict | None = None) -> int:
        """Total de solicitudes que coinciden con los mismos filtros de
        `listar_con_filtros` (para el contador del módulo Solicitudes)."""
        stmt = (
            select(func.count(Solicitud.id))
            .select_from(Solicitud)
            .outerjoin(Ciudadano, Ciudadano.id == Solicitud.ciudadano_id)
            .outerjoin(Proceso, Proceso.id == Solicitud.proceso_id)
        )
        stmt = self._aplicar_filtros(stmt, filtros)
        return self.db.execute(stmt).scalar_one()

    @staticmethod
    def _aplicar_filtros(stmt, filtros: dict | None):
        """WHERE compartido entre listar_con_filtros y contar. Filtra sobre
        el bloque SAC como respaldo cuando no hay ciudadano vinculado
        (COALESCE), manteniendo el detalle y la lista siempre consistentes."""
        filtros = filtros or {}
        numero = filtros.get("numero")
        documento = filtros.get("documento")
        nombre = filtros.get("nombre")
        if numero:
            stmt = stmt.where(Solicitud.numero_solicitud_sac.ilike(f"%{numero}%"))
        if documento:
            stmt = stmt.where(
                or_(
                    Ciudadano.numero_documento.ilike(f"%{documento}%"),
                    Solicitud.doc_numero_documento.ilike(f"%{documento}%"),
                )
            )
        if nombre:
            stmt = stmt.where(
                or_(
                    Ciudadano.nombre.ilike(f"%{nombre}%"),
                    Solicitud.doc_nombre.ilike(f"%{nombre}%"),
                )
            )
        if filtros.get("proceso") and filtros["proceso"] != "Todos":
            stmt = stmt.where(Proceso.nombre == filtros["proceso"])
        if filtros.get("estado_gestion") and filtros["estado_gestion"] != "Todos":
            stmt = stmt.where(Solicitud.estado_gestion == filtros["estado_gestion"])
        if filtros.get("funcionario_id"):
            stmt = stmt.where(Solicitud.funcionario_id == filtros["funcionario_id"])
        if "proceso_ids" in filtros:
            proceso_ids = filtros["proceso_ids"]
            if proceso_ids:
                stmt = stmt.where(Solicitud.proceso_id.in_(proceso_ids))
            else:
                stmt = stmt.where(Solicitud.id == -1)
        fecha_desde = _a_fecha(filtros.get("fecha_desde"))
        if fecha_desde:
            stmt = stmt.where(Solicitud.sac_fecha_ingreso >= dt.datetime.combine(fecha_desde, dt.time.min))
        fecha_hasta = _a_fecha(filtros.get("fecha_hasta"))
        if fecha_hasta:
            stmt = stmt.where(Solicitud.sac_fecha_ingreso <= dt.datetime.combine(fecha_hasta, dt.time.max))
        if filtros.get("excluir_completadas"):
            # "Completada" = hubo respuesta SI, hay radicado del ente de
            # control, o la gestión quedó solucionada (misma regla que
            # `motor_semaforo.calcular_semaforo_solicitud`). Por defecto el
            # módulo Solicitudes NO muestra estas filas (mejor rendimiento:
            # solo se traen las que aún están en gestión). Se usa EXISTS
            # correlacionado para que funcione igual en `listar_con_filtros`
            # y en `contar` (que no une Respuesta/EnteControl).
            completada = or_(
                exists(
                    select(1).where(
                        Respuesta.solicitud_id == Solicitud.id,
                        func.upper(func.btrim(func.coalesce(Respuesta.hubo_respuesta, ""))) == "SI",
                    )
                ).correlate(Solicitud),
                exists(
                    select(1).where(
                        EnteControl.solicitud_id == Solicitud.id,
                        func.btrim(func.coalesce(EnteControl.radicado, "")) != "",
                    )
                ).correlate(Solicitud),
                func.lower(func.btrim(func.coalesce(Solicitud.estado_gestion, ""))) == "solucionada",
            )
            stmt = stmt.where(~completada)
        return stmt

    def obtener_detalle(self, numero_solicitud_sac: str) -> dict | None:
        filas = self.listar_con_filtros({"numero": numero_solicitud_sac}, limit=1)
        if not filas or filas[0]["solicitud"].numero_solicitud_sac != numero_solicitud_sac:
            return None
        return filas[0]

    def guardar(self, solicitud: Solicitud) -> Solicitud:
        self.db.add(solicitud)
        self.db.flush()
        return solicitud


def _a_fecha(valor) -> dt.date | None:
    """Normaliza un filtro de fecha (QDate/date/str ISO) a date."""
    if isinstance(valor, dt.date):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            return dt.datetime.strptime(valor.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None
