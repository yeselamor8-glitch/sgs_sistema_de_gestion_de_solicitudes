from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout

from sgs.ui import theme

ETIQUETAS = {"VERDE": "En tiempo", "AMARILLO": "Próxima a vencer", "ROJO": "Vencida"}


class SemaforoBadge(QWidget):
    """Punto de color + texto. Se usa igual en Dashboard, Solicitudes y Detalle
    — es la ÚNICA implementación visual de semaforización en toda la app."""

    def __init__(self, color: str, mostrar_texto: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        fg, bg = theme.SEMAFORO_COLORES.get(color, theme.SEMAFORO_COLORES["VERDE"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 10, 3)
        layout.setSpacing(6)

        punto = QLabel("●")
        punto.setStyleSheet(f"color: {fg}; font-size: 10px;")
        layout.addWidget(punto)

        if mostrar_texto:
            texto = QLabel(ETIQUETAS.get(color, color))
            texto.setStyleSheet(f"color: {fg}; font-weight: 500; font-size: 12px;")
            layout.addWidget(texto)

        self.setStyleSheet(f"background-color: {bg}; border-radius: 10px;")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
