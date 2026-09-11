"""
Motor de clasificación automática de solicitudes.

Evalúa las reglas configurables (tabla reglas_clasificacion +
condiciones_regla) contra los datos de una solicitud proveniente de
SAC. Implementa exactamente el patrón confirmado en el instructivo
de maestras:

  * Varios valores en una misma condición (mismo campo)  -> OR
  * Varias condiciones dentro de una regla (campos distintos) -> AND
  * Reglas tipo 'excepcion' se evalúan ANTES que las 'normal', en
    orden_evaluacion ascendente, y si una excepción aplica, GANA
    sobre cualquier regla normal (ej. caso PO+medicina general de
    OTRAS_EPS que en realidad pertenece a PPNA).
  * Si ninguna regla aplica -> estado 'sin_clasificar'
  * Si más de una regla (no relacionada por excepción) aplica ->
    estado 'conflicto', para revisión del administrador.

No conoce SQLAlchemy: recibe estructuras simples para poder
reutilizarse también sobre un archivo SAC cargado en memoria sin
tocar la base de datos operativa (sección 24 del documento
funcional — "análisis directo de archivos SAC").
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Operador(str, Enum):
    IGUAL_A = "igual_a"
    DISTINTO_DE = "distinto_de"
    CONTIENE = "contiene"


@dataclass(frozen=True)
class Condicion:
    campo: str
    operador: Operador
    valores: tuple[str, ...]  # OR entre estos valores


@dataclass(frozen=True)
class Regla:
    proceso_id: int
    orden_evaluacion: int
    tipo_regla: str  # 'excepcion' | 'normal'
    condiciones: tuple[Condicion, ...]  # AND entre estas condiciones


@dataclass(frozen=True)
class ResultadoClasificacion:
    estado: str  # 'clasificada' | 'sin_clasificar' | 'conflicto'
    proceso_id: int | None
    procesos_en_conflicto: tuple[int, ...] = ()
    regla_aplicada: Regla | None = None


def _condicion_cumple(condicion: Condicion, datos: dict[str, str | None]) -> bool:
    valor = datos.get(condicion.campo)
    if valor is None:
        return False
    valor_norm = valor.strip().lower()
    valores_norm = [v.strip().lower() for v in condicion.valores]

    if condicion.operador == Operador.IGUAL_A:
        return valor_norm in valores_norm
    if condicion.operador == Operador.DISTINTO_DE:
        return valor_norm not in valores_norm
    if condicion.operador == Operador.CONTIENE:
        return any(v in valor_norm for v in valores_norm)
    raise ValueError(f"Operador no soportado: {condicion.operador}")


def _regla_cumple(regla: Regla, datos: dict[str, str | None]) -> bool:
    return all(_condicion_cumple(c, datos) for c in regla.condiciones)


def clasificar(datos: dict[str, str | None], reglas: list[Regla]) -> ResultadoClasificacion:
    reglas_ordenadas = sorted(reglas, key=lambda r: (r.tipo_regla != "excepcion", r.orden_evaluacion))

    for regla in reglas_ordenadas:
        if regla.tipo_regla == "excepcion" and _regla_cumple(regla, datos):
            return ResultadoClasificacion(
                estado="clasificada", proceso_id=regla.proceso_id, regla_aplicada=regla
            )

    procesos_que_aplican = [
        regla for regla in reglas_ordenadas if regla.tipo_regla == "normal" and _regla_cumple(regla, datos)
    ]

    if not procesos_que_aplican:
        return ResultadoClasificacion(estado="sin_clasificar", proceso_id=None)

    if len(procesos_que_aplican) > 1:
        ids = tuple(sorted({r.proceso_id for r in procesos_que_aplican}))
        if len(ids) == 1:
            # varias reglas del mismo proceso aplican -> no es conflicto real
            return ResultadoClasificacion(
                estado="clasificada", proceso_id=ids[0], regla_aplicada=procesos_que_aplican[0]
            )
        return ResultadoClasificacion(
            estado="conflicto", proceso_id=None, procesos_en_conflicto=ids
        )

    regla = procesos_que_aplican[0]
    return ResultadoClasificacion(estado="clasificada", proceso_id=regla.proceso_id, regla_aplicada=regla)
