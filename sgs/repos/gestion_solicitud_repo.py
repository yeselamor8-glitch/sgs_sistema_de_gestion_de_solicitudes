from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from sgs.models.orm import EnteControl, Respuesta, Solicitud, Traslado


class GestionSolicitudRepo:
    """
    Escribe SOLO el bloque de gestión de una solicitud — nunca toca el
    bloque SAC (`sac_*` en `solicitudes`), que es de solo lectura desde
    la app y solo lo escribe el importador (separación acordada en la
    Fase 2). Cubre las 4 tablas donde vive la gestión: `solicitudes`
    (estado/observaciones), `traslados`, `respuestas`, `entes_control`.
    """

    def __init__(self, db: Session):
        self.db = db

    def obtener_por_numero_sac(self, numero_solicitud_sac: str) -> Solicitud | None:
        stmt = select(Solicitud).where(Solicitud.numero_solicitud_sac == numero_solicitud_sac)
        return self.db.execute(stmt).scalar_one_or_none()

    def actualizar_gestion(self, numero_solicitud_sac: str, cambios: dict) -> None:
        solicitud = self.obtener_por_numero_sac(numero_solicitud_sac)
        if solicitud is None:
            raise ValueError(f"No existe la solicitud {numero_solicitud_sac}")

        if "estado_gestion" in cambios:
            solicitud.estado_gestion = cambios["estado_gestion"]
        if "observaciones" in cambios:
            solicitud.observaciones = cambios["observaciones"]
        if "funcionario_id" in cambios:
            solicitud.funcionario_id = cambios["funcionario_id"] or None
        solicitud.actualizado_en = dt.datetime.utcnow()

        self._upsert_traslado(solicitud.id, cambios)
        self._upsert_respuesta(solicitud.id, cambios)
        self._upsert_ente_control(solicitud.id, cambios)

        self.db.flush()

    # ------------------------------------------------------------------
    def _upsert_traslado(self, solicitud_id: int, cambios: dict) -> None:
        campos = {"fecha_traslado", "institucion_competente"}
        if not campos & cambios.keys():
            return
        fila = self.db.execute(
            select(Traslado).where(Traslado.solicitud_id == solicitud_id)
        ).scalar_one_or_none()
        if fila is None:
            fila = Traslado(solicitud_id=solicitud_id)
            self.db.add(fila)
        if "fecha_traslado" in cambios:
            fila.fecha_traslado = _a_fecha(cambios["fecha_traslado"])
        if "institucion_competente" in cambios:
            fila.institucion_competente = cambios["institucion_competente"]

    def _upsert_respuesta(self, solicitud_id: int, cambios: dict) -> None:
        campos = {"hubo_respuesta", "respuesta_entidad", "notificacion_usuario", "fecha_respuesta"}
        if not campos & cambios.keys():
            return
        fila = self.db.execute(
            select(Respuesta).where(Respuesta.solicitud_id == solicitud_id)
        ).scalar_one_or_none()
        if fila is None:
            fila = Respuesta(solicitud_id=solicitud_id)
            self.db.add(fila)
        if "hubo_respuesta" in cambios:
            fila.hubo_respuesta = cambios["hubo_respuesta"]
        if "respuesta_entidad" in cambios:
            fila.respuesta_entidad = cambios["respuesta_entidad"]
        if "notificacion_usuario" in cambios:
            fila.notificacion_usuario = cambios["notificacion_usuario"]
        if "fecha_respuesta" in cambios:
            fila.fecha_respuesta = _a_fecha(cambios["fecha_respuesta"])
        # decision y oportunidad_respuesta son CALCULADOS (motor_tiempos /
        # lógica de decisión) — este repo no los escribe directamente;
        # deben venir ya resueltos en `cambios` por el caso de uso si
        # corresponde recalcularlos.

    def _upsert_ente_control(self, solicitud_id: int, cambios: dict) -> None:
        campos = {"radicado_ente_control", "entidad_control", "fecha_reporte_control"}
        if not campos & cambios.keys():
            return
        fila = self.db.execute(
            select(EnteControl).where(EnteControl.solicitud_id == solicitud_id)
        ).scalar_one_or_none()
        if fila is None:
            fila = EnteControl(solicitud_id=solicitud_id)
            self.db.add(fila)
        if "radicado_ente_control" in cambios:
            fila.radicado = cambios["radicado_ente_control"]
        if "entidad_control" in cambios:
            fila.entidad = cambios["entidad_control"]
        if "fecha_reporte_control" in cambios:
            fila.fecha_reporte = _a_fecha(cambios["fecha_reporte_control"])


def _a_fecha(valor: str | None) -> dt.date | None:
    if not valor:
        return None
    try:
        return dt.datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None