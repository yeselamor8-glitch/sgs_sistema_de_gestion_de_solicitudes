from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from sgs.ui import theme
from sgs.ui.assets_loader import assets

# (clave, icono_id, etiqueta) — el icono se renderiza vía SVG con assets.icono()
MENU_ADMINISTRADOR = [
    ("dashboard", "dashboard", "Dashboard"),
    ("solicitudes", "solicitudes", "Solicitudes"),
    ("importar_sac", "importar_sac", "Importar SAC"),
    ("reportes", "reportes", "Reportes"),
    ("herramientas", "herramientas", "Herramientas"),
    ("configuracion", "configuracion", "Configuración"),
    ("auditoria", "auditoria", "Auditoría"),
]

MENU_FUNCIONARIO = [
    ("dashboard", "dashboard", "Dashboard"),
    ("mis_solicitudes", "solicitudes", "Mis solicitudes"),
    ("importar_sac", "importar_sac", "Importar SAC"),  # visible solo si tiene el permiso
    ("reportes", "reportes", "Reportes"),
    ("herramientas", "herramientas", "Herramientas"),
]

ANCHO_EXPANDIDO = 236
ANCHO_COLAPSADO = 68

VERSION = "SGS v1.0.0"
COPYRIGHT = "© 2026 Alcaldía de Medellín"
COPYRIGHT_SUB = "Secretaría de Salud"


class Sidebar(QWidget):
    """Barra lateral institucional con logo de la Alcaldía arriba, menú de
    navegación central con iconos vectoriales SVG limpios y bloque de
    usuario/versión en el pie. Colapsable a solo iconos."""

    pagina_seleccionada = Signal(str)
    cerrar_sesion = Signal()

    def __init__(self, rol: str, nombre_usuario: str, tiene_permiso_importar_sac: bool = True):
        super().__init__()
        self._colapsado = False
        self._items = MENU_ADMINISTRADOR if rol == "ADMINISTRADOR" else MENU_FUNCIONARIO
        self._rol = rol
        self._nombre_usuario = nombre_usuario

        self.setFixedWidth(ANCHO_EXPANDIDO)
        self.setStyleSheet(
            f"""
            Sidebar {{
                background-color: #FFFFFF;
                border-right: 1px solid #E2E8F0;
            }}
            """
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 14, 0, 14)
        self._layout.setSpacing(3)

        self._layout.addWidget(self._bloque_logo())
        self._layout.addWidget(self._separador())

        self._botones: dict[str, QPushButton] = {}
        for clave, icono_id, etiqueta in self._items:
            if clave == "importar_sac" and rol == "FUNCIONARIO" and not tiene_permiso_importar_sac:
                continue
            boton = self._crear_boton_menu(clave, icono_id, etiqueta)
            self._layout.addWidget(boton)
            self._botones[clave] = boton

        self._layout.addStretch()

        self._layout.addWidget(self._separador())
        self._boton_cerrar_sesion = QPushButton("  Cerrar sesión")
        qicon_cerrar = assets.icono("cerrar_sesion")
        if not qicon_cerrar.isNull():
            self._boton_cerrar_sesion.setIcon(qicon_cerrar)
            self._boton_cerrar_sesion.setIconSize(QSize(18, 18))
        self._boton_cerrar_sesion.setCursor(Qt.CursorShape.PointingHandCursor)
        self._boton_cerrar_sesion.setStyleSheet(self._estilo_boton_cerrar())
        self._boton_cerrar_sesion.clicked.connect(self.cerrar_sesion.emit)
        self._layout.addWidget(self._boton_cerrar_sesion)

        self._layout.addWidget(self._bloque_footer())
        self._actualizar_textos()

        if self._items:
            self._seleccionar(self._items[0][0])

    # ------------------------------------------------------------------
    # Bloque del logo (arriba)
    # ------------------------------------------------------------------
    def _bloque_logo(self) -> QWidget:
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(14, 4, 14, 6)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._lbl_logo = QLabel()
        self._lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._render_logo()
        layout.addWidget(self._lbl_logo)

        self._lbl_logo_sub = QLabel("Sistema de Gestión\nde Solicitudes")
        self._lbl_logo_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_logo_sub.setStyleSheet(
            "color: #64748B; font-size: 11px; font-weight: 600; line-height: 1.2;"
        )
        layout.addWidget(self._lbl_logo_sub)

        # Fila del botón de colapsar
        fila_colapsar = QHBoxLayout()
        fila_colapsar.setContentsMargins(0, 4, 0, 0)
        fila_colapsar.addStretch()
        self._boton_colapsar = QPushButton("«")
        self._boton_colapsar.setFixedSize(26, 26)
        self._boton_colapsar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._boton_colapsar.setToolTip("Contraer menú lateral")
        self._boton_colapsar.setStyleSheet(
            """
            QPushButton {
                background-color: #F8FAFC;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-weight: 700;
                font-size: 13px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #E0F2FE;
                color: #0284C7;
                border-color: #38BDF8;
            }
            """
        )
        self._boton_colapsar.clicked.connect(self._alternar_colapso)
        fila_colapsar.addWidget(self._boton_colapsar)
        layout.addLayout(fila_colapsar)
        return contenedor

    def _render_logo(self) -> None:
        ancho = 36 if self._colapsado else 165
        pixmap = assets.logo_icono() if self._colapsado else assets.logo_principal()
        if not pixmap.isNull():
            self._lbl_logo.setPixmap(
                pixmap.scaledToWidth(ancho, Qt.TransformationMode.SmoothTransformation)
            )
            self._lbl_logo.setText("")
        else:
            self._lbl_logo.setPixmap(pixmap)
            self._lbl_logo.setText("SGS" if self._colapsado else "Alcaldía de Medellín")
            self._lbl_logo.setStyleSheet(
                f"color: {theme.COLORES['primary']}; font-weight: 800; font-size: 15px;"
            )

    # ------------------------------------------------------------------
    def _separador(self) -> QFrame:
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setFixedHeight(1)
        linea.setStyleSheet("background-color: #E2E8F0; border: none; margin: 6px 14px;")
        return linea

    def _crear_boton_menu(self, clave: str, icono_id: str, etiqueta: str) -> QPushButton:
        boton = QPushButton(f"  {etiqueta}")
        boton.setCheckable(True)
        boton.setCursor(Qt.CursorShape.PointingHandCursor)
        boton.setMinimumHeight(42)

        qicon = assets.icono(icono_id)
        if not qicon.isNull():
            boton.setIcon(qicon)
            boton.setIconSize(QSize(18, 18))

        boton.setStyleSheet(self._estilo_boton())
        boton.clicked.connect(lambda checked, c=clave: self._seleccionar(c))
        return boton

    def _estilo_boton(self) -> str:
        return f"""
            QPushButton {{
                text-align: left;
                background-color: transparent;
                color: #334155;
                border: none;
                border-left: 3px solid transparent;
                border-radius: 8px;
                padding: 9px 12px;
                margin: 1px 8px;
                font-weight: 500;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #F1F5F9;
                color: #0F172A;
            }}
            QPushButton:checked {{
                background-color: #E0F2FE;
                color: {theme.COLORES['primary_dark']};
                border-left: 3px solid {theme.COLORES['primary']};
                font-weight: 700;
            }}
        """

    def _estilo_boton_cerrar(self) -> str:
        return """
            QPushButton {
                text-align: left;
                background-color: transparent;
                color: #64748B;
                border: none;
                border-radius: 8px;
                padding: 9px 12px;
                margin: 1px 8px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
                color: #DC2626;
            }
        """

    # ------------------------------------------------------------------
    # Footer (usuario, versión, copyright)
    # ------------------------------------------------------------------
    def _bloque_footer(self) -> QWidget:
        self._footer = QWidget()
        layout = QVBoxLayout(self._footer)
        layout.setContentsMargins(14, 6, 14, 0)
        layout.setSpacing(3)

        self._lbl_usuario = QLabel(self._nombre_usuario)
        self._lbl_usuario.setStyleSheet(
            "color: #0F172A; font-size: 13px; font-weight: 700;"
        )
        self._lbl_rol = QLabel(self._rol.capitalize())
        self._lbl_rol.setStyleSheet(
            f"color: {theme.COLORES['primary_dark']}; font-size: 11px; font-weight: 600;"
        )

        linea = QFrame()
        linea.setFixedHeight(1)
        linea.setStyleSheet("background-color: #E2E8F0; border: none; margin: 4px 0;")

        self._lbl_version = QLabel(VERSION)
        self._lbl_version.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self._lbl_copy = QLabel(f"{COPYRIGHT}\n{COPYRIGHT_SUB}")
        self._lbl_copy.setStyleSheet("color: #94A3B8; font-size: 10px; line-height: 1.2;")

        layout.addWidget(self._lbl_usuario)
        layout.addWidget(self._lbl_rol)
        layout.addWidget(linea)
        layout.addWidget(self._lbl_version)
        layout.addWidget(self._lbl_copy)
        return self._footer

    # ------------------------------------------------------------------
    def _alternar_colapso(self) -> None:
        self._colapsado = not self._colapsado
        self.setFixedWidth(ANCHO_COLAPSADO if self._colapsado else ANCHO_EXPANDIDO)
        self._boton_colapsar.setText("»" if self._colapsado else "«")
        self._boton_colapsar.setToolTip("Expandir menú lateral" if self._colapsado else "Contraer menú lateral")
        self._render_logo()
        self._actualizar_textos()

    def _actualizar_textos(self) -> None:
        self._lbl_logo_sub.setVisible(not self._colapsado)
        self._footer.setVisible(not self._colapsado)

        if self._colapsado:
            self._boton_cerrar_sesion.setText("")
            self._boton_cerrar_sesion.setToolTip("Cerrar sesión")
        else:
            self._boton_cerrar_sesion.setText("  Cerrar sesión")
            self._boton_cerrar_sesion.setToolTip("")

        for clave, icono_id, etiqueta in self._items:
            boton = self._botones.get(clave)
            if boton is None:
                continue
            if self._colapsado:
                boton.setText("")
                boton.setToolTip(etiqueta)
            else:
                boton.setText(f"  {etiqueta}")
                boton.setToolTip("")

    def _seleccionar(self, clave: str) -> None:
        for k, boton in self._botones.items():
            boton.setChecked(k == clave)
        self.pagina_seleccionada.emit(clave)

    def seleccionar_sin_emitir(self, clave: str) -> None:
        """Marca como activo el botón del menú correspondiente a `clave` sin
        emitir la señal de cambio de página (usado al navegar por código)."""
        for k, boton in self._botones.items():
            boton.setChecked(k == clave)

    def actualizar_permiso_importar_sac(self, tiene: bool) -> None:
        """Refresca en vivo la visibilidad del ítem Importar SAC (rol
        funcionario) cuando el administrador cambia el permiso."""
        if self._rol != "FUNCIONARIO":
            return
        tiene_ahora = "importar_sac" in self._botones
        if tiene and not tiene_ahora:
            boton = self._crear_boton_menu("importar_sac", "importar_sac", "Importar SAC")
            indice = self._layout.indexOf(self._botones["reportes"])
            self._layout.insertWidget(indice, boton)
            self._botones["importar_sac"] = boton
            self._actualizar_textos()
        elif not tiene and tiene_ahora:
            boton = self._botones.pop("importar_sac")
            self._layout.removeWidget(boton)
            boton.deleteLater()
            self._actualizar_textos()
            if not any(b.isChecked() for b in self._botones.values()):
                self._seleccionar(self._items[0][0])
