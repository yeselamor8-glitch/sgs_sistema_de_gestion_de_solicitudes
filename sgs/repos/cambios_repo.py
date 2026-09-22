from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sgs.models.orm import Notificacion, Proceso, Solicitud, SolicitudCambio, Usuario


class SolicitudCambioRepo:
    """Solicitudes de cambio (por ahora, reasignación de proceso) y su
    ciclo pendiente -> aprobada/rechazada."""

    def __init__(self, db: Session):
        self.db = db

    def crear_reasignacion_proceso(
        self,
        solicitud_id: int,
        proceso_actual_id: int | None,
        proceso_solicitado_id: int,
        motivo: str,
        solicitado_por: int,
    ) -> SolicitudCambio:
        cambio = SolicitudCambio(
            solicitud_id=solicitud_id,
            tipo="reasignacion_proceso",
            proceso_actual_id=proceso_actual_id,
            proceso_solicitado_id=proceso_solicitado_id,
            motivo=motivo,
            estado="pendiente",
            solicitado_por=solicitado_por,
        )
        self.db.add(cambio)
        self.db.flush()
        return cambio

    def obtener(self, cambio_id: int) -> SolicitudCambio | None:
        return self.db.get(SolicitudCambio, cambio_id)

    def listar_pendientes(self) -> list[SolicitudCambio]:
        stmt = (
            select(SolicitudCambio)
            .where(SolicitudCambio.estado == "pendiente")
            .order_by(SolicitudCambio.creado_en.desc())
        )
        return list(self.db.execute(stmt).scalars())

    def listar_por_solicitante(self, usuario_id: int) -> list[SolicitudCambio]:
        stmt = (
            select(SolicitudCambio)
            .where(SolicitudCambio.solicitado_por == usuario_id)
            .order_by(SolicitudCambio.creado_en.desc())
        )
        return list(self.db.execute(stmt).scalars())

    def resolver(
        self, cambio_id: int, aprobada: bool, aprobado_por: int, observacion: str | None
    ) -> SolicitudCambio:
        cambio = self.obtener(cambio_id)
        if cambio is None:
            raise ValueError(f"No existe la solicitud de cambio {cambio_id}")
        if cambio.estado != "pendiente":
            raise ValueError("La solicitud de cambio ya fue resuelta.")

        cambio.estado = "aprobada" if aprobada else "rechazada"
        cambio.aprobado_por = aprobado_por
        cambio.observacion_admin = observacion or None
        cambio.resuelto_en = dt.datetime.utcnow()

        if aprobada and cambio.tipo == "reasignacion_proceso" and cambio.proceso_solicitado_id:
            solicitud = self.db.get(Solicitud, cambio.solicitud_id)
            if solicitud is not None:
                solicitud.proceso_id = cambio.proceso_solicitado_id
                solicitud.actualizado_en = dt.datetime.utcnow()

        self.db.flush()
        return cambio

    # ------------------------------------------------------------------
    # Helpers de presentación (nombres legibles, sin exponer ORM a la UI)
    # ------------------------------------------------------------------
    def _nombre_proceso(self, proceso_id: int | None) -> str:
        if proceso_id is None:
            return "Sin proceso"
        proceso = self.db.get(Proceso, proceso_id)
        return proceso.nombre if proceso else f"(proceso {proceso_id})"

    def _numero_solicitud(self, solicitud_id: int) -> str:
        solicitud = self.db.get(Solicitud, solicitud_id)
        return solicitud.numero_solicitud_sac if solicitud else f"(solicitud {solicitud_id})"

    def _nombre_usuario(self, usuario_id: int | None) -> str:
        if usuario_id is None:
            return ""
        usuario = self.db.get(Usuario, usuario_id)
        return usuario.nombre if usuario else ""

    def a_dict(self, cambio: SolicitudCambio) -> dict:
        return {
            "id": cambio.id,
            "tipo": cambio.tipo,
            "numero_solicitud_sac": self._numero_solicitud(cambio.solicitud_id),
            "proceso_actual": self._nombre_proceso(cambio.proceso_actual_id),
            "proceso_solicitado": self._nombre_proceso(cambio.proceso_solicitado_id),
            "motivo": cambio.motivo,
            "estado": cambio.estado,
            "observacion_admin": cambio.observacion_admin or "",
            "solicitado_por": self._nombre_usuario(cambio.solicitado_por),
            "creado_en": cambio.creado_en.isoformat(timespec="minutes") if cambio.creado_en else "",
        }


class NotificacionRepo:
    def __init__(self, db: Session):
        self.db = db

    def crear(
        self,
        usuario_id: int,
        tipo: str,
        mensaje: str,
        referencia_tipo: str | None = None,
        referencia_id: int | None = None,
    ) -> Notificacion:
        notif = Notificacion(
            usuario_id=usuario_id,
            tipo=tipo,
            mensaje=mensaje,
            referencia_tipo=referencia_tipo,
            referencia_id=referencia_id,
        )
        self.db.add(notif)
        self.db.flush()
        return notif

    def crear_para_muchos(
        self,
        usuario_ids: list[int],
        tipo: str,
        mensaje: str,
        referencia_tipo: str | None = None,
        referencia_id: int | None = None,
    ) -> None:
        for uid in usuario_ids:
            self.db.add(
                Notificacion(
                    usuario_id=uid,
                    tipo=tipo,
                    mensaje=mensaje,
                    referencia_tipo=referencia_tipo,
                    referencia_id=referencia_id,
                )
            )
        self.db.flush()

    def listar_de(self, usuario_id: int, limit: int = 50) -> list[Notificacion]:
        stmt = (
            select(Notificacion)
            .where(Notificacion.usuario_id == usuario_id)
            .order_by(Notificacion.creado_en.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars())

    def contar_no_leidas(self, usuario_id: int) -> int:
        stmt = select(func.count()).select_from(Notificacion).where(
            Notificacion.usuario_id == usuario_id, Notificacion.leida.is_(False)
        )
        return int(self.db.execute(stmt).scalar() or 0)

    def marcar_todas_leidas(self, usuario_id: int) -> None:
        for notif in self.db.execute(
            select(Notificacion).where(
                Notificacion.usuario_id == usuario_id, Notificacion.leida.is_(False)
            )
        ).scalars():
            notif.leida = True
        self.db.flush()

    @staticmethod
    def a_dict(notif: Notificacion) -> dict:
        return {
            "id": notif.id,
            "tipo": notif.tipo,
            "mensaje": notif.mensaje,
            "leida": notif.leida,
            "referencia_tipo": notif.referencia_tipo,
            "referencia_id": notif.referencia_id,
            "creado_en": notif.creado_en.isoformat(timespec="minutes") if notif.creado_en else "",
        }


def ids_administradores(db: Session) -> list[int]:
    """IDs de los usuarios administradores activos (destinatarios de las
    solicitudes de cambio y alertas)."""
    stmt = select(Usuario.id).where(Usuario.rol == "ADMINISTRADOR", Usuario.activo.is_(True))
    return [uid for uid in db.execute(stmt).scalars()]
