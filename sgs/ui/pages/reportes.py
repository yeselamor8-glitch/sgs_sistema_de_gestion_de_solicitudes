from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgs.ui import theme
from sgs.ui.widgets.dialogo_columnas_analisis import DialogoColumnasAnalisis
from sgs.ui.widgets.section_card import SectionCard

FUNCIONES = [("Contar", "contar"), ("Sumar", "sumar"), ("Promedio", "promedio"), ("Mínimo", "minimo"), ("Máximo", "maximo")]
UNIDADES_FECHA = [("Día", "dia"), ("Semana", "semana"), ("Mes", "mes"), ("Año", "año")]


def _numeric_seguro(serie):
    import pandas as pd

    return pd.to_numeric(serie, errors="coerce").fillna(0)


class ReportesPage(QWidget):
    """
    Herramienta de análisis moldeable (sección 23/28-31 del documento
    funcional): trabaja sobre datos del sistema o sobre un archivo SAC
    cargado temporalmente (sin importarlo a la base operativa) — misma
    UI y mismo motor para ambos casos.

    TODO (siguiente iteración): reemplazar `_datos_ejemplo_sistema()`
    por un caso de uso real `casos_de_uso.obtener_solicitudes_para_analisis(...)`.
    """

    def __init__(self):
        super().__init__()
        self._df_original = None
        self._df_resultado = None
        self._columnas_visibles: list[str] = []

        contenedor = QScrollArea()
        contenedor.setWidgetResizable(True)
        cuerpo = QWidget()
        layout = QVBoxLayout(cuerpo)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        titulo = QLabel("Reportes y análisis")
        titulo.setProperty("role", "title")
        layout.addWidget(titulo)

        layout.addWidget(self._seccion_fuente())
        layout.addWidget(self._seccion_filtros())
        layout.addWidget(self._seccion_agrupar())
        layout.addWidget(self._seccion_tabla_dinamica())
        layout.addWidget(self._seccion_resultado())

        contenedor.setWidget(cuerpo)
        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.addWidget(contenedor)

    # ------------------------------------------------------------------
    def _seccion_fuente(self) -> SectionCard:
        card = SectionCard("Fuente de datos", columnas=1)
        fila = QHBoxLayout()

        self.radio_sistema = QRadioButton("Datos del sistema")
        self.radio_archivo = QRadioButton("Archivo SAC temporal (no se importa)")
        self.radio_sistema.setChecked(True)
        fila.addWidget(self.radio_sistema)
        fila.addWidget(self.radio_archivo)

        boton_cargar = QPushButton("Cargar")
        boton_cargar.clicked.connect(self._cargar_fuente)
        fila.addWidget(boton_cargar)

        self.lbl_fuente_estado = QLabel("Sin datos cargados.")
        self.lbl_fuente_estado.setProperty("role", "secondary")
        fila.addWidget(self.lbl_fuente_estado)
        fila.addStretch()

        widget = QWidget()
        widget.setLayout(fila)
        card.agregar_widget_ancho_completo(widget)
        return card

    def _cargar_fuente(self) -> None:
        from sgs.motores.motor_analisis import cargar_dataframe

        if self.radio_archivo.isChecked():
            ruta, _ = QFileDialog.getOpenFileName(self, "Cargar archivo SAC", "", "Exportes SAC (*.xls *.xlsx)")
            if not ruta:
                return
            try:
                from sgs.motores.lector_archivo_sac import leer_archivo_sac

                archivo = leer_archivo_sac(ruta)
                self._df_original = cargar_dataframe(archivo.filas)
                self.lbl_fuente_estado.setText(f"{len(archivo.filas)} filas cargadas de {ruta.split('/')[-1]}.")
            except Exception as exc:
                self.lbl_fuente_estado.setText(f"❌ No se pudo leer el archivo: {exc}")
                return
        else:
            filas = self._datos_ejemplo_sistema()
            self._df_original = cargar_dataframe(filas)
            self.lbl_fuente_estado.setText(f"{len(filas)} solicitudes cargadas del sistema.")

        self._columnas_visibles = list(self._df_original.columns)
        self._actualizar_listas_columnas()
        self._df_resultado = self._df_original
        self._refrescar_tabla_resultado()

    # ------------------------------------------------------------------
    def _seccion_filtros(self) -> SectionCard:
        card = SectionCard("Filtrar", columnas=1)
        fila = QHBoxLayout()

        self.combo_filtro_columna = QComboBox()
        self.combo_filtro_operador = QComboBox()
        self.combo_filtro_operador.addItems(["igual_a", "distinto_de", "contiene", "mayor_que", "menor_que"])
        self.campo_filtro_valor = QLineEdit()
        self.campo_filtro_valor.setPlaceholderText("Valor")

        boton_aplicar = QPushButton("Filtrar")
        boton_aplicar.clicked.connect(self._aplicar_filtro)
        boton_columnas = QPushButton("⚙️ Seleccionar columnas")
        boton_columnas.setProperty("variant", "ghost")
        boton_columnas.clicked.connect(self._abrir_seleccion_columnas)

        fila.addWidget(self.combo_filtro_columna)
        fila.addWidget(self.combo_filtro_operador)
        fila.addWidget(self.campo_filtro_valor)
        fila.addWidget(boton_aplicar)
        fila.addStretch()
        fila.addWidget(boton_columnas)

        widget = QWidget()
        widget.setLayout(fila)
        card.agregar_widget_ancho_completo(widget)
        return card

    def _abrir_seleccion_columnas(self) -> None:
        if self._df_original is None:
            return
        dialogo = DialogoColumnasAnalisis(list(self._df_original.columns), self._columnas_visibles, parent=self)
        if dialogo.exec():
            self._columnas_visibles = dialogo.columnas_seleccionadas()
            self._refrescar_tabla_resultado()

    def _aplicar_filtro(self) -> None:
        if self._df_original is None:
            return
        from sgs.motores.motor_analisis import Filtro, aplicar_filtros

        columna = self.combo_filtro_columna.currentText()
        valor = self.campo_filtro_valor.text().strip()
        base = self._df_original
        if columna and valor:
            filtro = Filtro(columna, self.combo_filtro_operador.currentText(), valor)
            base = aplicar_filtros(base, [filtro])
        self._df_resultado = base
        self._refrescar_tabla_resultado()

    # ------------------------------------------------------------------
    def _seccion_agrupar(self) -> SectionCard:
        card = SectionCard("Agrupar", columnas=1)
        fila = QHBoxLayout()

        self.lista_agrupar_por = QListWidget()
        self.lista_agrupar_por.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.lista_agrupar_por.setFixedHeight(70)
        fila.addWidget(self.lista_agrupar_por)

        self.combo_agrupar_unidad_fecha = QComboBox()
        self.combo_agrupar_unidad_fecha.addItem("(sin agrupar fecha)", None)
        for etiqueta, valor in UNIDADES_FECHA:
            self.combo_agrupar_unidad_fecha.addItem(etiqueta, valor)
        fila.addWidget(self.combo_agrupar_unidad_fecha)

        self.combo_agrupar_valor = QComboBox()
        fila.addWidget(self.combo_agrupar_valor)

        self.combo_agrupar_funcion = QComboBox()
        for etiqueta, valor in FUNCIONES:
            self.combo_agrupar_funcion.addItem(etiqueta, valor)
        fila.addWidget(self.combo_agrupar_funcion)

        boton_agrupar = QPushButton("Agrupar")
        boton_agrupar.clicked.connect(self._aplicar_agrupacion)
        fila.addWidget(boton_agrupar)

        widget = QWidget()
        widget.setLayout(fila)
        card.agregar_widget_ancho_completo(widget)
        return card

    def _aplicar_agrupacion(self) -> None:
        if self._df_original is None:
            return
        from sgs.motores.motor_analisis import agrupar_fecha, agrupar_y_agregar

        df = self._df_original
        columnas_agrupar = [item.text() for item in self.lista_agrupar_por.selectedItems()]

        unidad = self.combo_agrupar_unidad_fecha.currentData()
        if unidad and columnas_agrupar:
            columna_fecha = columnas_agrupar[0]
            df = agrupar_fecha(df, columna_fecha, unidad)
            columnas_agrupar = [f"{columna_fecha}_{unidad}"] + columnas_agrupar[1:]

        columna_valor = self.combo_agrupar_valor.currentText() or None
        funcion = self.combo_agrupar_funcion.currentData()

        if not columnas_agrupar:
            return
        self._df_resultado = agrupar_y_agregar(df, columnas_agrupar, columna_valor, funcion)
        self._columnas_visibles = list(self._df_resultado.columns)
        self._refrescar_tabla_resultado()

    # ------------------------------------------------------------------
    def _seccion_tabla_dinamica(self) -> SectionCard:
        card = SectionCard("Tabla dinámica", columnas=1)
        fila = QHBoxLayout()

        self.lista_pivote_filas = QListWidget()
        self.lista_pivote_filas.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.lista_pivote_filas.setFixedHeight(70)
        fila.addWidget(QLabel("Filas:"))
        fila.addWidget(self.lista_pivote_filas)

        self.lista_pivote_columnas = QListWidget()
        self.lista_pivote_columnas.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.lista_pivote_columnas.setFixedHeight(70)
        fila.addWidget(QLabel("Columnas:"))
        fila.addWidget(self.lista_pivote_columnas)

        self.combo_pivote_valores = QComboBox()
        self.combo_pivote_funcion = QComboBox()
        for etiqueta, valor in FUNCIONES:
            self.combo_pivote_funcion.addItem(etiqueta, valor)
        fila.addWidget(QLabel("Valores:"))
        fila.addWidget(self.combo_pivote_valores)
        fila.addWidget(self.combo_pivote_funcion)

        boton_generar = QPushButton("Generar tabla dinámica")
        boton_generar.clicked.connect(self._generar_tabla_dinamica)
        fila.addWidget(boton_generar)

        widget = QWidget()
        widget.setLayout(fila)
        card.agregar_widget_ancho_completo(widget)
        return card

    def _generar_tabla_dinamica(self) -> None:
        if self._df_original is None:
            return
        from sgs.motores.motor_analisis import tabla_dinamica

        filas = [item.text() for item in self.lista_pivote_filas.selectedItems()]
        columnas = [item.text() for item in self.lista_pivote_columnas.selectedItems()]
        valores = self.combo_pivote_valores.currentText()
        funcion = self.combo_pivote_funcion.currentData()

        if not filas:
            return
        self._df_resultado = tabla_dinamica(self._df_original, filas, columnas, valores, funcion)
        self._columnas_visibles = list(self._df_resultado.columns)
        self._refrescar_tabla_resultado()

    # ------------------------------------------------------------------
    def _seccion_resultado(self) -> SectionCard:
        card = SectionCard("Resultado", columnas=1)

        fila_botones = QHBoxLayout()
        self.lbl_conteo_resultado = QLabel("")
        self.lbl_conteo_resultado.setProperty("role", "secondary")
        fila_botones.addWidget(self.lbl_conteo_resultado)
        fila_botones.addStretch()

        boton_grafico = QPushButton("📊 Ver gráfico")
        boton_grafico.setProperty("variant", "ghost")
        boton_grafico.clicked.connect(self._mostrar_grafico)
        fila_botones.addWidget(boton_grafico)

        boton_exportar = QPushButton("Exportar a Excel")
        boton_exportar.clicked.connect(self._exportar_excel)
        fila_botones.addWidget(boton_exportar)

        widget_botones = QWidget()
        widget_botones.setLayout(fila_botones)
        card.agregar_widget_ancho_completo(widget_botones)

        self.tabla_resultado = QTableWidget()
        self.tabla_resultado.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_resultado.verticalHeader().setVisible(False)
        self.tabla_resultado.setMinimumHeight(280)
        card.agregar_widget_ancho_completo(self.tabla_resultado)

        self.lbl_error_resultado = QLabel("")
        self.lbl_error_resultado.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
        card.agregar_widget_ancho_completo(self.lbl_error_resultado)
        return card

    def _actualizar_listas_columnas(self) -> None:
        columnas = list(self._df_original.columns) if self._df_original is not None else []
        for combo in (self.combo_filtro_columna, self.combo_agrupar_valor, self.combo_pivote_valores):
            combo.clear()
            combo.addItems(columnas)
        for lista in (self.lista_agrupar_por, self.lista_pivote_filas, self.lista_pivote_columnas):
            lista.clear()
            for col in columnas:
                lista.addItem(QListWidgetItem(col))

    def _refrescar_tabla_resultado(self) -> None:
        if self._df_resultado is None:
            return
        df = self._df_resultado
        columnas_a_mostrar = [c for c in self._columnas_visibles if c in df.columns] or list(df.columns)
        df_mostrar = df[columnas_a_mostrar]

        self.tabla_resultado.setColumnCount(len(columnas_a_mostrar))
        self.tabla_resultado.setHorizontalHeaderLabels([str(c) for c in columnas_a_mostrar])
        self.tabla_resultado.setRowCount(min(len(df_mostrar), 500))
        for fila_idx, (_, fila) in enumerate(df_mostrar.head(500).iterrows()):
            for col_idx, valor in enumerate(fila):
                self.tabla_resultado.setItem(fila_idx, col_idx, QTableWidgetItem(str(valor)))

        self.lbl_conteo_resultado.setText(
            f"{len(df)} filas" + (" (mostrando las primeras 500)" if len(df) > 500 else "")
        )

    def _mostrar_grafico(self) -> None:
        if self._df_resultado is None or self._df_resultado.empty:
            return
        try:
            self._abrir_ventana_grafico()
        except Exception as exc:
            self.lbl_error_resultado.setText(f"No se pudo generar el gráfico: {exc}")

    def _abrir_ventana_grafico(self) -> None:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        from PySide6.QtWidgets import QDialog, QVBoxLayout as _QV

        df = self._df_resultado
        columnas_a_mostrar = [c for c in self._columnas_visibles if c in df.columns] or list(df.columns)
        if len(columnas_a_mostrar) < 2:
            self.lbl_error_resultado.setText("Se necesitan al menos 2 columnas en el resultado para graficar.")
            return

        categorias = df[columnas_a_mostrar[0]].astype(str).head(30)
        valores = _numeric_seguro(df[columnas_a_mostrar[1]]).head(30)

        dialogo = QDialog(self)
        dialogo.setWindowTitle("Gráfico")
        dialogo.resize(700, 450)
        dialogo.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        layout = _QV(dialogo)

        figura = Figure(figsize=(6, 4))
        eje = figura.add_subplot(111)
        eje.bar(categorias, valores, color=theme.ACCENT)
        eje.tick_params(axis="x", rotation=45, labelsize=8)
        figura.tight_layout()

        canvas = FigureCanvasQTAgg(figura)
        layout.addWidget(canvas)
        self._ventana_grafico = dialogo  # mantener referencia viva
        dialogo.show()

    def _exportar_excel(self) -> None:
        if self._df_resultado is None:
            return
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar a Excel", "analisis.xlsx", "Excel (*.xlsx)")
        if not ruta:
            return
        try:
            from sgs.motores.motor_analisis import exportar_excel

            columnas_a_mostrar = [c for c in self._columnas_visibles if c in self._df_resultado.columns]
            df_exportar = self._df_resultado[columnas_a_mostrar] if columnas_a_mostrar else self._df_resultado
            exportar_excel(df_exportar, ruta)
            self.lbl_error_resultado.setStyleSheet(f"color: {theme.SEMAFORO_VERDE};")
            self.lbl_error_resultado.setText(f"✅ Exportado a {ruta}")
        except Exception as exc:
            self.lbl_error_resultado.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
            self.lbl_error_resultado.setText(f"No se pudo exportar: {exc}")

    # ------------------------------------------------------------------
    @staticmethod
    def _datos_ejemplo_sistema() -> list[dict]:
        # Placeholder — se reemplaza por casos_de_uso.obtener_solicitudes_para_analisis(...)
        return [
            {"numero_solicitud_sac": "SAC-004821", "proceso": "Traslado", "eps": "Savia Salud", "estado_gestion": "En trámite", "fecha_ingreso": "2026-08-05", "dias_respuesta": 5},
            {"numero_solicitud_sac": "SAC-004822", "proceso": "Traslado", "eps": "Suramericana", "estado_gestion": "Solucionada", "fecha_ingreso": "2026-08-20", "dias_respuesta": 3},
            {"numero_solicitud_sac": "SAC-004902", "proceso": "Especialistas", "eps": "Savia Salud", "estado_gestion": "En trámite", "fecha_ingreso": "2026-09-01", "dias_respuesta": 10},
            {"numero_solicitud_sac": "SAC-004917", "proceso": "Urgentes y prioritarios", "eps": "Suramericana", "estado_gestion": "En trámite", "fecha_ingreso": "2026-09-02", "dias_respuesta": 2},
            {"numero_solicitud_sac": "SAC-004930", "proceso": "Acceso a los servicios de salud", "eps": "Savia Salud", "estado_gestion": "Solucionada", "fecha_ingreso": "2026-09-02", "dias_respuesta": 6},
        ]