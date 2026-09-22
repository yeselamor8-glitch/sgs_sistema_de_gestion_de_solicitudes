from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from sgs.models.orm import Auditoria, Solicitud, Usuario


class AuditoriaRepo:
    """Bitácora de acciones importantes. Escritura (registrar) y consulta
    (listar con filtros básicos). Es de solo lectura desde la UI."""

    def __init__(self, db: Session):
        self.db = db

    def registrar(
        self,
        usuario_id: int | None,
        accion: str,
        entidad: str,
        entidad_id: int | None = None,
        valor_anterior: dict | None = None,
        valor_nuevo: dict | None = None,
        solicitud_relacionada_id: int | None = None,
    ) -> Auditoria:
        registro = Auditoria(
            usuario_id=usuario_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
            solicitud_relacionada_id=solicitud_relacionada_id,
        )
        self.db.add(registro)
        self.db.flush()
        return registro

    def listar(self, filtros: dict | None = None, limit: int = 300) -> list[dict]:
        """Devuelve la bitácora (más reciente primero) en tipos simples,
        lista para la tabla de la UI. Filtros opcionales: entidad, accion
        (contiene), usuario_id, numero_solicitud, desde, hasta (date)."""
        filtros = filtros or {}
        stmt = select(Auditoria).order_by(Auditoria.fecha.desc())

        if filtros.get("entidad"):
            stmt = stmt.where(Auditoria.entidad == filtros["entidad"])
        if filtros.get("usuario_id"):
            stmt = stmt.where(Auditoria.usuario_id == filtros["usuario_id"])
        if filtros.get("desde"):
            stmt = stmt.where(Auditoria.fecha >= filtros["desde"])
        if filtros.get("hasta"):
            # incluir todo el día 'hasta'
            hasta = filtros["hasta"]
            if isinstance(hasta, dt.date) and not isinstance(hasta, dt.datetime):
                hasta = dt.datetime.combine(hasta, dt.time.max)
            stmt = stmt.where(Auditoria.fecha <= hasta)

        stmt = stmt.limit(limit)
        registros = self.db.execute(stmt).scalars().all()

        # caches de nombres para no consultar N veces
        nombres_usuario: dict[int, str] = {}
        numeros_solicitud: dict[int, str] = {}
        accion_contiene = (filtros.get("accion") or "").strip().lower()

        filas = []
        for r in registros:
            if accion_contiene and accion_contiene not in r.accion.lower():
                continue
            if r.usuario_id and r.usuario_id not in nombres_usuario:
                u = self.db.get(Usuario, r.usuario_id)
                nombres_usuario[r.usuario_id] = u.nombre if u else f"(usuario {r.usuario_id})"
            if r.solicitud_relacionada_id and r.solicitud_relacionada_id not in numeros_solicitud:
                s = self.db.get(Solicitud, r.solicitud_relacionada_id)
                numeros_solicitud[r.solicitud_relacionada_id] = (
                    s.numero_solicitud_sac if s else f"(solicitud {r.solicitud_relacionada_id})"
                )
            filas.append(
                {
                    "usuario": nombres_usuario.get(r.usuario_id, "Sistema"),
                    "accion": r.accion,
                    "entidad": r.entidad + (f" #{r.entidad_id}" if r.entidad_id else ""),
                    "solicitud": numeros_solicitud.get(r.solicitud_relacionada_id, ""),
                    "valor_anterior": _resumen_valor(r.valor_anterior),
                    "valor_nuevo": _resumen_valor(r.valor_nuevo),
                    "fecha": r.fecha.strftime("%Y-%m-%d %H:%M") if r.fecha else "",
                }
            )
        return filas

    def entidades_distintas(self) -> list[str]:
        stmt = select(Auditoria.entidad).distinct().order_by(Auditoria.entidad)
        return [e for e in self.db.execute(stmt).scalars() if e]


def _resumen_valor(valor) -> str:
    """Convierte el JSON de valor_anterior/nuevo en un texto compacto."""
    if valor is None:
        return ""
    if isinstance(valor, dict):
        return ", ".join(f"{k}: {v}" for k, v in valor.items())
    return str(valor)
