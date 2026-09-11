from sgs.motores.motor_analisis import (
    Filtro,
    agrupar_fecha,
    agrupar_y_agregar,
    aplicar_filtros,
    cargar_dataframe,
    ordenar,
    seleccionar_columnas,
    tabla_dinamica,
)

FILAS = [
    {"proceso": "Traslado", "eps": "Savia Salud", "dias": 5, "fecha_ingreso": "2026-08-05"},
    {"proceso": "Traslado", "eps": "Suramericana", "dias": 3, "fecha_ingreso": "2026-08-20"},
    {"proceso": "Especialistas", "eps": "Savia Salud", "dias": 10, "fecha_ingreso": "2026-09-01"},
    {"proceso": "Especialistas", "eps": "Savia Salud", "dias": 2, "fecha_ingreso": "2026-09-02"},
]


def test_seleccionar_columnas_respeta_orden_y_visibilidad():
    df = cargar_dataframe(FILAS)
    resultado = seleccionar_columnas(df, ["proceso", "dias"])
    assert list(resultado.columns) == ["proceso", "dias"]


def test_filtro_igual_a():
    df = cargar_dataframe(FILAS)
    resultado = aplicar_filtros(df, [Filtro("proceso", "igual_a", "Traslado")])
    assert len(resultado) == 2


def test_filtro_contiene_es_insensible_a_mayusculas():
    df = cargar_dataframe(FILAS)
    resultado = aplicar_filtros(df, [Filtro("eps", "contiene", "savia")])
    assert len(resultado) == 3


def test_filtro_mayor_que_numerico():
    df = cargar_dataframe(FILAS)
    resultado = aplicar_filtros(df, [Filtro("dias", "mayor_que", 4)])
    assert len(resultado) == 2


def test_ordenar_ascendente_y_descendente():
    df = cargar_dataframe(FILAS)
    asc = ordenar(df, "dias", ascendente=True)
    assert asc.iloc[0]["dias"] == 2
    desc = ordenar(df, "dias", ascendente=False)
    assert desc.iloc[0]["dias"] == 10


def test_agrupar_y_contar():
    df = cargar_dataframe(FILAS)
    resultado = agrupar_y_agregar(df, ["proceso"], None, "contar")
    fila_traslado = resultado[resultado["proceso"] == "Traslado"].iloc[0]
    assert fila_traslado["conteo"] == 2


def test_agrupar_y_promediar():
    df = cargar_dataframe(FILAS)
    resultado = agrupar_y_agregar(df, ["proceso"], "dias", "promedio")
    fila_especialistas = resultado[resultado["proceso"] == "Especialistas"].iloc[0]
    assert fila_especialistas["promedio_dias"] == 6.0  # (10+2)/2


def test_agrupar_fecha_por_mes():
    df = cargar_dataframe(FILAS)
    resultado = agrupar_fecha(df, "fecha_ingreso", "mes")
    assert "fecha_ingreso_mes" in resultado.columns
    assert resultado.iloc[0]["fecha_ingreso_mes"] == "2026-08"


def test_tabla_dinamica_proceso_x_eps_contando():
    df = cargar_dataframe(FILAS)
    pivote = tabla_dinamica(df, filas=["proceso"], columnas=["eps"], valores="dias", funcion="contar")
    assert "proceso" in pivote.columns
    fila_especialistas = pivote[pivote["proceso"] == "Especialistas"].iloc[0]
    assert fila_especialistas["Savia Salud"] == 2