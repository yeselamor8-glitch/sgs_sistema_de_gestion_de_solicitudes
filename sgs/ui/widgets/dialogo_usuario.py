from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
)


class DialogoUsuario(QDialog):
    def __init__(self, usuario: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar usuario" if usuario else "Crear usuario")
        self.resize(360, 260)
        usuario = usuario or {}

        layout = QFormLayout(self)

        self.campo_codigo_sac = QLineEdit(usuario.get("codigo_sac", ""))
        self.campo_username = QLineEdit(usuario.get("username", ""))
        self.campo_nombre = QLineEdit(usuario.get("nombre", ""))
        self.combo_rol = QComboBox()
        self.combo_rol.addItems(["FUNCIONARIO", "ADMINISTRADOR"])
        self.combo_rol.setCurrentText(usuario.get("rol", "FUNCIONARIO"))
        self.campo_password = QLineEdit()
        self.campo_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.campo_password.setPlaceholderText(
            "Dejar vacío para no cambiar" if usuario else "Contraseña inicial"
        )

        layout.addRow("Código SAC:", self.campo_codigo_sac)
        layout.addRow("Usuario:", self.campo_username)
        layout.addRow("Nombre:", self.campo_nombre)
        layout.addRow("Rol:", self.combo_rol)
        layout.addRow("Contraseña:", self.campo_password)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addRow(botones)

    def datos(self) -> dict:
        return {
            "codigo_sac": self.campo_codigo_sac.text().strip(),
            "username": self.campo_username.text().strip(),
            "nombre": self.campo_nombre.text().strip(),
            "rol": self.combo_rol.currentText(),
            "password": self.campo_password.text(),
        }