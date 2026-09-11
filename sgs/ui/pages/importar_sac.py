from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgs.ui import theme
from sgs.ui.widgets.indicador_pasos import IndicadorPasos
from sgs.ui.widgets.metric_card import MetricCard

PERIODOS = ["Un día", "Varios días", "Rango de fechas", "Mes completo"]


class ImportarSacPage(QWidget):
    importacion_completada = Signal()

    """
    Flujo: Seleccionar archivo → Validar estructura → Vista previa →
    Clasificar → Detectar duplicados → Mostrar resumen → Confirmar →
    Guardar en PostgreSQL.

    TODO (siguiente iteración): usuario_id real (viene de la sesión,
    hoy placeholder=1 si no se pasa uno).
    """

    def __init__(self, usuario_id: int | None = None):
        super().__init__()
        self._usuario_id = usuario_id or 1
        self._ruta_archivo: str | None = None
        self._resumen = None
        self._vista_previa = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        titulo = QLabel("Importar SAC")
        titulo.setProperty("role", "title")
        layout.addWidget(titulo)

        self.indicador = IndicadorPasos()
        layout.addWidget(self.indicador)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, stretch=1)

        self._pagina_seleccion = self._construir_paso_seleccion()
        self._pagina_validacion = self._construir_paso_validacion()
        self._pagina_vista_previa = self._construir_paso_vista_previa()
        self._pagina_resumen = self._construir_paso_resumen()

        for pagina in (
            self._pagina_seleccion,
            self._pagina_validacion,
            self._pagina_vista_previa,
            self._pagina_resumen,
        ):
            self.stack.addWidget(pagina)

        self._ir_a_paso(0)

    # ------------------------------------------------------------------
    # Paso 1: Seleccionar archivo
    # ------------------------------------------------------------------
    def _construir_paso_seleccion(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setSpacing(14)

        info = QLabel(
            "Selecciona el archivo exportado desde SAC. Puede corresponder a un día, "
            "varios días, un rango de fechas o un mes completo — el nombre del archivo "
            "no se usa como regla, el sistema analiza el contenido."
        )
        info.setWordWrap(True)
        info.setProperty("role", "secondary")
        layout.addWidget(info)

        lbl_periodo = QLabel("Periodo que cubre este exporte (informativo):")
        layout.addWidget(lbl_periodo)

        fila_periodo = QHBoxLayout()
        self.grupo_periodo = QButtonGroup(self)
        for i, periodo in enumerate(PERIODOS):
            radio = QRadioButton(periodo)
            if i == 0:
                radio.setChecked(True)
            self.grupo_periodo.addButton(radio, i)
            fila_periodo.addWidget(radio)
        fila_periodo.addStretch()
        layout.addLayout(fila_periodo)

        fila_archivo = QHBoxLayout()
        self.lbl_archivo_seleccionado = QLabel("Ningún archivo seleccionado.")
        self.lbl_archivo_seleccionado.setProperty("role", "secondary")
        boton_examinar = QPushButton("Examinar…")
        boton_examinar.setProperty("variant", "ghost")
        boton_examinar.clicked.connect(self._elegir_archivo)
        fila_archivo.addWidget(boton_examinar)
        fila_archivo.addWidget(self.lbl_archivo_seleccionado, stretch=1)
        layout.addLayout(fila_archivo)

        layout.addStretch()

        self.lbl_error_seleccion = QLabel("")
        self.lbl_error_seleccion.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
        layout.addWidget(self.lbl_error_seleccion)

        boton_continuar = QPushButton("Validar estructura →")
        boton_continuar.clicked.connect(self._validar_estructura)
        layout.addWidget(boton_continuar, alignment=Qt.AlignmentFlag.AlignRight)
        return pagina

    def _elegir_archivo(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar exporte SAC", "", "Exportes SAC (*.xls *.xlsx)"
        )
        if ruta:
            self._ruta_archivo = ruta
            self.lbl_archivo_seleccionado.setText(ruta.split("/")[-1])

    # ------------------------------------------------------------------
    # Paso 2: Validar estructura (solo tiene pantalla propia visible
    # cuando hay error; si todo está bien, pasa directo a Vista previa)
    # ------------------------------------------------------------------
    def _construir_paso_validacion(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        self.lbl_resultado_validacion = QLabel("")
        self.lbl_resultado_validacion.setWordWrap(True)
        layout.addWidget(self.lbl_resultado_validacion)
        layout.addStretch()

        fila_acciones = QHBoxLayout()
        boton_cancelar = QPushButton("Cancelar")
        boton_cancelar.setProperty("variant", "ghost")
        boton_cancelar.clicked.connect(self._cancelar_validacion)
        fila_acciones.addWidget(boton_cancelar)
        fila_acciones.addStretch()

        boton_volver = QPushButton("← Elegir otro archivo")
        boton_volver.setProperty("variant", "ghost")
        boton_volver.clicked.connect(lambda: self._ir_a_paso(0))
        fila_acciones.addWidget(boton_volver)
        layout.addLayout(fila_acciones)
        return pagina

    def _cancelar_validacion(self) -> None:
        self._ruta_archivo = None
        self._vista_previa = None
        self._resumen = None
        self.lbl_archivo_seleccionado.setText("Ningún archivo seleccionado.")
        self.lbl_error_seleccion.setText("")
        self.lbl_resultado_validacion.setText("")
        self._ir_a_paso(0)

    def _validar_estructura(self) -> None:
        if not self._ruta_archivo:
            self.lbl_error_seleccion.setText("Selecciona un archivo antes de continuar.")
            return
        self.lbl_error_seleccion.setText("")

        try:
            from sgs.app.casos_de_uso import validar_y_previsualizar_archivo_sac

            self._vista_previa = validar_y_previsualizar_archivo_sac(self._ruta_archivo)
        except Exception as exc:
            self._ir_a_paso(1)
            self.lbl_resultado_validacion.setText(f"❌ No se pudo leer el archivo: {exc}")
            self.lbl_resultado_validacion.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
            return

        if self._vista_previa.columnas_faltantes:
            self._ir_a_paso(1)
            faltan = ", ".join(self._vista_previa.columnas_faltantes)
            self.lbl_resultado_validacion.setText(
                f"❌ El archivo no tiene la estructura esperada. Faltan columnas: {faltan}."
            )
            self.lbl_resultado_validacion.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
            return

        self._llenar_vista_previa()
        self._ir_a_paso(2)

    # ------------------------------------------------------------------
    # Paso 3: Vista previa
    # ------------------------------------------------------------------
    def _construir_paso_vista_previa(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setSpacing(10)

        self.lbl_conteo_vista_previa = QLabel("")
        layout.addWidget(self.lbl_conteo_vista_previa)

        self.tabla_vista_previa = QTableWidget()
        self.tabla_vista_previa.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_vista_previa.verticalHeader().setVisible(False)
        layout.addWidget(self.tabla_vista_previa, stretch=1)

        boton_clasificar = QPushButton("Clasificar y detectar duplicados →")
        boton_clasificar.clicked.connect(self._clasificar_y_detectar_duplicados)
        layout.addWidget(boton_clasificar, alignment=Qt.AlignmentFlag.AlignRight)
        return pagina

    def _llenar_vista_previa(self) -> None:
        vp = self._vista_previa
        self.lbl_conteo_vista_previa.setText(
            f"{vp.total_filas} registros encontrados en el archivo. Mostrando los primeros {len(vp.filas_muestra)}."
        )
        columnas_clave = ["numerosolicitud", "fechasolicitud", "motivo", "tipoasuntosol", "solicitud"]
        self.tabla_vista_previa.setColumnCount(len(columnas_clave))
        self.tabla_vista_previa.setHorizontalHeaderLabels(columnas_clave)
        self.tabla_vista_previa.setRowCount(len(vp.filas_muestra))
        for col_idx in range(len(columnas_clave)):
            self.tabla_vista_previa.setColumnWidth(col_idx, 180)
        for fila_idx, fila in enumerate(vp.filas_muestra):
            for col_idx, clave in enumerate(columnas_clave):
                valor = fila.get(clave, "")
                self.tabla_vista_previa.setItem(fila_idx, col_idx, QTableWidgetItem(str(valor)))

    # ------------------------------------------------------------------
    # Paso 4 + 5: Clasificar/duplicados -> Resumen y confirmar
    # ------------------------------------------------------------------
    def _construir_paso_resumen(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setSpacing(14)

        self.grilla_resumen = QGridLayout()
        layout.addLayout(self.grilla_resumen)

        self.lbl_estado_confirmacion = QLabel("")
        self.lbl_estado_confirmacion.setWordWrap(True)
        layout.addWidget(self.lbl_estado_confirmacion)
        self.tabla_por_proceso = QTableWidget()
        self.tabla_por_proceso.setColumnCount(2)
        self.tabla_por_proceso.setHorizontalHeaderLabels(["Proceso", "Registros"])
        self.tabla_por_proceso.setVisible(False)
        layout.addWidget(self.tabla_por_proceso)
        layout.addStretch()

        fila_botones = QHBoxLayout()
        boton_volver = QPushButton("← Volver a la vista previa")
        boton_volver.setProperty("variant", "ghost")
        boton_volver.clicked.connect(lambda: self._ir_a_paso(2))
        fila_botones.addWidget(boton_volver)
        fila_botones.addStretch()

        self.boton_confirmar = QPushButton("Confirmar importación")
        self.boton_confirmar.clicked.connect(self._confirmar_importacion)
        fila_botones.addWidget(self.boton_confirmar)
        self.boton_ir_inicio = QPushButton("Ir al inicio")
        self.boton_ir_inicio.setVisible(False)
        self.boton_ir_inicio.clicked.connect(self.importacion_completada.emit)
        fila_botones.addWidget(self.boton_ir_inicio)
        layout.addLayout(fila_botones)
        return pagina

    def _clasificar_y_detectar_duplicados(self) -> None:
        try:
            from sgs.app.casos_de_uso import clasificar_y_detectar_duplicados

            self._resumen = clasificar_y_detectar_duplicados(self._ruta_archivo)
        except Exception as exc:
            print(f"[importar_sac] error al clasificar: {exc}")  # log técnico para el desarrollador
            self.lbl_estado_confirmacion.setText(
                "❌ No se pudo conectar con la base de datos para clasificar el archivo. Intenta de nuevo."
            )
            self.lbl_estado_confirmacion.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
            self._ir_a_paso(3)
            return

        self._llenar_resumen()
        self._ir_a_paso(3)

    def _llenar_resumen(self) -> None:
        while self.grilla_resumen.count():
            item = self.grilla_resumen.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        r = self._resumen
        tarjetas = [
            MetricCard("Registros nuevos", str(r.nuevos)),
            MetricCard("Actualizados", str(r.actualizados)),
            MetricCard("Sin cambios", str(r.sin_cambios)),
            MetricCard("Errores", str(r.errores), theme.SEMAFORO_ROJO, theme.SEMAFORO_ROJO_BG),
            MetricCard(
                "Sin clasificación", str(r.sin_clasificar), theme.SEMAFORO_AMARILLO, theme.SEMAFORO_AMARILLO_BG
            ),
            MetricCard("Conflictos", str(r.conflictos), theme.SEMAFORO_AMARILLO, theme.SEMAFORO_AMARILLO_BG),
        ]
        for i, tarjeta in enumerate(tarjetas):
            self.grilla_resumen.addWidget(tarjeta, i // 3, i % 3)

        if r.duplicados_archivo or r.duplicados_existentes:
            mensaje = []
            if r.duplicados_archivo:
                mensaje.append(f"Duplicados dentro del archivo: {', '.join(r.duplicados_archivo)}.")
            if r.duplicados_existentes:
                mensaje.append(f"Ya existen en la base de datos: {', '.join(r.duplicados_existentes)}.")
            self.lbl_estado_confirmacion.setText("⚠️ " + " ".join(mensaje) + " No se permite importar mientras existan duplicados.")
            self.lbl_estado_confirmacion.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
            self.boton_confirmar.setEnabled(False)
            self.boton_confirmar.setToolTip("Elimina los duplicados para continuar.")
            return

        self.lbl_estado_confirmacion.setText(
            f"Total procesado: {r.total} registros. Revisa el resumen antes de confirmar — "
            "las filas con error no se guardarán."
        )
        self.lbl_estado_confirmacion.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        self.boton_confirmar.setEnabled(True)
        self.boton_confirmar.setToolTip("")

    def _confirmar_importacion(self) -> None:
        if self._resumen and (self._resumen.duplicados_archivo or self._resumen.duplicados_existentes):
            self.lbl_estado_confirmacion.setText(
                "⚠️ La importación está bloqueada porque existen números de solicitud duplicados. "
                "Corrige esos registros antes de intentar guardar."
            )
            self.lbl_estado_confirmacion.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
            return

        try:
            from sgs.app.casos_de_uso import confirmar_importacion_sac

            nombre_archivo = self._ruta_archivo.split("/")[-1]
            resultado = confirmar_importacion_sac(self._ruta_archivo, nombre_archivo, self._usuario_id)
        except Exception as exc:
            print(f"[importar_sac] error al guardar: {exc}")  # log técnico para el desarrollador
            self.lbl_estado_confirmacion.setText(
                f"❌ No se pudo guardar en la base de datos: {exc}"
            )
            self.lbl_estado_confirmacion.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
            return

        self.lbl_estado_confirmacion.setText(
            f"✅ Importación guardada: {resultado['nuevos']} nuevos, "
            f"{resultado['actualizados']} actualizados, {resultado['sin_cambios']} sin cambios, "
            f"{resultado['errores']} con error, {resultado['sin_clasificar']} sin clasificación."
        )
        self.lbl_estado_confirmacion.setStyleSheet(f"color: {theme.SEMAFORO_VERDE};")
        self.boton_confirmar.setEnabled(False)
        por_proceso = resultado.get("por_proceso", {})
        self.tabla_por_proceso.setRowCount(len(por_proceso))
        for fila_idx, (proceso, total) in enumerate(por_proceso.items()):
            self.tabla_por_proceso.setItem(fila_idx, 0, QTableWidgetItem(proceso))
            self.tabla_por_proceso.setItem(fila_idx, 1, QTableWidgetItem(str(total)))
        self.tabla_por_proceso.setVisible(True)
        self.boton_ir_inicio.setVisible(True)

    # ------------------------------------------------------------------
    def _ir_a_paso(self, indice_stack: int) -> None:
        # el indicador tiene 5 pasos, el stack solo 4 páginas (validación
        # y vista previa comparten avance visual cuando no hay error)
        mapa_indicador = {0: 0, 1: 1, 2: 2, 3: 4}
        self.stack.setCurrentIndex(indice_stack)
        self.indicador.marcar_paso(mapa_indicador.get(indice_stack, 0))