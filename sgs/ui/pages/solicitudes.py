from __future__ import annotations

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
from sgs.ui.columnas_solicitudes import COLUMNAS_DISPONIBLES, configuracion_por_defecto, etiqueta_de
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addLayout(self._barra_superior())

        self.tabla = QTableWidget()
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionsMovable(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
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
        boton_buscar.clicked.connect(self._cargar_datos)
        fila_busqueda.addWidget(boton_buscar)

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
            self._actualizar_boton_filtros()
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
    def _cargar_datos(self) -> None:
        try:
            from sgs.app.casos_de_uso import obtener_solicitudes

            filtros = dict(self._filtros)
            filtros.update({
                "numero": self.campo_numero.text().strip(),
                "documento": self.campo_documento.text().strip(),
                "nombre": self.campo_nombre.text().strip(),
            })
            filas = obtener_solicitudes(filtros, self._usuario_id, self._rol)
            self.lbl_estado.setText("")
        except Exception as exc:
            filas = []
            self.lbl_estado.setText(f"No se pudo consultar la base de datos: {exc}")
        filas = self._filtrar(filas)
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

    def _guardar_estado(self, numero: str, estado: str) -> None:
        try:
            from sgs.app.casos_de_uso import guardar_gestion_solicitud

            guardar_gestion_solicitud(numero, {"estado_gestion": estado})
            self.lbl_estado.setText("Estado de gestión actualizado.")
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
