from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class DialogoColumnasAnalisis(QDialog):
    """Mostrar/ocultar y reordenar columnas de cualquier conjunto de
    datos cargado (sistema o archivo SAC temporal) — a diferencia del
    catálogo fijo de la pantalla Solicitudes, aquí las columnas
    dependen de lo que traiga cada fuente."""

    def __init__(self, columnas_disponibles: list[str], columnas_visibles_actuales: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar columnas")
        self.resize(320, 420)

        # orden: primero las visibles actuales (en su orden), luego el resto
        resto = [c for c in columnas_disponibles if c not in columnas_visibles_actuales]
        self._orden = list(columnas_visibles_actuales) + resto

        layout = QVBoxLayout(self)
        info = QLabel("Marca las columnas a mostrar y usa las flechas para reordenarlas.")
        info.setProperty("role", "secondary")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.lista = QListWidget()
        self._poblar(columnas_visibles_actuales)
        layout.addWidget(self.lista)

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

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _poblar(self, visibles: list[str]) -> None:
        self.lista.clear()
        for col in self._orden:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if col in visibles else Qt.CheckState.Unchecked)
            self.lista.addItem(item)

    def _mover(self, delta: int) -> None:
        fila = self.lista.currentRow()
        nueva_fila = fila + delta
        if fila < 0 or not (0 <= nueva_fila < self.lista.count()):
            return
        self._orden[fila], self._orden[nueva_fila] = self._orden[nueva_fila], self._orden[fila]
        visibles_actuales = self.columnas_seleccionadas()
        self._poblar(visibles_actuales)
        self.lista.setCurrentRow(nueva_fila)

    def columnas_seleccionadas(self) -> list[str]:
        return [
            self.lista.item(i).text()
            for i in range(self.lista.count())
            if self.lista.item(i).checkState() == Qt.CheckState.Checked
        ]