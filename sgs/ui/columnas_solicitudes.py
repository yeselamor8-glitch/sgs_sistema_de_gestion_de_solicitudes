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
    DefinicionColumna("semaforo", "Semáforo", 90),
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