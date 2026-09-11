from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout

from sgs.ui import theme

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

ANCHO_EXPANDIDO = 210
ANCHO_COLAPSADO = 60


class Sidebar(QWidget):
    """Tema claro. No incluye Notificaciones ni Solicitudes de cambio como
    ítems — esos viven en la campana del encabezado. Colapsable a solo
    íconos para liberar espacio en pantallas con tablas de muchas columnas."""

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
            f"background-color: {theme.BG_SIDEBAR}; border-right: 1px solid {theme.BORDER_SIDEBAR};"
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 14, 0, 12)
        self._layout.setSpacing(2)

        self._layout.addLayout(self._fila_titulo())

        self._botones: dict[str, QPushButton] = {}
        for clave, icono, etiqueta in self._items:
            if clave == "importar_sac" and rol == "FUNCIONARIO" and not tiene_permiso_importar_sac:
                continue
            boton = QPushButton(f"{icono}   {etiqueta}")
            boton.setCheckable(True)
            boton.setStyleSheet(self._estilo_boton())
            boton.clicked.connect(lambda checked, c=clave: self._seleccionar(c))
            self._layout.addWidget(boton)
            self._botones[clave] = boton

        self._layout.addStretch()

        self._boton_cerrar_sesion = QPushButton("🚪  Cerrar sesión")
        self._boton_cerrar_sesion.setStyleSheet(self._estilo_boton())
        self._boton_cerrar_sesion.clicked.connect(self.cerrar_sesion.emit)
        self._layout.addWidget(self._boton_cerrar_sesion)

        self._lbl_pie = QLabel()
        self._lbl_pie.setStyleSheet(
            f"color: {theme.TEXT_ON_SIDEBAR_MUTED}; font-size: 11px; padding: 10px 16px 0 16px;"
            f"border-top: 1px solid {theme.BORDER_SIDEBAR};"
        )
        self._layout.addWidget(self._lbl_pie)
        self._actualizar_textos()

        if self._items:
            self._seleccionar(self._items[0][0])

    def _fila_titulo(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setContentsMargins(16, 0, 12, 14)
        self._lbl_titulo = QLabel("Gestión de\nSolicitudes")
        self._lbl_titulo.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-weight: 600; font-size: 14px;"
        )
        boton_colapsar = QPushButton("«")
        boton_colapsar.setFixedSize(24, 24)
        boton_colapsar.setStyleSheet(
            f"background-color: transparent; color: {theme.TEXT_SECONDARY};"
            f"border: 1px solid {theme.BORDER}; border-radius: 6px; font-weight: 600; padding: 0;"
        )
        boton_colapsar.clicked.connect(self._alternar_colapso)
        self._boton_colapsar = boton_colapsar

        fila.addWidget(self._lbl_titulo)
        fila.addStretch()
        fila.addWidget(boton_colapsar)
        return fila

    def _estilo_boton(self) -> str:
        return f"""
            QPushButton {{
                text-align: left; background-color: transparent; color: {theme.TEXT_ON_SIDEBAR};
                border: none; border-radius: 8px; padding: 9px 14px; margin: 0 8px; font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {theme.BG_SIDEBAR_HOVER}; }}
            QPushButton:checked {{
                background-color: {theme.BG_SIDEBAR_ACTIVE}; color: {theme.TEXT_ON_SIDEBAR_ACTIVE};
            }}
        """

    def _alternar_colapso(self) -> None:
        self._colapsado = not self._colapsado
        self.setFixedWidth(ANCHO_COLAPSADO if self._colapsado else ANCHO_EXPANDIDO)
        self._boton_colapsar.setText("»" if self._colapsado else "«")
        self._actualizar_textos()

    def _actualizar_textos(self) -> None:
        self._lbl_titulo.setVisible(not self._colapsado)
        self._boton_cerrar_sesion.setText("🚪" if self._colapsado else "🚪  Cerrar sesión")
        self._boton_cerrar_sesion.setToolTip("Cerrar sesión" if self._colapsado else "")
        self._lbl_pie.setVisible(not self._colapsado)
        self._lbl_pie.setText(f"{self._nombre_usuario}\n{self._rol.capitalize()}")

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