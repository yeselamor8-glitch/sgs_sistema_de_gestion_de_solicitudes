"""
Lectura de archivos exportados desde SAC (solo libro de Excel .xlsx).

Solo lee y convierte a estructuras simples (encabezados + filas como
list[dict]) — no valida reglas de negocio ni clasifica (eso es
sgs.motores.motor_importacion_sac). Mantenerlo separado permite
probar el motor sin depender de archivos reales.

Nota: el formato .xls legado ya no es compatible (generaba problemas
de lectura). Solo se admite el libro de Excel moderno (.xlsx).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchivoSacLeido:
    encabezados: list[str]
    filas: list[dict]


def leer_archivo_sac(ruta: str) -> ArchivoSacLeido:
    if ruta.lower().endswith(".xlsx"):
        return _leer_xlsx(ruta)
    if ruta.lower().endswith(".xls"):
        raise ValueError(
            "Solo se admite el formato libro de Excel (.xlsx). "
            "El formato .xls ya no es compatible; vuelve a exportar o guarda el archivo como .xlsx."
        )
    raise ValueError("Formato no soportado: solo se admite el libro de Excel (.xlsx) exportado de SAC.")


def _leer_xlsx(ruta: str) -> ArchivoSacLeido:
    import openpyxl

    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    filas_iter = ws.iter_rows(values_only=True)
    encabezados = [str(h).strip() if h is not None else "" for h in next(filas_iter)]
    filas = []
    for fila in filas_iter:
        if fila[0] is None and all(v is None for v in fila):
            continue
        filas.append(dict(zip(encabezados, fila)))
    return ArchivoSacLeido(encabezados=encabezados, filas=filas)