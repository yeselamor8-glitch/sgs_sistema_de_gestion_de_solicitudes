"""
Semaforización de una solicitud — en DOS fases, calculada SIEMPRE contra
la fecha actual (las vistas se recalculan al mostrar, para que "leer la
fecha de hoy" sea la única fuente de verdad):

    FASE 1 — sin fecha de traslado aún
        La fecha límite usa la MISMA jerarquía de tiempos que la fase 2
        (prioridad -> EPS -> solicitud -> fallback), partiendo de la FECHA
        DE INGRESO. La maestra solo define plazos propios para Riesgo
        Vital (1 día calendario) y Priorizado (2 días hábiles); "Riesgo
        simple" y las demás prioridades caen a sus tiempos de respuesta
        por proceso (EPS 3/5 días, solicitud 5, etc.). Se compara contra
        HOY: vencida/cerca/a tiempo según los días hábiles restantes.
        Ej.: ingreso 12-ago, Riesgo Vital (1 día), hoy 13-sep -> VENCIDA.

    FASE 2 — con fecha de traslado registrada
        La fecha límite de RESPUESTA viene de las reglas de tiempos
        (días hábiles según EPS/solicitud/motivo/prioridad por proceso,
        ya calculada y persistida al guardar el traslado). Se compara
        contra HOY con la misma regla de restantes.

    COMPLETADO — la solicitud ya se solucionó: hubo respuesta SI, o el
    ente de control recibió el radicado (se marcó el radicado). Tiene
    precedencia sobre las dos fases.

Colores: A_TIEMPO blanco, CERCA_DE_VENCIMIENTO amarillo, VENCIDO rojo,
COMPLETADO verde, SIN_FECHA gris (sin datos suficientes para evaluar).

El umbral "cerca de vencer" (amarillo) es configurable desde
Configuración → Semaforización: `calcular_semaforo_solicitud` acepta
`dias_habiles_cerca` (una solicitud está en amarillo si le quedan ese
número de días hábiles o menos). Si no se pasa, usa el valor por defecto
`DIAS_HABILES_CERCA`.
"""
from __future__ import annotations

import datetime as dt

from sgs.motores.motor_tiempos import (
    ParametrosTiempo,
    calcular_fecha_limite,
    es_dia_habil,
)

A_TIEMPO = "A_TIEMPO"
CERCA_DE_VENCIMIENTO = "CERCA_DE_VENCIMIENTO"
VENCIDO = "VENCIDO"
SIN_FECHA = "SIN_FECHA"
COMPLETADO = "COMPLETADO"

# Orden de urgencia para ordenar listados de solicitudes: lo más urgente
# primero. Fuente única de verdad — la usan la capa de aplicación
# (orden por defecto del módulo Solicitudes) y la UI (orden manual por
# clic en la columna Semáforo). Valores más bajos = más urgente.
ORDEN_URGENCIA: dict[str, int] = {
    VENCIDO: 0,
    CERCA_DE_VENCIMIENTO: 1,
    A_TIEMPO: 2,
    SIN_FECHA: 3,
    COMPLETADO: 4,
}

# Rango por defecto para códigos desconocidos: van al final (menos urgentes).
_RANGO_DESCONOCIDO = max(ORDEN_URGENCIA.values()) + 1


def rango_urgencia(color: str | None) -> int:
    """Posición de un color de semáforo en el orden de urgencia (menor =
    más urgente). Códigos desconocidos o None van al final."""
    return ORDEN_URGENCIA.get(color or "", _RANGO_DESCONOCIDO)

# Umbral "cerca" por defecto: 0 o 1 días hábiles restantes antes de la
# fecha límite (vence hoy o mañana hábil) -> amarillo; 2+ -> blanco;
# negativo -> rojo. Es solo el valor por defecto; el configurado en
# Configuración → Semaforización lo reemplaza vía `dias_habiles_cerca`.
DIAS_HABILES_CERCA = 1


def dias_habiles_restantes(hoy: dt.date, fecha_limite: dt.date, festivos: set[dt.date]) -> int:
    """Positivo = quedan días; 0 = vence hoy; negativo = ya venció (magnitud = días de mora)."""
    if fecha_limite < hoy:
        dias = 0
        fecha = fecha_limite
        while fecha < hoy:
            fecha += dt.timedelta(days=1)
            if es_dia_habil(fecha, festivos):
                dias += 1
        return -dias

    dias = 0
    fecha = hoy
    while fecha < fecha_limite:
        fecha += dt.timedelta(days=1)
        if es_dia_habil(fecha, festivos):
            dias += 1
    return dias


def _semaforo_por_dias_restantes(dias_restantes: int, dias_habiles_cerca: int = DIAS_HABILES_CERCA) -> str:
    if dias_restantes < 0:
        return VENCIDO
    if dias_restantes <= dias_habiles_cerca:
        return CERCA_DE_VENCIMIENTO
    return A_TIEMPO


def calcular_semaforo_solicitud(
    hoy: dt.date,
    *,
    fecha_ingreso: dt.date | None,
    fecha_traslado: dt.date | None,
    fecha_limite_respuesta: dt.date | None,
    prioridad_caso: str | None,
    eps: str | None = None,
    solicitud: str | None = None,
    motivo: str | None = None,
    parametros: ParametrosTiempo,
    hubo_respuesta: str | None = None,
    radicado_ente_control: str | None = None,
    estado_gestion: str | None = None,
    dias_habiles_cerca: int = DIAS_HABILES_CERCA,
) -> str:
    """
    Semáforo completo de la solicitud (fases 1/2 + COMPLETADO) contra la
    fecha `hoy`. `parametros` debe traer las reglas completas de tiempos
    (prioridad, EPS, solicitud y festivos); en fase 2 la fecha límite de
    respuesta ya viene persistida del traslado.

    COMPLETADO: la solicitud ya se solucionó — hubo respuesta SI, el ente
    de control recibió su radicado, o el estado de gestión quedó en
    "Solucionada". Tiene precedencia sobre las dos fases.
    """
    if (hubo_respuesta or "").strip().upper() == "SI":
        return COMPLETADO
    if (radicado_ente_control or "").strip():
        return COMPLETADO
    if (estado_gestion or "").strip().lower() == "solucionada":
        return COMPLETADO

    if fecha_traslado is None:
        # Fase 1 — plazo partiendo de la FECHA DE INGRESO con la misma
        # jerarquía de la fase 2: Riesgo Vital (calendario) > Priorizado
        # (hábiles) > EPS/solicitud > fallback. Así "Riesgo simple" usa
        # los tiempos de respuesta de su proceso.
        if not fecha_ingreso:
            return SIN_FECHA
        fecha_limite, _ = calcular_fecha_limite(
            fecha_ingreso,
            prioridad_caso,
            eps,
            solicitud,
            parametros,
            motivo=motivo,
        )
    else:
        # Fase 2 — fecha límite de RESPUESTA ya calculada por las reglas
        # de tiempos de su proceso (EPS/solicitud/motivo/prioridad)
        if not fecha_limite_respuesta:
            return SIN_FECHA
        fecha_limite = fecha_limite_respuesta

    return _semaforo_por_dias_restantes(
        dias_habiles_restantes(hoy, fecha_limite, parametros.festivos), dias_habiles_cerca
    )


def calcular_semaforo(indicador_oportunidad: str | None) -> str:
    """
    Compatibilidad: mapea el INDICADOR del paso de traslado (columna AD
    de la maestra) al estado de semaforización. Ya NO alimenta el semáforo
    de la solicitud (eso es `calcular_semaforo_solicitud`); se conserva
    solo para mostrar el indicador del paso de traslado.
    """
    if indicador_oportunidad in (A_TIEMPO, CERCA_DE_VENCIMIENTO, VENCIDO):
        return indicador_oportunidad
    return SIN_FECHA