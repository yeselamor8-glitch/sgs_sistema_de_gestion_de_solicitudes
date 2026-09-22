from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class DialogoReglaClasificacion(QDialog):
    """Editor de una regla de clasificación: proceso destino, tipo
    (normal/excepción), orden, descripción y una tabla de condiciones.

    Dentro de una condición, varios valores separados por coma son OR;
    entre condiciones distintas es AND (así lo evalúa el motor).
    """

    def __init__(self, procesos: list[dict], campos: list[str], operadores: list[str],
                 tipos: list[str], regla: dict | None = None, parent=None):
        super().__init__(parent)
        self._campos = campos
        self._operadores = operadores
        self.setWindowTitle("Editar regla" if regla else "Nueva regla de clasificación")
        self.resize(560, 480)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Una regla enruta solicitudes a un proceso. Varios valores en una condición "
            "(separados por coma) son OR; entre condiciones distintas es AND. Las reglas "
            "de tipo «excepción» se evalúan primero."
        )
        info.setWordWrap(True)
        info.setProperty("role", "secondary")
        layout.addWidget(info)

        formulario = QFormLayout()
        self.combo_proceso = QComboBox()
        for p in procesos:
            self.combo_proceso.addItem(p["nombre"], p["id"])
        formulario.addRow("Proceso destino:", self.combo_proceso)

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(tipos)
        formulario.addRow("Tipo de regla:", self.combo_tipo)

        self.spin_orden = QSpinBox()
        self.spin_orden.setRange(1, 999)
        self.spin_orden.setValue(100)
        formulario.addRow("Orden de evaluación:", self.spin_orden)

        self.campo_descripcion = QLineEdit()
        self.campo_descripcion.setPlaceholderText("Descripción (opcional)")
        formulario.addRow("Descripción:", self.campo_descripcion)
        layout.addLayout(formulario)

        layout.addWidget(QLabel("Condiciones (campo · operador · valores separados por coma):"))
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Campo", "Operador", "Valores (coma = OR)"])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setColumnWidth(0, 180)
        self.tabla.setColumnWidth(1, 120)
        layout.addWidget(self.tabla)

        fila_cond = QHBoxLayout()
        boton_agregar = QPushButton("+ Agregar condición")
        boton_agregar.setProperty("variant", "ghost")
        boton_agregar.clicked.connect(lambda: self._agregar_fila())
        boton_quitar = QPushButton("Quitar condición")
        boton_quitar.setProperty("variant", "ghost")
        boton_quitar.clicked.connect(self._quitar_fila)
        fila_cond.addWidget(boton_agregar)
        fila_cond.addWidget(boton_quitar)
        fila_cond.addStretch()
        layout.addLayout(fila_cond)

        self.lbl_error = QLabel("")
        self.lbl_error.setProperty("role", "secondary")
        layout.addWidget(self.lbl_error)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Guardar")
        botones.accepted.connect(self._al_aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        if regla:
            self._cargar(regla)
        else:
            self._agregar_fila()

    # ------------------------------------------------------------------
    def _agregar_fila(self, campo: str = "", operador: str = "", valores: str = "") -> None:
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)

        combo_campo = QComboBox()
        combo_campo.setEditable(True)  # permite un campo no listado si hiciera falta
        combo_campo.addItems(self._campos)
        if campo:
            combo_campo.setCurrentText(campo)
        self.tabla.setCellWidget(fila, 0, combo_campo)

        combo_op = QComboBox()
        combo_op.addItems(self._operadores)
        if operador:
            combo_op.setCurrentText(operador)
        self.tabla.setCellWidget(fila, 1, combo_op)

        self.tabla.setItem(fila, 2, QTableWidgetItem(valores))

    def _quitar_fila(self) -> None:
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.tabla.removeRow(fila)

    def _cargar(self, regla: dict) -> None:
        idx = self.combo_proceso.findData(regla["proceso_id"])
        if idx >= 0:
            self.combo_proceso.setCurrentIndex(idx)
        self.combo_tipo.setCurrentText(regla["tipo_regla"])
        self.spin_orden.setValue(int(regla.get("orden_evaluacion", 100)))
        self.campo_descripcion.setText(regla.get("descripcion", ""))
        for c in regla.get("condiciones", []):
            self._agregar_fila(c["campo"], c["operador"], ", ".join(c["valores"]))
        if self.tabla.rowCount() == 0:
            self._agregar_fila()

    # ------------------------------------------------------------------
    def _al_aceptar(self) -> None:
        if not self.condiciones():
            self.lbl_error.setText("Agrega al menos una condición con su campo y valores.")
            self.lbl_error.setStyleSheet("color: #E53935;")
            return
        self.accept()

    def proceso_id(self) -> int | None:
        return self.combo_proceso.currentData()

    def tipo_regla(self) -> str:
        return self.combo_tipo.currentText()

    def orden(self) -> int:
        return self.spin_orden.value()

    def descripcion(self) -> str:
        return self.campo_descripcion.text().strip()

    def condiciones(self) -> list[tuple[str, str, list[str]]]:
        """[(campo, operador, [valores]), ...] — descarta filas incompletas."""
        resultado = []
        for fila in range(self.tabla.rowCount()):
            combo_campo = self.tabla.cellWidget(fila, 0)
            combo_op = self.tabla.cellWidget(fila, 1)
            item_val = self.tabla.item(fila, 2)
            campo = combo_campo.currentText().strip() if combo_campo else ""
            operador = combo_op.currentText().strip() if combo_op else ""
            valores_txt = item_val.text().strip() if item_val else ""
            valores = [v.strip() for v in valores_txt.split(",") if v.strip()]
            if campo and operador and valores:
                resultado.append((campo, operador, valores))
        return resultado
