from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)


class DialogoReasignacion(QDialog):
    """Pide el proceso destino y el motivo para solicitar la reasignación
    de una solicitud. La confirmación la maneja quien lo invoca."""

    def __init__(self, numero_solicitud_sac: str, proceso_actual: str, procesos: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Solicitar reasignación")
        self.resize(420, 300)

        layout = QVBoxLayout(self)

        info = QLabel(
            f"Solicitud {numero_solicitud_sac} — proceso actual: {proceso_actual}.\n"
            "Elige el proceso al que debería reasignarse y explica el motivo. "
            "Un administrador revisará y aprobará o rechazará la solicitud."
        )
        info.setWordWrap(True)
        info.setProperty("role", "secondary")
        layout.addWidget(info)

        formulario = QFormLayout()
        self.combo_proceso = QComboBox()
        for p in procesos:
            self.combo_proceso.addItem(p["nombre"], p["id"])
        formulario.addRow("Proceso destino:", self.combo_proceso)

        self.campo_motivo = QPlainTextEdit()
        self.campo_motivo.setPlaceholderText("Motivo de la reasignación (obligatorio)")
        self.campo_motivo.setFixedHeight(90)
        formulario.addRow("Motivo:", self.campo_motivo)
        layout.addLayout(formulario)

        self.lbl_error = QLabel("")
        self.lbl_error.setProperty("role", "secondary")
        layout.addWidget(self.lbl_error)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Solicitar reasignación")
        botones.accepted.connect(self._al_aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _al_aceptar(self) -> None:
        if not self.motivo():
            self.lbl_error.setText("El motivo es obligatorio.")
            return
        if self.proceso_destino_id() is None:
            self.lbl_error.setText("Selecciona un proceso destino.")
            return
        self.accept()

    def proceso_destino_id(self) -> int | None:
        return self.combo_proceso.currentData()

    def proceso_destino_nombre(self) -> str:
        return self.combo_proceso.currentText()

    def motivo(self) -> str:
        return self.campo_motivo.toPlainText().strip()
