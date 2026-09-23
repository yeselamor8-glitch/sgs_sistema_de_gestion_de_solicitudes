"""
Catálogo de columnas disponibles para la tabla de Solicitudes.

Una sola fuente de verdad: tanto la tabla como el diálogo de
"Personalizar columnas" leen de aquí. Cubre los campos que el
análisis de las maestras marcó como importantes (bloque SAC +
asignación + tiempos/semaforización + gestión).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DefinicionColumna:
    clave: str
    etiqueta: str
    ancho_defecto: int
    visible_defecto: bool = True


COLUMNAS_DISPONIBLES: list[DefinicionColumna] = [
    DefinicionColumna("numero_solicitud_sac", "N.° solicitud SAC", 140),
    DefinicionColumna("semaforo", "Semáforo", 155),
    DefinicionColumna("nombre_ciudadano", "Ciudadano", 200),
    DefinicionColumna("documento", "Documento", 120),
    DefinicionColumna("proceso", "Proceso", 190),
    DefinicionColumna("funcionario", "Funcionario", 160),
    DefinicionColumna("motivo", "Motivo", 160, visible_defecto=False),
    DefinicionColumna("tipo_asunto", "Tipo de asunto", 180, visible_defecto=False),
    DefinicionColumna("solicitud", "Solicitud", 170),
    DefinicionColumna("prioridad_caso", "Prioridad", 110),
    DefinicionColumna("eps", "EPS", 130, visible_defecto=False),
    DefinicionColumna("fecha_ingreso", "Fecha ingreso", 120),
    DefinicionColumna("fecha_limite", "Fecha límite", 120),
    DefinicionColumna("estado_sac", "Estado SAC", 130),
    DefinicionColumna("estado_gestion", "Estado de gestión", 140, visible_defecto=False),
    DefinicionColumna("clasificacion_estado", "Clasificación", 130, visible_defecto=False),
]

CLAVES_POR_DEFECTO_VISIBLES = [c.clave for c in COLUMNAS_DISPONIBLES if c.visible_defecto]


def configuracion_por_defecto() -> list[dict]:
    """[{clave, visible, ancho}] en el orden por defecto — lo que
    devuelve 'Restablecer vista predeterminada'."""
    return [
        {"clave": c.clave, "visible": c.visible_defecto, "ancho": c.ancho_defecto}
        for c in COLUMNAS_DISPONIBLES
    ]


def etiqueta_de(clave: str) -> str:
    for c in COLUMNAS_DISPONIBLES:
        if c.clave == clave:
            return c.etiqueta
    return clave


# Columnas cuyo valor es una fecha ISO (yyyy-mm-dd); se ordenan como fecha
# (el vacío va al final) en vez de como texto.
_COLUMNAS_FECHA = {"fecha_ingreso", "fecha_limite"}


def _clave_orden(fila: dict, clave: str):
    """Clave de ordenamiento tipada para una fila de la tabla de
    Solicitudes, según la columna. Devuelve una tupla (flag_vacio, valor)
    para que los vacíos queden siempre al final sin importar la dirección."""
    valor = fila.get(clave, "")
    if clave == "semaforo":
        from sgs.motores import motor_semaforo

        return (0, motor_semaforo.rango_urgencia(valor))
    if clave in _COLUMNAS_FECHA:
        texto = str(valor or "")
        # Las fechas ISO ordenan bien como texto; el vacío va al final.
        return (1, "") if texto == "" else (0, texto)
    texto = str(valor or "").lower()
    return (1, "") if texto == "" else (0, texto)


def ordenar_filas(filas: list[dict], clave: str, descendente: bool) -> list[dict]:
    """Ordena las filas de la tabla de Solicitudes por la columna `clave`.

    Reglas por tipo de columna:
      * ``semaforo``  -> por urgencia (VENCIDO primero), no alfabético.
      * ``fecha_*``   -> como fecha ISO (los vacíos al final).
      * resto         -> texto en minúscula (los vacíos al final).

    Los vacíos quedan siempre al final gracias al flag de la clave, que no
    se invierte con `descendente` (solo se invierte el valor)."""
    def key(fila: dict):
        flag_vacio, valor = _clave_orden(fila, clave)
        if descendente:
            # Invertir solo el valor, no el flag de vacío.
            if isinstance(valor, (int, float)):
                return (flag_vacio, -valor)
            return (flag_vacio, _TextoInverso(valor))
        return (flag_vacio, valor)

    return sorted(filas, key=key)


class _TextoInverso:
    """Envuelve un texto para poder ordenarlo en orden inverso dentro de
    `sorted` sin usar reverse (que también invertiría el flag de vacío)."""

    __slots__ = ("valor",)

    def __init__(self, valor: str):
        self.valor = valor

    def __lt__(self, otro: "_TextoInverso") -> bool:
        return self.valor > otro.valor

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, _TextoInverso) and self.valor == otro.valor