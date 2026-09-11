"""
Motor de análisis / tabla dinámica.

Trabaja sobre pandas DataFrames construidos a partir de list[dict] —
sean datos del sistema (vía casos_de_uso) o de un archivo SAC cargado
temporalmente (vía lector_archivo_sac), sin distinguir el origen: es
la misma función la que analiza ambos (sección 24/28-31 del documento
funcional). No conoce SQLAlchemy ni PySide6.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

Operador = Literal["igual_a", "distinto_de", "contiene", "mayor_que", "menor_que"]
FuncionAgregacion = Literal["contar", "sumar", "promedio", "minimo", "maximo"]

_FUNC_PANDAS = {
    "contar": "count",
    "sumar": "sum",
    "promedio": "mean",
    "minimo": "min",
    "maximo": "max",
}

_UNIDAD_FECHA_A_FREQ = {"dia": "D", "semana": "W", "mes": "M", "año": "Y"}


@dataclass(frozen=True)
class Filtro:
    columna: str
    operador: Operador
    valor: object


def cargar_dataframe(filas: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(filas)


def seleccionar_columnas(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Muestra/oculta y reordena — `columnas` ya viene en el orden deseado."""
    columnas_validas = [c for c in columnas if c in df.columns]
    return df[columnas_validas]


def aplicar_filtros(df: pd.DataFrame, filtros: list[Filtro]) -> pd.DataFrame:
    resultado = df
    for f in filtros:
        if f.columna not in resultado.columns:
            continue
        serie = resultado[f.columna]
        if f.operador == "igual_a":
            resultado = resultado[serie.astype(str).str.lower() == str(f.valor).lower()]
        elif f.operador == "distinto_de":
            resultado = resultado[serie.astype(str).str.lower() != str(f.valor).lower()]
        elif f.operador == "contiene":
            resultado = resultado[serie.astype(str).str.lower().str.contains(str(f.valor).lower(), na=False)]
        elif f.operador == "mayor_que":
            resultado = resultado[pd.to_numeric(serie, errors="coerce") > float(f.valor)]
        elif f.operador == "menor_que":
            resultado = resultado[pd.to_numeric(serie, errors="coerce") < float(f.valor)]
    return resultado


def ordenar(df: pd.DataFrame, columna: str, ascendente: bool = True) -> pd.DataFrame:
    if columna not in df.columns:
        return df
    return df.sort_values(by=columna, ascending=ascendente)


def agrupar_fecha(df: pd.DataFrame, columna: str, unidad: str, nueva_columna: str | None = None) -> pd.DataFrame:
    """Agrega una columna con la fecha truncada a día/semana/mes/año,
    para poder agrupar por ella después (sección 29 — 'agrupaciones por fecha')."""
    if columna not in df.columns:
        return df
    freq = _UNIDAD_FECHA_A_FREQ.get(unidad, "D")
    destino = nueva_columna or f"{columna}_{unidad}"
    resultado = df.copy()
    fechas = pd.to_datetime(resultado[columna], errors="coerce")
    resultado[destino] = fechas.dt.to_period(freq).astype(str)
    return resultado


def agrupar_y_agregar(
    df: pd.DataFrame, columnas_agrupar: list[str], columna_valor: str | None, funcion: FuncionAgregacion
) -> pd.DataFrame:
    columnas_agrupar = [c for c in columnas_agrupar if c in df.columns]
    if not columnas_agrupar:
        return df

    if funcion == "contar" or columna_valor is None or columna_valor not in df.columns:
        resultado = df.groupby(columnas_agrupar, dropna=False).size().reset_index(name="conteo")
        return resultado

    func_pandas = _FUNC_PANDAS[funcion]
    serie_numerica = pd.to_numeric(df[columna_valor], errors="coerce")
    df_temp = df.copy()
    df_temp["_valor_"] = serie_numerica
    resultado = (
        df_temp.groupby(columnas_agrupar, dropna=False)["_valor_"]
        .agg(func_pandas)
        .reset_index(name=f"{funcion}_{columna_valor}")
    )
    return resultado


def tabla_dinamica(
    df: pd.DataFrame,
    filas: list[str],
    columnas: list[str],
    valores: str,
    funcion: FuncionAgregacion = "contar",
) -> pd.DataFrame:
    func_pandas = "size" if funcion == "contar" else _FUNC_PANDAS[funcion]
    df_temp = df.copy()
    if funcion != "contar" and valores in df_temp.columns:
        df_temp[valores] = pd.to_numeric(df_temp[valores], errors="coerce")

    pivote = pd.pivot_table(
        df_temp,
        index=filas or None,
        columns=columnas or None,
        values=valores if valores in df_temp.columns else None,
        aggfunc=func_pandas,
        fill_value=0,
    )
    return pivote.reset_index()


def exportar_excel(df: pd.DataFrame, ruta: str) -> None:
    df.to_excel(ruta, index=False)