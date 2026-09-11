"""
Motor de importación SAC.

No conoce SQLAlchemy ni cómo leer un .xls/.xlsx — recibe filas ya
parseadas (list[dict], una por solicitud, claves = encabezados del
exporte SAC) y una foto de lo que ya existe en el sistema
(numero_solicitud_sac -> dict con los mismos campos SAC guardados la
última vez). Esto lo hace 100% testeable con pytest y reutilizable
para el "análisis directo de archivos SAC" (sección 24 del documento
funcional) sin tocar la base de datos operativa.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sgs.motores.motor_clasificacion import Regla, clasificar

COLUMNAS_REQUERIDAS = [
    "numerosolicitud",
    "fechasolicitud",
    "motivo",
    "tipoasuntosol",
    "solicitud",
]

# Campos del bloque SAC que se comparan para decidir "actualizado" vs
# "sin_cambios" -- son los mismos que la app trata como de solo lectura
# (sac_*). Si SAC cambia cualquiera de estos, se actualiza; los campos
# de gestión (fecha_traslado, respuesta, observaciones, etc.) NUNCA se
# tocan aquí (separación acordada en la Fase 2).
CAMPOS_SAC_COMPARABLES = [
    "motivo",
    "tipoasuntosol",
    "solicitud",
    "subclasificacion",
    "detalle",
    "prioridad_caso",
    "tipoidentificacion",
    "numeroidentificacion",
    "detallesolicitud",
    "tipo_pqr",
    "estadosolicitud",
    "barrera_acceso",
    "grupopoblacional",
]
# NOTA: barrera_acceso, epsvigentesg y estado (SAC) todavía no tienen
# columna sac_* en el modelo `Solicitud` (Fase 3) — cuando se agreguen,
# sumarlas aquí Y en importacion_sac_repo.MAPEO_CAMPOS_SAC juntas, para
# no comparar un campo que no se está guardando.


@dataclass(frozen=True)
class ResultadoFila:
    numero_solicitud_sac: str
    accion: str  # 'nuevo' | 'actualizado' | 'sin_cambios' | 'error'
    clasificacion_estado: str | None = None  # 'clasificada' | 'sin_clasificar' | 'conflicto'
    proceso_id: int | None = None
    errores: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResumenImportacion:
    total: int
    nuevos: int
    actualizados: int
    sin_cambios: int
    errores: int
    sin_clasificar: int
    conflictos: int
    resultados: tuple[ResultadoFila, ...]
    duplicados_archivo: tuple[str, ...] = ()
    duplicados_existentes: tuple[str, ...] = ()


def detectar_duplicados(filas: list[dict], existentes: dict[str, dict]) -> tuple[list[str], list[str]]:
    """Devuelve (duplicados dentro del archivo, duplicados ya registrados en BD)."""
    conteos: dict[str, int] = {}
    for fila in filas:
        numero = _numero_solicitud(fila)
        if numero:
            conteos[numero] = conteos.get(numero, 0) + 1

    duplicados_archivo = sorted(numero for numero, total in conteos.items() if total > 1)
    duplicados_existentes = sorted(numero for numero in conteos if numero in existentes)
    return duplicados_archivo, duplicados_existentes


def validar_estructura(encabezados: list[str]) -> list[str]:
    """Devuelve la lista de columnas requeridas que faltan (vacía = estructura OK)."""
    presentes = {e.strip().lower() for e in encabezados if e}
    return [c for c in COLUMNAS_REQUERIDAS if c.lower() not in presentes]


def _normalizar_numero_solicitud(valor) -> str | None:
    if valor is None:
        return None

    if isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float)):
        try:
            numero = Decimal(str(valor))
        except InvalidOperation:
            return str(valor).strip()
        if numero == numero.to_integral_value():
            return str(numero.quantize(Decimal("1")))
        return format(numero.normalize(), "f").rstrip("0").rstrip(".")

    texto = str(valor).strip()
    if not texto:
        return None

    texto = texto.replace(" ", "")
    if texto.endswith(".0") and re.fullmatch(r"[-+]?\d+\.0", texto):
        texto = texto[:-2]
    if texto.endswith("/0") and re.fullmatch(r"[-+]?\d+/0", texto):
        texto = texto[:-2]
    return texto


def _numero_solicitud(fila: dict) -> str | None:
    valor = fila.get("numerosolicitud")
    return _normalizar_numero_solicitud(valor)


def _fila_cambio(fila_nueva: dict, fila_existente: dict) -> bool:
    for campo in CAMPOS_SAC_COMPARABLES:
        if str(fila_nueva.get(campo, "") or "").strip() != str(fila_existente.get(campo, "") or "").strip():
            return True
    return False


def procesar_fila(fila: dict, existentes: dict[str, dict], reglas: list[Regla]) -> ResultadoFila:
    numero = _numero_solicitud(fila)
    if not numero:
        return ResultadoFila(
            numero_solicitud_sac="(sin número)", accion="error", errores=("Falta 'numerosolicitud'.",)
        )

    faltantes = [c for c in COLUMNAS_REQUERIDAS if not str(fila.get(c, "") or "").strip()]
    if faltantes:
        return ResultadoFila(
            numero_solicitud_sac=numero,
            accion="error",
            errores=tuple(f"Falta valor en '{c}'." for c in faltantes),
        )

    datos_clasificacion = dict(fila)
    datos_clasificacion.setdefault("detalle", fila.get("detallesolicitud"))
    datos_clasificacion.setdefault("tipoasuntosol", fila.get("tipo_pqr"))
    resultado_clasificacion = clasificar(datos_clasificacion, reglas)

    existente = existentes.get(numero)
    if existente is None:
        accion = "nuevo"
    elif _fila_cambio(fila, existente):
        accion = "actualizado"
    else:
        accion = "sin_cambios"

    return ResultadoFila(
        numero_solicitud_sac=numero,
        accion=accion,
        clasificacion_estado=resultado_clasificacion.estado,
        proceso_id=resultado_clasificacion.proceso_id,
    )


def procesar_archivo(
    filas: list[dict], existentes: dict[str, dict], reglas: list[Regla]
) -> ResumenImportacion:
    resultados = [procesar_fila(fila, existentes, reglas) for fila in filas]

    def contar(pred) -> int:
        return sum(1 for r in resultados if pred(r))

    return ResumenImportacion(
        total=len(resultados),
        nuevos=contar(lambda r: r.accion == "nuevo"),
        actualizados=contar(lambda r: r.accion == "actualizado"),
        sin_cambios=contar(lambda r: r.accion == "sin_cambios"),
        errores=contar(lambda r: r.accion == "error"),
        sin_clasificar=contar(lambda r: r.clasificacion_estado == "sin_clasificar"),
        conflictos=contar(lambda r: r.clasificacion_estado == "conflicto"),
        resultados=tuple(resultados),
    )