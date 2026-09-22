from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from sgs.ui import theme
from sgs.ui.assets_loader import assets

# (clave, ícono, etiqueta) — el ícono se conserva visible incluso colapsado
MENU_ADMINISTRADOR = [
    ("dashboard", "🏠", "Dashboard"),
    ("solicitudes", "📋", "Solicitudes"),
    ("importar_sac", "📥", "Importar SAC"),
    ("reportes", "📊", "Reportes"),
    ("herramientas", "🛠", "Herramientas"),
    ("configuracion", "⚙", "Configuración"),
    ("auditoria", "📝", "Auditoría"),
]

MENU_FUNCIONARIO = [
    ("dashboard", "🏠", "Dashboard"),
    ("mis_solicitudes", "📋", "Mis solicitudes"),
    ("importar_sac", "📥", "Importar SAC"),  # visible solo si tiene el permiso
    ("reportes", "📊", "Reportes"),
    ("herramientas", "🛠", "Herramientas"),
]

ANCHO_EXPANDIDO = 232
ANCHO_COLAPSADO = 64

VERSION = "SGS v1.0.0"
COPYRIGHT = "© 2026 Alcaldía de Medellín"
COPYRIGHT_SUB = "Secretaría de Salud"


class Sidebar(QWidget):
    """Barra lateral clara con logo institucional arriba, menú de
    navegación en el centro y bloque de usuario/versión abajo. No incluye
    Notificaciones ni Solicitudes de cambio como ítems — esos viven en la
    campana del encabezado. Colapsable a solo íconos."""

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
            f"Sidebar {{ background-color: {theme.COLORES['surface']}; "
            f"border-right: 1px solid {theme.COLORES['outline_variant']}; }}"
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 12, 0, 12)
        self._layout.setSpacing(2)

        self._layout.addWidget(self._bloque_logo())
        self._layout.addWidget(self._separador())

        self._botones: dict[str, QPushButton] = {}
        for clave, icono, etiqueta in self._items:
            if clave == "importar_sac" and rol == "FUNCIONARIO" and not tiene_permiso_importar_sac:
                continue
            boton = self._crear_boton_menu(clave, icono, etiqueta)
            self._layout.addWidget(boton)
            self._botones[clave] = boton

        self._layout.addStretch()

        self._layout.addWidget(self._separador())
        self._boton_cerrar_sesion = QPushButton("🚪   Cerrar sesión")
        self._boton_cerrar_sesion.setCursor(Qt.CursorShape.PointingHandCursor)
        self._boton_cerrar_sesion.setStyleSheet(self._estilo_boton())
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
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._lbl_logo = QLabel()
        self._lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._render_logo()
        layout.addWidget(self._lbl_logo)

        self._lbl_logo_sub = QLabel("Sistema de Gestión\nde Solicitudes")
        self._lbl_logo_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_logo_sub.setStyleSheet(
            f"color: {theme.COLORES['on_surface_var']}; font-size: 11px;"
        )
        layout.addWidget(self._lbl_logo_sub)

        # fila del botón de colapsar, alineada a la derecha
        fila_colapsar = QHBoxLayout()
        fila_colapsar.setContentsMargins(0, 0, 0, 0)
        fila_colapsar.addStretch()
        self._boton_colapsar = QPushButton("«")
        self._boton_colapsar.setFixedSize(24, 24)
        self._boton_colapsar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._boton_colapsar.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {theme.COLORES['on_surface_var']};"
            f" border: 1px solid {theme.COLORES['outline']}; border-radius: 6px; font-weight: 600; padding: 0; }}"
            f"QPushButton:hover {{ background-color: {theme.COLORES['surface_variant']}; }}"
        )
        self._boton_colapsar.clicked.connect(self._alternar_colapso)
        fila_colapsar.addWidget(self._boton_colapsar)
        layout.addLayout(fila_colapsar)
        return contenedor

    def _render_logo(self) -> None:
        ancho = 40 if self._colapsado else 180
        pixmap = assets.logo_icono() if self._colapsado else assets.logo_principal()
        if not pixmap.isNull():
            self._lbl_logo.setPixmap(
                pixmap.scaledToWidth(ancho, Qt.TransformationMode.SmoothTransformation)
            )
            self._lbl_logo.setText("")
        else:
            # Respaldo textual si el logo aún no está en assets
            self._lbl_logo.setPixmap(pixmap)  # limpia cualquier pixmap previo
            self._lbl_logo.setText("SGS" if self._colapsado else "Alcaldía de Medellín")
            self._lbl_logo.setStyleSheet(
                f"color: {theme.COLORES['primary']}; font-weight: 700; font-size: 15px;"
            )

    # ------------------------------------------------------------------
    def _separador(self) -> QFrame:
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setFixedHeight(1)
        linea.setStyleSheet(f"background-color: {theme.COLORES['outline_variant']}; border: none; margin: 8px 16px;")
        return linea

    def _crear_boton_menu(self, clave: str, icono: str, etiqueta: str) -> QPushButton:
        boton = QPushButton(f"{icono}   {etiqueta}")
        boton.setCheckable(True)
        boton.setCursor(Qt.CursorShape.PointingHandCursor)
        boton.setMinimumHeight(44)
        boton.setStyleSheet(self._estilo_boton())
        boton.clicked.connect(lambda checked, c=clave: self._seleccionar(c))
        return boton

    def _estilo_boton(self) -> str:
        return f"""
            QPushButton {{
                text-align: left; background-color: transparent; color: {theme.COLORES['on_surface']};
                border: none; border-left: 4px solid transparent; border-radius: 8px;
                padding: 10px 12px; margin: 1px 8px; font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {theme.COLORES['surface_hover']}; }}
            QPushButton:checked {{
                background-color: {theme.COLORES['surface_variant']};
                color: {theme.COLORES['primary']};
                border-left: 4px solid {theme.COLORES['primary']};
                font-weight: 600;
            }}
        """

    # ------------------------------------------------------------------
    # Footer (usuario, versión, copyright)
    # ------------------------------------------------------------------
    def _bloque_footer(self) -> QWidget:
        self._footer = QWidget()
        layout = QVBoxLayout(self._footer)
        layout.setContentsMargins(16, 8, 16, 0)
        layout.setSpacing(2)

        self._lbl_usuario = QLabel(self._nombre_usuario)
        self._lbl_usuario.setStyleSheet(
            f"color: {theme.COLORES['on_surface']}; font-size: 13px; font-weight: 700;"
        )
        self._lbl_rol = QLabel(self._rol.capitalize())
        self._lbl_rol.setStyleSheet(f"color: {theme.COLORES['on_surface_var']}; font-size: 11px;")

        linea = QFrame()
        linea.setFixedHeight(1)
        linea.setStyleSheet(f"background-color: {theme.COLORES['outline_variant']}; border: none; margin: 6px 0;")

        self._lbl_version = QLabel(VERSION)
        self._lbl_version.setStyleSheet(f"color: {theme.COLORES['on_surface_var']}; font-size: 11px;")
        self._lbl_copy = QLabel(f"{COPYRIGHT}\n{COPYRIGHT_SUB}")
        self._lbl_copy.setStyleSheet(f"color: {theme.COLORES['on_surface_var']}; font-size: 10px;")

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
        self._render_logo()
        self._actualizar_textos()

    def _actualizar_textos(self) -> None:
        self._lbl_logo_sub.setVisible(not self._colapsado)
        self._footer.setVisible(not self._colapsado)
        self._boton_cerrar_sesion.setText("🚪" if self._colapsado else "🚪   Cerrar sesión")
        self._boton_cerrar_sesion.setToolTip("Cerrar sesión" if self._colapsado else "")

        for clave, icono, etiqueta in self._items:
            boton = self._botones.get(clave)
            if boton is None:
                continue
            boton.setText(icono if self._colapsado else f"{icono}   {etiqueta}")
            boton.setToolTip(etiqueta if self._colapsado else "")

    def _seleccionar(self, clave: str) -> None:
        for k, boton in self._botones.items():
            boton.setChecked(k == clave)
        self.pagina_seleccionada.emit(clave)

    def actualizar_permiso_importar_sac(self, tiene: bool) -> None:
        """Refresca en vivo la visibilidad del ítem Importar SAC (rol
        funcionario) cuando el administrador cambia el permiso."""
        if self._rol != "FUNCIONARIO":
            return
        tiene_ahora = "importar_sac" in self._botones
        if tiene and not tiene_ahora:
            boton = self._crear_boton_menu("importar_sac", "📥", "Importar SAC")
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
