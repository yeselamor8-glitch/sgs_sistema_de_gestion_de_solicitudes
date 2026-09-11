"""
Motor de tiempos de respuesta.

Implementa EXACTAMENTE la jerarquía encontrada en la fórmula de la
columna AE de la hoja MAESTRA (ver informe de análisis):

    1. prioridad_caso == 'Riesgo Vital'  -> fecha_traslado + 1 día CALENDARIO
    2. prioridad_caso == 'Priorizado'    -> +2 días HÁBILES
    3. la EPS tiene override de días     -> +días_habiles_eps
    4. la 'solicitud' tiene tiempo definido -> +días_habiles_solicitud
       (si el tiempo definido es 0 -> mismo día)
    5. no hay regla aplicable            -> fallback +10 días hábiles

CORRECCIÓN respecto al Excel original (hallazgo maestra DISCAPACIDAD):
dentro del paso 4, si `motivo` es Reclamación/Queja y existe una fila
de tiempos específica para esa combinación (solicitud, motivo), esa
fila tiene prioridad sobre el tiempo "general" de esa misma solicitud.
En el Excel original el VLOOKUP solo buscaba por `solicitud` y
encontraba siempre la primera fila (la de motivo=Gestión), por lo que
las reclamaciones/quejas nunca recibían su plazo real de 15 días. Este
motor corrige eso.

No conoce SQLAlchemy: recibe parámetros simples para ser 100%
testeable con pytest y reutilizable en el módulo de "análisis directo
de archivo SAC" sin pasar por la base de datos operativa.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


FALLBACK_DIAS_HABILES = 10


def es_dia_habil(fecha: dt.date, festivos: set[dt.date]) -> bool:
    return fecha.weekday() < 5 and fecha not in festivos


def sumar_dias_habiles(fecha_inicio: dt.date, dias: int, festivos: set[dt.date]) -> dt.date:
    """Equivalente a WORKDAY() de Excel."""
    fecha = fecha_inicio
    restantes = dias
    paso = 1 if dias >= 0 else -1
    while restantes != 0:
        fecha += dt.timedelta(days=paso)
        if es_dia_habil(fecha, festivos):
            restantes -= paso
    return fecha


MOTIVOS_RECLAMACION = {"reclamación", "reclamacion", "queja"}


@dataclass(frozen=True)
class ParametrosTiempo:
    # clave (solicitud, motivo) -> días hábiles. motivo=None es la regla
    # general ("Gestión"); una clave con motivo específico (ej. 'Queja')
    # tiene prioridad sobre la de motivo=None para la misma solicitud.
    dias_por_solicitud: dict[tuple[str, str | None], int]
    dias_por_prioridad: dict[str, int]        # 'Riesgo Vital' / 'Priorizado' -> días
    prioridad_es_calendario: set[str]         # ej. {'Riesgo Vital'}
    dias_por_eps: dict[str, int]              # nombre EPS -> días hábiles override
    festivos: set[dt.date]


def _buscar_dias_solicitud(
    solicitud: str, motivo: str | None, tabla: dict[tuple[str, str | None], int]
) -> tuple[int, str] | None:
    """Motivo Reclamación/Queja tiene prioridad sobre la regla general de esa
    misma solicitud (corrige el bug del VLOOKUP original, ver docstring del módulo)."""
    if motivo and motivo.strip().lower() in MOTIVOS_RECLAMACION:
        clave_especifica = (solicitud, motivo)
        if clave_especifica in tabla:
            return tabla[clave_especifica], f"solicitud_reclamacion:{solicitud}|{motivo}"
        # buscar cualquier override de reclamación/queja para esa solicitud
        for (s, m), dias in tabla.items():
            if s == solicitud and m and m.strip().lower() in MOTIVOS_RECLAMACION:
                return dias, f"solicitud_reclamacion:{solicitud}|{m}"

    clave_general = (solicitud, None)
    if clave_general in tabla:
        return tabla[clave_general], f"solicitud:{solicitud}"

    return None


def calcular_fecha_limite(
    fecha_traslado: dt.date,
    prioridad_caso: str | None,
    eps: str | None,
    solicitud: str | None,
    parametros: ParametrosTiempo,
    motivo: str | None = None,
) -> tuple[dt.date, str]:
    """
    Devuelve (fecha_limite, regla_aplicada) — la regla_aplicada se
    conserva para trazabilidad/depuración, no solo el resultado.
    """
    if prioridad_caso in parametros.prioridad_es_calendario:
        dias = parametros.dias_por_prioridad.get(prioridad_caso, 1)
        return fecha_traslado + dt.timedelta(days=dias), f"prioridad_calendario:{prioridad_caso}"

    if prioridad_caso in parametros.dias_por_prioridad:
        dias = parametros.dias_por_prioridad[prioridad_caso]
        return sumar_dias_habiles(fecha_traslado, dias, parametros.festivos), f"prioridad_habil:{prioridad_caso}"

    if eps and eps in parametros.dias_por_eps:
        dias = parametros.dias_por_eps[eps]
        return sumar_dias_habiles(fecha_traslado, dias, parametros.festivos), f"eps:{eps}"

    if solicitud:
        encontrado = _buscar_dias_solicitud(solicitud, motivo, parametros.dias_por_solicitud)
        if encontrado is not None:
            dias, regla = encontrado
            if dias == 0:
                return fecha_traslado, regla.replace("solicitud", "solicitud_mismo_dia", 1)
            return sumar_dias_habiles(fecha_traslado, dias, parametros.festivos), regla

    return (
        sumar_dias_habiles(fecha_traslado, FALLBACK_DIAS_HABILES, parametros.festivos),
        "fallback_10_dias",
    )


def calcular_oportunidad_traslado(
    fecha_ingreso: dt.date, fecha_traslado: dt.date, festivos: set[dt.date]
) -> int:
    """Días hábiles transcurridos entre el ingreso y el traslado (columna AC)."""
    dias = 0
    fecha = fecha_ingreso
    while fecha < fecha_traslado:
        fecha += dt.timedelta(days=1)
        if es_dia_habil(fecha, festivos):
            dias += 1
    return dias - 1


def indicador_oportunidad_traslado(dias_habiles_transcurridos: int) -> str:
    """Columna AD — semaforización del PASO de traslado, no de la solicitud completa."""
    if dias_habiles_transcurridos <= 1:
        return "A_TIEMPO"
    if dias_habiles_transcurridos == 2:
        return "CERCA_DE_VENCIMIENTO"
    return "VENCIDO"
