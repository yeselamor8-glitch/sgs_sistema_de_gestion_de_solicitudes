from __future__ import annotations

from PySide6.QtCore import Qt
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

COLUMNAS = ["Usuario", "Acción", "Entidad", "Solicitud", "Valor anterior", "Valor nuevo", "Fecha/hora"]
CLAVES = ["usuario", "accion", "entidad", "solicitud", "valor_anterior", "valor_nuevo", "fecha"]


class AuditoriaPage(QWidget):
    """Pantalla de solo consulta de la bitácora de acciones importantes.
    No permite edición: solo listar y filtrar."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        titulo = QLabel("Auditoría")
        titulo.setProperty("role", "title")
        layout.addWidget(titulo)

        subtitulo = QLabel("Registro de acciones importantes del sistema (solo consulta).")
        subtitulo.setProperty("role", "secondary")
        layout.addWidget(subtitulo)

        # Barra de filtros
        fila = QHBoxLayout()
        fila.setSpacing(8)

        self.combo_entidad = QComboBox()
        self.combo_entidad.addItem("Todas las entidades", None)
        fila.addWidget(self.combo_entidad)

        self.campo_accion = QLineEdit()
        self.campo_accion.setPlaceholderText("Acción contiene…")
        self.campo_accion.setFixedWidth(220)
        self.campo_accion.returnPressed.connect(self._cargar)
        fila.addWidget(self.campo_accion)

        boton_buscar = QPushButton("Buscar")
        boton_buscar.setProperty("variant", "primary")
        boton_buscar.clicked.connect(self._cargar)
        fila.addWidget(boton_buscar)

        boton_limpiar = QPushButton("Limpiar")
        boton_limpiar.setProperty("variant", "ghost")
        boton_limpiar.clicked.connect(self._limpiar)
        fila.addWidget(boton_limpiar)

        fila.addStretch()
        layout.addLayout(fila)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tabla)

        self.lbl_estado = QLabel("")
        self.lbl_estado.setProperty("role", "secondary")
        layout.addWidget(self.lbl_estado)

        self._cargar_entidades()
        self._cargar()

    def al_mostrar(self) -> None:
        self._cargar_entidades()
        self._cargar()

    def _cargar_entidades(self) -> None:
        actual = self.combo_entidad.currentData()
        try:
            from sgs.app.casos_de_uso import listar_entidades_auditoria

            entidades = listar_entidades_auditoria()
        except Exception:
            entidades = []
        self.combo_entidad.blockSignals(True)
        self.combo_entidad.clear()
        self.combo_entidad.addItem("Todas las entidades", None)
        for e in entidades:
            self.combo_entidad.addItem(e, e)
        idx = self.combo_entidad.findData(actual)
        if idx >= 0:
            self.combo_entidad.setCurrentIndex(idx)
        self.combo_entidad.blockSignals(False)

    def _limpiar(self) -> None:
        self.combo_entidad.setCurrentIndex(0)
        self.campo_accion.clear()
        self._cargar()

    def _cargar(self) -> None:
        filtros = {}
        if self.combo_entidad.currentData():
            filtros["entidad"] = self.combo_entidad.currentData()
        if self.campo_accion.text().strip():
            filtros["accion"] = self.campo_accion.text().strip()

        try:
            from sgs.app.casos_de_uso import listar_auditoria

            filas = listar_auditoria(filtros)
            self.lbl_estado.setText("")
        except Exception as exc:
            filas = []
            self.lbl_estado.setText(f"No se pudo consultar la auditoría: {exc}")

        self.tabla.setRowCount(len(filas))
        for i, fila in enumerate(filas):
            for j, clave in enumerate(CLAVES):
                item = QTableWidgetItem(str(fila.get(clave, "")))
                self.tabla.setItem(i, j, item)

        if not filas and not self.lbl_estado.text():
            self.lbl_estado.setText("No hay registros de auditoría para los filtros actuales.")
        elif filas:
            self.lbl_estado.setText(f"{len(filas)} registros.")
