from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sgs.ui import theme
from sgs.ui.assets_loader import assets


class LoginWindow(QWidget):
    """Solo pide usuario/contraseña. El rol se resuelve en backend después
    de autenticar — no existe selector Administrador/Funcionario (sección
    4 del documento funcional).

    Diseño de dos paneles: izquierda con gradiente azul institucional y el
    logo; derecha panel blanco con el formulario de acceso."""

    login_exitoso = Signal(int, str, str)  # usuario_id, nombre, rol

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Solicitudes — Iniciar sesión")
        self.resize(920, 600)
        self.setMinimumSize(760, 520)
        self.setStyleSheet(f"background-color: {theme.COLORES['background']};")

        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        raiz.addWidget(self._panel_izquierdo(), stretch=5)
        raiz.addWidget(self._panel_derecho(), stretch=6)

    # ------------------------------------------------------------------
    def _panel_izquierdo(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(
            f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0082C8, stop:0.5 {theme.COLORES['primary_dark']}, stop:1 #083344);
            }}
            QLabel {{ background: transparent; color: white; }}
            """
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(40, 44, 40, 40)
        layout.setSpacing(16)

        # Contenedor del logo limpio institucional
        marca = QFrame()
        marca.setStyleSheet("QFrame { background: transparent; border: none; }")
        marca_layout = QVBoxLayout(marca)
        marca_layout.setContentsMargins(0, 0, 0, 0)
        marca_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = assets.logo_principal()
        lbl_logo = QLabel()
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not logo.isNull():
            lbl_logo.setPixmap(
                logo.scaledToWidth(190, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            lbl_logo.setText("Alcaldía de Medellín")
            lbl_logo.setStyleSheet("color: white; font-size: 20px; font-weight: 700;")
        marca_layout.addWidget(lbl_logo)
        layout.addWidget(marca, alignment=Qt.AlignmentFlag.AlignHCenter)

        tag_institucional = QLabel("Distrito de Ciencia, Tecnología e Innovación")
        tag_institucional.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag_institucional.setStyleSheet(
            "color: rgba(255, 255, 255, 0.85); font-size: 11px; font-weight: 500; letter-spacing: 0.5px;"
        )
        layout.addWidget(tag_institucional)

        layout.addStretch(1)

        marca_texto = QLabel("Sistema de Gestión\nde Solicitudes")
        marca_texto.setAlignment(Qt.AlignmentFlag.AlignLeft)
        marca_texto.setStyleSheet(
            "color: white; font-size: 26px; font-weight: 800; line-height: 1.2;"
        )
        layout.addWidget(marca_texto)

        subtitulo = QLabel("Plataforma institucional de seguimiento, control y gestión de requerimientos ciudadanos.")
        subtitulo.setWordWrap(True)
        subtitulo.setStyleSheet("color: rgba(255, 255, 255, 0.90); font-size: 13px; line-height: 1.4;")
        layout.addWidget(subtitulo)

        layout.addStretch(2)

        pie = QLabel("Secretaría de Salud · Medellín")
        pie.setAlignment(Qt.AlignmentFlag.AlignLeft)
        pie.setStyleSheet("color: rgba(255, 255, 255, 0.75); font-size: 12px; font-weight: 500;")
        layout.addWidget(pie)
        return panel

    # ------------------------------------------------------------------
    def _panel_derecho(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(f"QFrame {{ background-color: #FFFFFF; }}")
        contenedor = QVBoxLayout(panel)
        contenedor.setContentsMargins(60, 48, 60, 40)
        contenedor.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        formulario = QVBoxLayout()
        formulario.setSpacing(12)

        bienvenida = QLabel("Iniciar sesión")
        bienvenida.setStyleSheet(
            "color: #0F172A; font-size: 26px; font-weight: 800; letter-spacing: -0.3px;"
        )
        instruccion = QLabel("Ingresa con tu usuario institucional asignado.")
        instruccion.setStyleSheet("color: #64748B; font-size: 13px;")

        formulario.addWidget(bienvenida)
        formulario.addWidget(instruccion)
        formulario.addSpacing(12)

        formulario.addWidget(self._etiqueta_campo("Usuario institucional"))
        self.campo_usuario = self._campo_con_icono("usuario", "Ingresa tu usuario institucional")
        formulario.addWidget(self.campo_usuario)

        formulario.addSpacing(4)
        formulario.addWidget(self._etiqueta_campo("Contraseña de acceso"))
        self.campo_password = self._campo_con_icono("candado", "Ingresa tu contraseña", password=True)
        formulario.addWidget(self.campo_password)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(
            "background-color: #FEF2F2; border: 1px solid #FECACA; "
            "border-radius: 8px; color: #DC2626; padding: 10px 12px; "
            "font-size: 12px; font-weight: 500;"
        )
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        formulario.addWidget(self.lbl_error)

        formulario.addSpacing(10)
        boton_entrar = QPushButton("Ingresar a la plataforma")
        boton_entrar.setObjectName("botonIngresar")
        boton_entrar.setProperty("variant", "primary")
        boton_entrar.setMinimumHeight(46)
        boton_entrar.setCursor(Qt.CursorShape.PointingHandCursor)
        boton_entrar.setStyleSheet(
            f"""
            QPushButton#botonIngresar {{
                background-color: {theme.COLORES['primary']};
                color: #FFFFFF;
                border: 1px solid #0087BD;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton#botonIngresar:hover {{
                background-color: {theme.COLORES['primary_dark']};
                border-color: #006094;
            }}
            QPushButton#botonIngresar:pressed {{
                background-color: #004A73;
            }}
            """
        )
        boton_entrar.clicked.connect(self._intentar_login)
        formulario.addWidget(boton_entrar)

        contenedor.addLayout(formulario)
        contenedor.addStretch()

        pie = QLabel("SGS v1.0.0 · Alcaldía de Medellín · Secretaría de Salud")
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pie.setStyleSheet("color: #94A3B8; font-size: 11px;")
        contenedor.addWidget(pie)

        self.campo_password.returnPressed.connect(self._intentar_login)
        self.campo_usuario.returnPressed.connect(lambda: self.campo_password.setFocus())
        return panel

    # ------------------------------------------------------------------
    def _etiqueta_campo(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet(
            "color: #334155; font-size: 12px; font-weight: 600;"
        )
        return lbl

    def _campo_con_icono(self, icono: str, placeholder: str, password: bool = False) -> QLineEdit:
        campo = QLineEdit()
        campo.setPlaceholderText(placeholder)
        campo.setMinimumHeight(44)
        campo.setStyleSheet(
            """
            QLineEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:hover {
                border-color: #94A3B8;
            }
            QLineEdit:focus {
                border: 1.5px solid #00A0DF;
                background-color: #FFFFFF;
            }
            """
        )
        qicon = assets.icono(icono)
        if not qicon.isNull():
            accion = campo.addAction(qicon, QLineEdit.ActionPosition.LeadingPosition)
            accion.setEnabled(False)
        if password:
            campo.setEchoMode(QLineEdit.EchoMode.Password)
            self._agregar_toggle_password(campo)
        return campo

    def _agregar_toggle_password(self, campo: QLineEdit) -> None:
        icono_ver = assets.icono("ver")
        icono_ocultar = assets.icono("ocultar")
        icono_inicial = icono_ver if not icono_ver.isNull() else campo.style().standardIcon(
            campo.style().StandardPixmap.SP_DialogYesButton
        )
        accion = campo.addAction(
            icono_inicial,
            QLineEdit.ActionPosition.TrailingPosition,
        )

        def alternar():
            if campo.echoMode() == QLineEdit.EchoMode.Password:
                campo.setEchoMode(QLineEdit.EchoMode.Normal)
                if not icono_ocultar.isNull():
                    accion.setIcon(icono_ocultar)
            else:
                campo.setEchoMode(QLineEdit.EchoMode.Password)
                if not icono_ver.isNull():
                    accion.setIcon(icono_ver)

        accion.triggered.connect(alternar)

    # ------------------------------------------------------------------
    def _intentar_login(self) -> None:
        from sgs.app.casos_de_uso import autenticar

        usuario = self.campo_usuario.text().strip()
        password = self.campo_password.text()
        if not usuario or not password:
            self._mostrar_error("Ingresa usuario y contraseña.")
            return

        try:
            resultado = autenticar(usuario, password)
        except Exception:
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

