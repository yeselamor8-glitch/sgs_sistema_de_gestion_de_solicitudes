from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout

from sgs.ui import theme

ETIQUETAS = {
    "A_TIEMPO": "A tiempo",
    "CERCA_DE_VENCIMIENTO": "Cerca de vencimiento",
    "VENCIDO": "Vencida",
    "COMPLETADO": "Completada",
    "SIN_FECHA": "Sin fechas",
}


class SemaforoBadge(QWidget):
    """Punto de color + texto. Se usa igual en Dashboard, Solicitudes y Detalle
    — es la ÚNICA implementación visual de semaforización en toda la app."""

    def __init__(self, color: str, mostrar_texto: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self._texto_label: QLabel | None = None
        self._punto_label = QLabel("●")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 8, 2)
        layout.setSpacing(5)

        self._punto_label.setStyleSheet("font-size: 10px; background: transparent;")
        layout.addWidget(self._punto_label)

        if mostrar_texto:
            self._texto_label = QLabel()
            self._texto_label.setStyleSheet("font-weight: 600; font-size: 11px; background: transparent;")
            layout.addWidget(self._texto_label)

        self._color_actual: str | None = None
        self.cambiar_color(color)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def cambiar_color(self, color: str) -> None:
        """Actualiza estado visual (color, texto y fondo) sin recrear el widget —
        permite refrescar en vivo el semáforo (ej. traslado recién elegido)."""
        fg, bg = theme.SEMAFORO_COLORES.get(
            color, theme.SEMAFORO_COLORES.get("SIN_FECHA", ("#64748B", "#F1F5F9"))
        )
        self._color_actual = color
        self._punto_label.setStyleSheet(f"color: {fg}; font-size: 10px; background: transparent;")
        if self._texto_label is not None:
            self._texto_label.setText(ETIQUETAS.get(color, color))
            self._texto_label.setStyleSheet(f"color: {fg}; font-weight: 600; font-size: 11px; background: transparent;")
        self.setStyleSheet(f"background-color: {bg}; border-radius: 9px; border: 1px solid {bg};")

