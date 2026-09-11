from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from sgs.ui import theme
from sgs.ui.columnas_solicitudes import configuracion_por_defecto, etiqueta_de


class DialogoPersonalizarColumnas(QDialog):
    """
    Controla visibilidad, orden y ancho de columna. Recibe la
    configuración actual ([{clave, visible, ancho}], en el orden
    actual) y expone `configuracion_resultante()` tras aceptar.
    """

    COL_VISIBLE, COL_NOMBRE, COL_ANCHO = range(3)

    def __init__(self, configuracion_actual: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Personalizar columnas")
        self.resize(380, 460)
        self._configuracion = [dict(c) for c in configuracion_actual]

        layout = QVBoxLayout(self)

        info = QLabel("Marca las columnas visibles, ajusta el ancho y usa las flechas para reordenarlas.")
        info.setProperty("role", "secondary")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["", "Columna", "Ancho (px)"])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.horizontalHeader().setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch)
        self.tabla.setStyleSheet(f"QTableWidget {{ border: 1px solid {theme.BORDER}; border-radius: 8px; }}")
        self._poblar_tabla()
        layout.addWidget(self.tabla)

        fila_mover = QHBoxLayout()
        boton_subir = QPushButton("↑ Subir")
        boton_bajar = QPushButton("↓ Bajar")
        boton_subir.setProperty("variant", "ghost")
        boton_bajar.setProperty("variant", "ghost")
        boton_subir.clicked.connect(lambda: self._mover(-1))
        boton_bajar.clicked.connect(lambda: self._mover(1))
        fila_mover.addWidget(boton_subir)
        fila_mover.addWidget(boton_bajar)
        layout.addLayout(fila_mover)

        boton_restablecer = QPushButton("Restablecer vista predeterminada")
        boton_restablecer.setProperty("variant", "ghost")
        boton_restablecer.clicked.connect(self._restablecer)
        layout.addWidget(boton_restablecer)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _poblar_tabla(self) -> None:
        self.tabla.setRowCount(len(self._configuracion))
        for fila, col in enumerate(self._configuracion):
            check = QCheckBox()
            check.setChecked(col["visible"])
            contenedor = QHBoxLayout()
            contenedor.setContentsMargins(10, 0, 0, 0)
            contenedor.addWidget(check)
            widget_check = self._envolver(contenedor)
            self.tabla.setCellWidget(fila, self.COL_VISIBLE, widget_check)

            self.tabla.setItem(fila, self.COL_NOMBRE, QTableWidgetItem(etiqueta_de(col["clave"])))

            spin = QSpinBox()
            spin.setRange(50, 400)
            spin.setValue(col["ancho"])
            self.tabla.setCellWidget(fila, self.COL_ANCHO, spin)

        self.tabla.setColumnWidth(self.COL_VISIBLE, 40)
        self.tabla.setColumnWidth(self.COL_ANCHO, 100)

    @staticmethod
    def _envolver(layout: QHBoxLayout):
        from PySide6.QtWidgets import QWidget

        w = QWidget()
        w.setLayout(layout)
        return w

    def _fila_actual_a_config(self, fila: int) -> dict:
        widget_check = self.tabla.cellWidget(fila, self.COL_VISIBLE)
        check = widget_check.findChild(QCheckBox)
        spin = self.tabla.cellWidget(fila, self.COL_ANCHO)
        return {
            "clave": self._configuracion[fila]["clave"],
            "visible": check.isChecked(),
            "ancho": spin.value(),
        }

    def _sincronizar_estado_actual(self) -> None:
        """Antes de reordenar/restablecer, guarda lo que el usuario ya
        marcó/ajustó para no perderlo."""
        for fila in range(self.tabla.rowCount()):
            self._configuracion[fila] = self._fila_actual_a_config(fila)

    def _mover(self, delta: int) -> None:
        fila = self.tabla.currentRow()
        nueva_fila = fila + delta
        if fila < 0 or not (0 <= nueva_fila < self.tabla.rowCount()):
            return
        self._sincronizar_estado_actual()
        self._configuracion[fila], self._configuracion[nueva_fila] = (
            self._configuracion[nueva_fila],
            self._configuracion[fila],
        )
        self._poblar_tabla()
        self.tabla.setCurrentCell(nueva_fila, self.COL_NOMBRE)

    def _restablecer(self) -> None:
        self._configuracion = configuracion_por_defecto()
        self._poblar_tabla()

    def configuracion_resultante(self) -> list[dict]:
        """Llamar después de exec() == Accepted."""
        self._sincronizar_estado_actual()
        return [dict(c) for c in self._configuracion]