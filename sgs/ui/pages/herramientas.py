from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from sgs.ui import theme


class HerramientasPage(QWidget):
    """
    Punto de extensión para integrar utilidades ya desarrolladas por
    separado (sección 25 del documento funcional). La arquitectura para
    registrarlas ya existe (tabla `herramientas` en el schema), pero
    ninguna utilidad concreta se implementa todavía — queda para una
    siguiente versión.
    """

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        titulo = QLabel("Herramientas")
        titulo.setProperty("role", "title")
        layout.addWidget(titulo)

        mensaje = QLabel("🛠  Próximamente en la siguiente versión.")
        mensaje.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 14px; padding-top: 20px;")
        layout.addWidget(mensaje)

        layout.addStretch()