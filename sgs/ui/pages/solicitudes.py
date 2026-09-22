from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgs.ui import theme
from sgs.ui.columnas_solicitudes import (
    COLUMNAS_DISPONIBLES,
    configuracion_por_defecto,
    etiqueta_de,
    ordenar_filas,
)
from sgs.ui.widgets.dialogo_columnas import DialogoPersonalizarColumnas
from sgs.ui.widgets.dialogo_filtros import DialogoFiltros
from sgs.ui.widgets.semaforo_badge import SemaforoBadge


class SolicitudesPage(QWidget):
    """
    Módulo "Solicitudes" (administrador) / "Mis solicitudes" (funcionario
    — mismo widget, `titulo` cambia y el listado ya viene filtrado por
    proceso/funcionario desde la capa de aplicación).

    IMPORTANTE: nunca hay botón "Nueva solicitud" — las solicitudes
    entran solo por importación SAC (sección 9 / "no debe existir
    botón Nueva solicitud").

    Consulta los datos y la configuración de columnas mediante la capa de
    aplicación; la página no accede directamente al ORM.
    """

    solicitud_seleccionada = Signal(str)  # numero_solicitud_sac

    NOMBRE_PANTALLA = "solicitudes"

    def __init__(self, titulo: str = "Solicitudes", usuario_id: int | None = None, rol: str | None = None):
        super().__init__()
        self._titulo = titulo
        self._usuario_id = usuario_id
        self._rol = rol
        self._config_columnas = self._cargar_configuracion_inicial()
        self._filtros: dict = {}
        # Orden manual por clic en encabezado: None = usar el orden
        # automático que viene de la capa de aplicación; (clave, descendente)
        # = el usuario ordenó manualmente por esa columna.
        self._orden_manual: tuple[str, bool] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addLayout(self._barra_superior())

        self.lbl_contador = QLabel("")
        self.lbl_contador.setProperty("role", "secondary")
        layout.addWidget(self.lbl_contador)

        self.tabla = QTableWidget()
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionsMovable(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Orden manual por clic: lo resolvemos nosotros en Python (el sort
        # nativo de QTableWidget no sirve con celdas-widget como el semáforo
        # o el combo de estado). El indicador de flecha es solo visual.
        self.tabla.horizontalHeader().setSectionsClickable(True)
        self.tabla.horizontalHeader().setSortIndicatorShown(True)
        self.tabla.horizontalHeader().sectionClicked.connect(self._al_click_encabezado)
        layout.addWidget(self.tabla)
        self.lbl_estado = QLabel("")
        self.lbl_estado.setProperty("role", "secondary")
        layout.addWidget(self.lbl_estado)

        self._aplicar_configuracion_columnas()
        self._cargar_datos()

    def _cargar_configuracion_inicial(self) -> list[dict]:
        if self._usuario_id is not None:
            try:
                from sgs.app.casos_de_uso import obtener_configuracion_columnas

                guardada = obtener_configuracion_columnas(self._usuario_id, self.NOMBRE_PANTALLA)
                if guardada:
                    return guardada
            except Exception:
                pass
        return configuracion_por_defecto()

    # ------------------------------------------------------------------
    # Barra superior: búsqueda, filtros, personalizar columnas
    # ------------------------------------------------------------------
    def _barra_superior(self) -> QVBoxLayout:
        contenedor = QVBoxLayout()
        contenedor.setSpacing(10)

        fila_titulo = QHBoxLayout()
        titulo = QLabel(self._titulo)
        titulo.setProperty("role", "title")
        fila_titulo.addWidget(titulo)
        fila_titulo.addStretch()
        contenedor.addLayout(fila_titulo)

        fila_busqueda = QHBoxLayout()
        fila_busqueda.setSpacing(8)

        self.campo_numero = QLineEdit()
        self.campo_numero.setPlaceholderText("N.° de solicitud")
        self.campo_documento = QLineEdit()
        self.campo_documento.setPlaceholderText("Documento")
        self.campo_nombre = QLineEdit()
        self.campo_nombre.setPlaceholderText("Nombre")

        for campo in (self.campo_numero, self.campo_documento, self.campo_nombre):
            campo.setFixedWidth(180)
            campo.returnPressed.connect(self._cargar_datos)
            fila_busqueda.addWidget(campo)

        boton_filtros = QPushButton("Filtros")
        boton_filtros.setProperty("variant", "ghost")
        boton_filtros.clicked.connect(self._abrir_filtros)
        self.boton_filtros = boton_filtros
        fila_busqueda.addWidget(boton_filtros)

        boton_buscar = QPushButton("Buscar")
        boton_buscar.setProperty("variant", "primary")
        boton_buscar.clicked.connect(self._cargar_datos)
        fila_busqueda.addWidget(boton_buscar)

        boton_reasignar = QPushButton("Solicitar reasignación")
        boton_reasignar.setProperty("variant", "ghost")
        boton_reasignar.clicked.connect(self._solicitar_reasignacion)
        fila_busqueda.addWidget(boton_reasignar)

        fila_busqueda.addStretch()

        boton_columnas = QPushButton("⚙️ Personalizar columnas")
        boton_columnas.setProperty("variant", "ghost")
        boton_columnas.clicked.connect(self._abrir_personalizar_columnas)
        fila_busqueda.addWidget(boton_columnas)

        contenedor.addLayout(fila_busqueda)
        return contenedor

    def _abrir_filtros(self) -> None:
        dialogo = DialogoFiltros(self._filtros, parent=self)
        if dialogo.exec():
            self._filtros = dialogo.filtros_resultantes()
            # Cambiar filtros vuelve a la regla de orden automática.
            self._orden_manual = None
            self._actualizar_boton_filtros()
            self._cargar_datos()

    def _fila_seleccionada(self) -> dict | None:
        fila = self.tabla.currentRow()
        filas = getattr(self, "_filas_actuales", [])
        if fila < 0 or fila >= len(filas):
            return None
        return filas[fila]

    def _solicitar_reasignacion(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        from sgs.ui.widgets.dialogo_reasignacion import DialogoReasignacion

        solicitud = self._fila_seleccionada()
        if solicitud is None:
            QMessageBox.information(
                self, "Selecciona una solicitud",
                "Selecciona en la tabla la solicitud que quieres reasignar."
            )
            return

        try:
            from sgs.app.casos_de_uso import listar_procesos

            procesos = [
                p for p in listar_procesos()
                if p["activo"] and p["id"] is not None and p["id"] != solicitud.get("proceso_id")
            ]
        except Exception as exc:
            QMessageBox.critical(self, "No se pudieron cargar los procesos", str(exc))
            return

        if not procesos:
            QMessageBox.information(
                self, "Sin procesos destino",
                "No hay otros procesos activos a los que reasignar esta solicitud."
            )
            return

        dialogo = DialogoReasignacion(
            solicitud["numero_solicitud_sac"], solicitud.get("proceso", "Sin proceso"), procesos, parent=self
        )
        if not dialogo.exec():
            return

        confirmar = QMessageBox.question(
            self,
            "Confirmar solicitud de reasignación",
            f"¿Enviar la solicitud de reasignación de {solicitud['numero_solicitud_sac']} "
            f"hacia «{dialogo.proceso_destino_nombre()}»?\n\n"
            "Un administrador deberá aprobarla.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmar != QMessageBox.StandardButton.Yes:
            return

        try:
            from sgs.app.casos_de_uso import solicitar_reasignacion_proceso

            solicitar_reasignacion_proceso(
                solicitud["numero_solicitud_sac"],
                dialogo.proceso_destino_id(),
                dialogo.motivo(),
                self._usuario_id,
            )
            QMessageBox.information(
                self, "Solicitud enviada",
                "La solicitud de reasignación fue enviada. Un administrador la revisará."
            )
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo enviar", str(exc))

    # ------------------------------------------------------------------
    # Orden manual por clic en el encabezado
    # ------------------------------------------------------------------
    def _al_click_encabezado(self, indice_columna: int) -> None:
        """Ordena por la columna clicada. Alterna asc/desc en clics
        sucesivos sobre la misma columna. La última columna (acción
        'Detalle') no ordena."""
        columnas = getattr(self, "_columnas_visibles_actuales", [])
        if indice_columna < 0 or indice_columna >= len(columnas):
            return  # columna de acción "Detalle" o índice fuera de rango
        clave = columnas[indice_columna]["clave"]
        if self._orden_manual and self._orden_manual[0] == clave:
            descendente = not self._orden_manual[1]
        else:
            descendente = False
        self._orden_manual = (clave, descendente)
        orden_qt = Qt.SortOrder.DescendingOrder if descendente else Qt.SortOrder.AscendingOrder
        self.tabla.horizontalHeader().setSortIndicator(indice_columna, orden_qt)
        self._cargar_datos()

    def _actualizar_boton_filtros(self) -> None:
        activos = sum(
            1
            for clave in ("proceso", "estado_gestion", "semaforo")
            if self._filtros.get(clave, "Todos") != "Todos"
        )
        self.boton_filtros.setText(f"Filtros ({activos})" if activos else "Filtros")

    # ------------------------------------------------------------------
    # Personalización de columnas
    # ------------------------------------------------------------------
    def _abrir_personalizar_columnas(self) -> None:
        dialogo = DialogoPersonalizarColumnas(self._config_columnas, parent=self)
        if dialogo.exec():
            self._config_columnas = dialogo.configuracion_resultante()
            # Cambiar el conjunto/orden de columnas invalida el índice del
            # orden manual: se vuelve a la regla de orden automática.
            self._orden_manual = None
            self._aplicar_configuracion_columnas()
            self._cargar_datos()
            self._guardar_configuracion_columnas()

    def _guardar_configuracion_columnas(self) -> None:
        if self._usuario_id is None:
            return
        try:
            from sgs.app.casos_de_uso import guardar_configuracion_columnas

            guardar_configuracion_columnas(self._usuario_id, self.NOMBRE_PANTALLA, self._config_columnas)
        except Exception:
            pass

    def _aplicar_configuracion_columnas(self) -> None:
        columnas_visibles = [c for c in self._config_columnas if c["visible"]]
        
        # Limpiar celdas anteriores para evitar residuos visuales
        self.tabla.clearContents()
        self.tabla.setRowCount(0)
        
        self.tabla.setColumnCount(len(columnas_visibles) + 1)  # +1 columna de acción "Detalle"

        etiquetas = [etiqueta_de(c["clave"]) for c in columnas_visibles] + [""]
        self.tabla.setHorizontalHeaderLabels(etiquetas)
        
        # Evitar reordenamiento durante la reconfiguración
        header = self.tabla.horizontalHeader()
        header.setSectionsMovable(False)

        for i, col in enumerate(columnas_visibles):
            self.tabla.setColumnWidth(i, col["ancho"])
        self.tabla.setColumnWidth(len(columnas_visibles), 110)

        self._columnas_visibles_actuales = columnas_visibles
        
        # Reactivar reordenamiento manual
        header.setSectionsMovable(True)

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------
    def al_mostrar(self) -> None:
        """Invocado por MainWindow cada vez que la página vuelve a
        mostrarse — se restaura SIEMPRE la vista predeterminada (mes en
        curso, sin completadas) aunque hubiera búsquedas o filtros de una
        visita anterior."""
        self._filtros = {}
        self._orden_manual = None
        self.tabla.horizontalHeader().setSortIndicatorShown(True)
        for campo in (self.campo_numero, self.campo_documento, self.campo_nombre):
            campo.clear()
        self._actualizar_boton_filtros()
        self._cargar_datos()

    def _filtros_para_consulta(self) -> dict:
        """Filtros listos para enviar a la capa de aplicación: los
        rangos de fecha (QDate del diálogo) se normalizan a ISO."""
        filtros = dict(self._filtros)
        for clave in ("fecha_desde", "fecha_hasta"):
            valor = filtros.get(clave)
            if valor is not None:
                filtros[clave] = valor.toString("yyyy-MM-dd") if hasattr(valor, "toString") else str(valor)
        filtros.update({
            "numero": self.campo_numero.text().strip(),
            "documento": self.campo_documento.text().strip(),
            "nombre": self.campo_nombre.text().strip(),
        })
        if not self._hay_criterios_activos():
            # Vista por defecto del módulo: SOLO el mes actual y sin las
            # completadas (no se borran — quedan ocultas). Rendimiento:
            # cada vez que se entra se consultan pocas filas, y el flag se
            # respeta igual en el contador.
            hoy = dt.date.today()
            filtros["fecha_desde"] = dt.date(hoy.year, hoy.month, 1)
            filtros["fecha_hasta"] = hoy
            filtros["excluir_completadas"] = True
        return filtros

    def _hay_criterios_activos(self) -> bool:
        """True si hay CUALQUIER búsqueda o filtro aplicado. Por defecto el
        módulo solo muestra las solicitudes NO completadas (las completadas
        no se borran: quedan ocultas para no frenar la consulta). Si el
        usuario activa cualquier criterio, se incluyen también ellas."""
        if (
            self.campo_numero.text().strip()
            or self.campo_documento.text().strip()
            or self.campo_nombre.text().strip()
        ):
            return True
        if self._filtros.get("proceso", "Todos") != "Todos":
            return True
        if self._filtros.get("estado_gestion", "Todos") != "Todos":
            return True
        if self._filtros.get("semaforo", "Todos") != "Todos":
            return True
        if self._filtros.get("fecha_desde") or self._filtros.get("fecha_hasta"):
            return True
        return False

    def _actualizar_contador(self, total: int) -> None:
        hay_criterios = bool(
            self.campo_numero.text().strip()
            or self.campo_documento.text().strip()
            or self.campo_nombre.text().strip()
            or self._filtros
        )
        if hay_criterios:
            self.lbl_contador.setText(f"Solicitudes encontradas: {total}")
        else:
            self.lbl_contador.setText(
                f"Total de solicitudes en gestión: {total} "
                "(las completadas no se muestran por defecto; usa un filtro para verlas)"
            )

    def _cargar_datos(self) -> None:
        try:
            from sgs.app.casos_de_uso import contar_solicitudes, obtener_solicitudes

            filtros = self._filtros_para_consulta()
            filas = obtener_solicitudes(
                filtros, self._usuario_id, self._rol, hay_criterios=self._hay_criterios_activos()
            )
            self.lbl_estado.setText("")
        except Exception as exc:
            filas = []
            self.lbl_estado.setText(f"No se pudo consultar la base de datos: {exc}")
        filas = self._filtrar(filas)
        filas = self._aplicar_orden_manual(filas)

        try:
            contador = contar_solicitudes(self._filtros_para_consulta(), self._usuario_id, self._rol)
        except Exception:
            contador = len(filas)
        if self._filtros.get("semaforo", "Todos") != "Todos":
            contador = len(filas)
        self._actualizar_contador(contador)
        self._filas_actuales = filas
        self.tabla.setRowCount(len(filas))

        for fila_idx, solicitud in enumerate(filas):
            for col_idx, col in enumerate(self._columnas_visibles_actuales):
                valor = solicitud.get(col["clave"], "")
                if col["clave"] == "semaforo":
                    self.tabla.setCellWidget(fila_idx, col_idx, SemaforoBadge(valor))
                elif col["clave"] == "estado_gestion":
                    combo = QComboBox()
                    combo.addItems(["En trámite", "Solucionada"])
                    if valor and combo.findText(valor) < 0:
                        combo.addItem(str(valor))
                    combo.setCurrentText(str(valor))
                    combo.currentTextChanged.connect(
                        lambda estado, n=solicitud["numero_solicitud_sac"]: self._guardar_estado(n, estado)
                    )
                    self.tabla.setCellWidget(fila_idx, col_idx, combo)
                else:
                    self.tabla.setItem(fila_idx, col_idx, QTableWidgetItem(str(valor)))

            boton_detalle = QPushButton("Detalle →")
            boton_detalle.setProperty("variant", "ghost")
            numero = solicitud["numero_solicitud_sac"]
            boton_detalle.clicked.connect(lambda checked, n=numero: self.solicitud_seleccionada.emit(n))
            self.tabla.setCellWidget(fila_idx, len(self._columnas_visibles_actuales), boton_detalle)

    def _aplicar_orden_manual(self, filas: list[dict]) -> list[dict]:
        """Si el usuario ordenó por clic, reordena aquí (en Python) y
        sincroniza el indicador de flecha con la columna visible. Si no hay
        orden manual, respeta el orden automático que trae la capa de
        aplicación y oculta el indicador."""
        header = self.tabla.horizontalHeader()
        if not self._orden_manual:
            header.setSortIndicatorShown(False)
            return filas
        clave, descendente = self._orden_manual
        columnas = getattr(self, "_columnas_visibles_actuales", [])
        indice = next((i for i, c in enumerate(columnas) if c["clave"] == clave), None)
        if indice is None:
            # La columna ordenada ya no está visible: se descarta el orden
            # manual y se vuelve al automático.
            self._orden_manual = None
            header.setSortIndicatorShown(False)
            return filas
        header.setSortIndicatorShown(True)
        header.setSortIndicator(
            indice,
            Qt.SortOrder.DescendingOrder if descendente else Qt.SortOrder.AscendingOrder,
        )
        return ordenar_filas(filas, clave, descendente)

    def _guardar_estado(self, numero: str, estado: str) -> None:
        try:
            from sgs.app.casos_de_uso import guardar_gestion_solicitud

            guardar_gestion_solicitud(numero, {"estado_gestion": estado})
            self.lbl_estado.setText("Estado de gestión actualizado.")
            self._cargar_datos()
        except Exception as exc:
            self.lbl_estado.setText(f"No se pudo actualizar el estado: {exc}")

    def _filtrar(self, datos: list[dict]) -> list[dict]:
        numero = self.campo_numero.text().strip().lower()
        documento = self.campo_documento.text().strip().lower()
        nombre = self.campo_nombre.text().strip().lower()

        proceso = self._filtros.get("proceso", "Todos")
        estado = self._filtros.get("estado_gestion", "Todos")
        semaforo = self._filtros.get("semaforo", "Todos")
        fecha_desde = self._filtros.get("fecha_desde")
        fecha_hasta = self._filtros.get("fecha_hasta")

        def coincide(s: dict) -> bool:
            if numero and numero not in s["numero_solicitud_sac"].lower():
                return False
            if documento and documento not in s["documento"].lower():
                return False
            if nombre and nombre not in s["nombre_ciudadano"].lower():
                return False
            if proceso != "Todos" and s["proceso"] != proceso:
                return False
            if estado != "Todos" and s["estado_gestion"] != estado:
                return False
            if semaforo != "Todos" and s["semaforo"] != semaforo:
                return False
            if fecha_desde and s["fecha_ingreso"] < fecha_desde.toString("yyyy-MM-dd"):
                return False
            if fecha_hasta and s["fecha_ingreso"] > fecha_hasta.toString("yyyy-MM-dd"):
                return False
            return True

        return [s for s in datos if coincide(s)]
