from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from sgs.ui import theme


class LoginWindow(QWidget):
    """Solo pide usuario/contraseña. El rol se resuelve en backend después
    de autenticar — no existe selector Administrador/Funcionario (sección
    4 del documento funcional)."""

    login_exitoso = Signal(int, str, str)  # usuario_id, nombre, rol

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Solicitudes — Iniciar sesión")
        self.resize(420, 480)
        self.setStyleSheet(f"background-color: {theme.BG_APP};")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tarjeta = QFrame()
        tarjeta.setFixedWidth(340)
        tarjeta.setStyleSheet(f"background-color: {theme.BG_CARD}; border-radius: 14px;")
        tarjeta_layout = QVBoxLayout(tarjeta)
        tarjeta_layout.setContentsMargins(28, 32, 28, 32)
        tarjeta_layout.setSpacing(14)

        titulo = QLabel("Gestión de Solicitudes")
        titulo.setStyleSheet("font-size: 17px; font-weight: 600;")
        subtitulo = QLabel("Ingresa con tu usuario institucional")
        subtitulo.setProperty("role", "secondary")

        self.campo_usuario = QLineEdit()
        self.campo_usuario.setPlaceholderText("Usuario")
        self.campo_password = QLineEdit()
        self.campo_password.setPlaceholderText("Contraseña")
        self.campo_password.setEchoMode(QLineEdit.EchoMode.Password)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(f"color: {theme.SEMAFORO_ROJO}; font-size: 12px;")
        self.lbl_error.hide()

        boton_entrar = QPushButton("Entrar")
        boton_entrar.clicked.connect(self._intentar_login)
        self.campo_password.returnPressed.connect(self._intentar_login)

        tarjeta_layout.addWidget(titulo)
        tarjeta_layout.addWidget(subtitulo)
        tarjeta_layout.addSpacing(10)
        tarjeta_layout.addWidget(self.campo_usuario)
        tarjeta_layout.addWidget(self.campo_password)
        tarjeta_layout.addWidget(self.lbl_error)
        tarjeta_layout.addWidget(boton_entrar)

        layout.addWidget(tarjeta)

    def _intentar_login(self) -> None:
        from sgs.app.casos_de_uso import autenticar  # import perezoso: evita tocar la BD al abrir la ventana

        usuario = self.campo_usuario.text().strip()
        password = self.campo_password.text()
        if not usuario or not password:
            self._mostrar_error("Ingresa usuario y contraseña.")
            return

        try:
            resultado = autenticar(usuario, password)
        except Exception:
            # No exponer detalles técnicos (cadena de conexión, driver, etc.) en la UI
            self._mostrar_error("No fue posible conectar con el sistema. Intenta de nuevo.")
            return

        if not resultado.ok:
            self._mostrar_error(resultado.mensaje_error or "Usuario o contraseña incorrectos.")
            return

        self.lbl_error.hide()
        self.login_exitoso.emit(resultado.usuario_id, resultado.nombre or resultado.username, resultado.rol)

    def _mostrar_error(self, mensaje: str) -> None:
        self.lbl_error.setText(mensaje)
        self.lbl_error.show()