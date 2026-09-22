from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from sgs.models.orm import (
    CatalogoEps,
    CondicionRegla,
    Festivo,
    ReglaClasificacion,
    ReglaTiemposEps,
    ReglaTiemposPrioridad,
    ReglaTiemposSolicitud,
)
from sgs.motores.motor_clasificacion import Condicion, Operador, Regla
from sgs.motores.motor_tiempos import ParametrosTiempo


class ReglaClasificacionRepo:
    """Traduce las filas de reglas_clasificacion/condiciones_regla al
    tipo Regla que consume el motor de clasificación (mantiene el
    motor libre de SQLAlchemy)."""

    def __init__(self, db: Session):
        self.db = db

    def listar_reglas_activas(self) -> list[Regla]:
        stmt = select(ReglaClasificacion).where(ReglaClasificacion.activo.is_(True))
        reglas_orm = self.db.execute(stmt).scalars().all()
        return [
            Regla(
                proceso_id=r.proceso_id,
                orden_evaluacion=r.orden_evaluacion,
                tipo_regla=r.tipo_regla,
                condiciones=tuple(
                    Condicion(c.campo, Operador(c.operador), tuple(c.valores)) for c in r.condiciones
                ),
            )
            for r in reglas_orm
        ]

    def proceso_tiene_reglas(self, proceso_id: int) -> bool:
        stmt = select(ReglaClasificacion.id).where(ReglaClasificacion.proceso_id == proceso_id).limit(1)
        return self.db.execute(stmt).first() is not None

    def crear_regla(
        self,
        proceso_id: int,
        tipo_regla: str,
        orden_evaluacion: int,
        condiciones: list[tuple[str, str, list[str]]],
        descripcion: str | None = None,
        activo: bool = True,
    ) -> ReglaClasificacion:
        """`condiciones` = [(campo, operador, valores), ...] — AND entre ellas."""
        regla = ReglaClasificacion(
            proceso_id=proceso_id,
            tipo_regla=tipo_regla,
            orden_evaluacion=orden_evaluacion,
            activo=activo,
            descripcion=descripcion or None,
        )
        self.db.add(regla)
        self.db.flush()
        for campo, operador, valores in condiciones:
            self.db.add(CondicionRegla(regla_id=regla.id, campo=campo, operador=operador, valores=list(valores)))
        self.db.flush()
        return regla

    def obtener_para_editar(self, regla_id: int) -> dict | None:
        """Devuelve la regla en tipos simples (para el diálogo de edición)."""
        regla = self.db.get(ReglaClasificacion, regla_id)
        if regla is None:
            return None
        return {
            "id": regla.id,
            "proceso_id": regla.proceso_id,
            "tipo_regla": regla.tipo_regla,
            "orden_evaluacion": regla.orden_evaluacion,
            "activo": regla.activo,
            "descripcion": regla.descripcion or "",
            "condiciones": [
                {"campo": c.campo, "operador": c.operador, "valores": list(c.valores)}
                for c in regla.condiciones
            ],
        }

    def actualizar_regla(
        self,
        regla_id: int,
        proceso_id: int,
        tipo_regla: str,
        orden_evaluacion: int,
        condiciones: list[tuple[str, str, list[str]]],
        descripcion: str | None = None,
        activo: bool | None = None,
    ) -> None:
        """Actualiza la cabecera y REEMPLAZA todas las condiciones."""
        regla = self.db.get(ReglaClasificacion, regla_id)
        if regla is None:
            raise ValueError(f"No existe la regla {regla_id}")
        regla.proceso_id = proceso_id
        regla.tipo_regla = tipo_regla
        regla.orden_evaluacion = orden_evaluacion
        regla.descripcion = descripcion or None
        if activo is not None:
            regla.activo = activo
        # cascade delete-orphan borra las condiciones viejas al vaciar la lista
        regla.condiciones.clear()
        self.db.flush()
        for campo, operador, valores in condiciones:
            self.db.add(CondicionRegla(regla_id=regla.id, campo=campo, operador=operador, valores=list(valores)))
        self.db.flush()

    def eliminar_regla(self, regla_id: int) -> None:
        regla = self.db.get(ReglaClasificacion, regla_id)
        if regla is not None:
            self.db.delete(regla)  # cascade borra sus condiciones
            self.db.flush()

    def cambiar_estado(self, regla_id: int, activo: bool) -> None:
        regla = self.db.get(ReglaClasificacion, regla_id)
        if regla is None:
            raise ValueError(f"No existe la regla {regla_id}")
        regla.activo = activo
        self.db.flush()

    def listar_para_mostrar(self) -> list[dict]:
        """Vista para la pantalla de Configuración (id, proceso, tipo,
        orden, estado y resumen legible de condiciones)."""
        from sgs.models.orm import Proceso

        stmt = select(ReglaClasificacion).order_by(ReglaClasificacion.proceso_id, ReglaClasificacion.orden_evaluacion)
        filas = []
        for r in self.db.execute(stmt).scalars():
            proceso = self.db.get(Proceso, r.proceso_id)
            resumen = " AND ".join(
                f"{c.campo} {c.operador} {list(c.valores)}" for c in r.condiciones
            )
            filas.append(
                {
                    "id": r.id,
                    "proceso": proceso.nombre if proceso else str(r.proceso_id),
                    "tipo": r.tipo_regla,
                    "orden": r.orden_evaluacion,
                    "activo": r.activo,
                    "resumen": resumen,
                }
            )
        return filas


class ReglaTiemposRepo:
    """Ensambla ParametrosTiempo desde las tablas de configuración, y
    también las administra (Configuración → Tiempos de respuesta)."""

    def __init__(self, db: Session):
        self.db = db

    def cargar_parametros(self, festivos: set, proceso_id: int) -> ParametrosTiempo:
        solicitudes = {
            (r.solicitud, r.motivo): r.dias_habiles
            for r in self.db.execute(
                select(ReglaTiemposSolicitud).where(ReglaTiemposSolicitud.proceso_id == proceso_id)
            ).scalars()
        }
        prioridades = {r.prioridad_caso: r.dias_habiles for r in self.db.execute(select(ReglaTiemposPrioridad)).scalars()}
        prioridad_calendario = {
            r.prioridad_caso
            for r in self.db.execute(select(ReglaTiemposPrioridad)).scalars()
            if r.es_dia_calendario
        }
        nombres_eps = {e.id: e.nombre for e in self.db.execute(select(CatalogoEps)).scalars()}
        eps = {
            nombres_eps[r.eps_id]: r.dias_habiles
            for r in self.db.execute(
                select(ReglaTiemposEps).where(ReglaTiemposEps.proceso_id == proceso_id)
            ).scalars()
            if r.eps_id in nombres_eps
        }

        return ParametrosTiempo(
            dias_por_solicitud=solicitudes,
            dias_por_prioridad=prioridades,
            prioridad_es_calendario=prioridad_calendario,
            dias_por_eps=eps,
            festivos=festivos,
        )

    # ------------------------------------------------------------------
    # Listar para mostrar en Configuración (formato simple, no el que
    # consume el motor)
    # ------------------------------------------------------------------
    def listar_reglas_solicitud(self, proceso_id: int) -> list[dict]:
        return [
            {
                "solicitud": r.solicitud,
                "motivo": r.motivo or "",
                "dias_habiles": r.dias_habiles,
            }
            for r in self.db.execute(
                select(ReglaTiemposSolicitud).where(ReglaTiemposSolicitud.proceso_id == proceso_id)
            ).scalars()
        ]

    def listar_reglas_prioridad(self) -> list[dict]:
        return [
            {"prioridad_caso": r.prioridad_caso, "dias_habiles": r.dias_habiles, "es_dia_calendario": r.es_dia_calendario}
            for r in self.db.execute(select(ReglaTiemposPrioridad)).scalars()
        ]

    def listar_reglas_eps(self, proceso_id: int) -> list[dict]:
        nombres_eps = {e.id: e.nombre for e in self.db.execute(select(CatalogoEps)).scalars()}
        return [
            {"eps": nombres_eps.get(r.eps_id, f"(id {r.eps_id})"), "dias_habiles": r.dias_habiles}
            for r in self.db.execute(
                select(ReglaTiemposEps).where(ReglaTiemposEps.proceso_id == proceso_id)
            ).scalars()
        ]

    def cargar_festivos(self) -> set[dt.date]:
        return {f.fecha for f in self.db.execute(select(Festivo)).scalars()}

    def listar_festivos(self) -> list[dict]:
        return [
            {"fecha": f.fecha.isoformat(), "descripcion": f.descripcion or ""}
            for f in self.db.execute(select(Festivo)).scalars()
        ]

    # ------------------------------------------------------------------
    # Reemplazar todo (la pantalla de Configuración guarda la vista
    # completa de cada sub-pestaña de una sola vez)
    # ------------------------------------------------------------------
    def reemplazar_reglas_solicitud(self, proceso_id: int, filas: list[dict]) -> None:
        for r in self.db.execute(
            select(ReglaTiemposSolicitud).where(ReglaTiemposSolicitud.proceso_id == proceso_id)
        ).scalars():
            self.db.delete(r)
        self.db.flush()
        for f in filas:
            if not f["solicitud"]:
                continue
            self.db.add(
                ReglaTiemposSolicitud(
                    proceso_id=proceso_id,
                    solicitud=f["solicitud"],
                    motivo=f["motivo"] or None,
                    dias_habiles=int(f["dias_habiles"]),
                )
            )
        self.db.flush()

    def reemplazar_reglas_prioridad(self, filas: list[dict]) -> None:
        for r in self.db.execute(select(ReglaTiemposPrioridad)).scalars():
            self.db.delete(r)
        self.db.flush()
        for f in filas:
            if not f["prioridad_caso"]:
                continue
            self.db.add(
                ReglaTiemposPrioridad(
                    prioridad_caso=f["prioridad_caso"],
                    dias_habiles=int(f["dias_habiles"]),
                    es_dia_calendario=bool(f["es_dia_calendario"]),
                )
            )
        self.db.flush()

    def reemplazar_reglas_eps(self, proceso_id: int, filas: list[dict]) -> None:
        nombres_existentes = {e.nombre: e for e in self.db.execute(select(CatalogoEps)).scalars()}
        for r in self.db.execute(
            select(ReglaTiemposEps).where(ReglaTiemposEps.proceso_id == proceso_id)
        ).scalars():
            self.db.delete(r)
        self.db.flush()
        for f in filas:
            nombre = f["eps"]
            if not nombre:
                continue
            eps = nombres_existentes.get(nombre)
            if eps is None:
                eps = CatalogoEps(nombre=nombre, activo=True)
                self.db.add(eps)
                self.db.flush()
                nombres_existentes[nombre] = eps
            self.db.add(ReglaTiemposEps(proceso_id=proceso_id, eps_id=eps.id, dias_habiles=int(f["dias_habiles"])))
        self.db.flush()

    def reemplazar_festivos(self, filas: list[dict]) -> None:
        for f_orm in self.db.execute(select(Festivo)).scalars():
            self.db.delete(f_orm)
        self.db.flush()
        for f in filas:
            if not f["fecha"]:
                continue
            fecha = dt.datetime.strptime(f["fecha"], "%Y-%m-%d").date()
            self.db.add(Festivo(fecha=fecha, descripcion=f["descripcion"] or None))
        self.db.flush()