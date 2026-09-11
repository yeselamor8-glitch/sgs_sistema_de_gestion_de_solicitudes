"""
Semaforización GENERAL de la solicitud — mide días hábiles restantes
hasta `fecha_limite_respuesta`.

No confundir con motor_tiempos.indicador_oportunidad_traslado, que
mide un paso puntual del proceso (qué tan rápido se trasladó el
caso, sobre días YA TRANSCURRIDOS) y no cambia una vez ocurre el
traslado. Este motor mide días que FALTAN, sobre la fecha límite de
respuesta, y se recalcula cada vez que se consulta la solicitud
porque cambia todos los días aunque nadie la edite.

NOTA IMPORTANTE SOBRE EL UMBRAL ADOPTADO:
El indicador de oportunidad del traslado usa los cortes "<=1 dia =
A_TIEMPO, =2 = CERCA_DE_VENCIMIENTO, >2 = VENCIDO" sobre DÍAS
TRANSCURRIDOS (a más días usados, peor). Aquí se reutilizan los
mismos NÚMEROS (1 y 2) pero aplicados a DÍAS QUE FALTAN, donde la
lógica se invierte necesariamente: a menos días por delante, peor
semáforo. Es decir: <=1 día hábil restante (o ya vencida) = ROJO,
2 días restantes = AMARILLO, más de 2 = VERDE. Esta interpretación
no viene de una fórmula explícita del Excel (allí no existía una
semaforización general de 3 niveles) — es la que se acordó con el
usuario; si se quisiera otro corte, solo cambian los parámetros.
"""
from __future__ import annotations

import datetime as dt

from sgs.motores.motor_tiempos import es_dia_habil

VERDE = "VERDE"
AMARILLO = "AMARILLO"
ROJO = "ROJO"


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


def calcular_semaforo(
    hoy: dt.date,
    fecha_limite: dt.date | None,
    festivos: set[dt.date],
    dias_rojo_si_restan_hasta: int = 1,
    dias_amarillo_si_restan_hasta: int = 2,
) -> str:
    """
    fecha_limite=None -> VERDE (aún no hay fecha límite calculada,
    ej. falta la fecha de traslado; no se puede evaluar vencimiento).
    """
    if fecha_limite is None:
        return VERDE

    restantes = dias_habiles_restantes(hoy, fecha_limite, festivos)
    if restantes <= dias_rojo_si_restan_hasta:
        return ROJO
    if restantes <= dias_amarillo_si_restan_hasta:
        return AMARILLO
    return VERDE
