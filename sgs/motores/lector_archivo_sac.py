"""
Lectura de archivos exportados desde SAC (.xls legado o .xlsx).

Solo lee y convierte a estructuras simples (encabezados + filas como
list[dict]) — no valida reglas de negocio ni clasifica (eso es
sgs.motores.motor_importacion_sac). Mantenerlo separado permite
probar el motor sin depender de archivos reales.
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
        return _leer_xls(ruta)
    raise ValueError("Formato no soportado: solo se aceptan archivos .xls o .xlsx exportados de SAC.")


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


def _leer_xls(ruta: str) -> ArchivoSacLeido:
    import xlrd

    wb = xlrd.open_workbook(ruta)
    ws = wb.sheet_by_index(0)
    encabezados = [str(h).strip() for h in ws.row_values(0)]
    filas = []
    for i in range(1, ws.nrows):
        valores = ws.row_values(i)
        if all(v == "" for v in valores):
            continue
        filas.append(dict(zip(encabezados, valores)))
    return ArchivoSacLeido(encabezados=encabezados, filas=filas)