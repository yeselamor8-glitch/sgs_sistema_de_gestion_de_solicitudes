from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from sgs.ui import theme


class MetricCard(QFrame):
    """Tarjeta de métrica uniforme (Material Design 3): título arriba,
    valor grande abajo, borde sutil y esquinas redondeadas.

    Pinta el fondo con un selector por objectName (#metricCard) + borde,
    lo que Qt respeta de forma consistente incluso con el estilo Fusion.

    API estable (usada por dashboard e importar_sac):
        MetricCard(titulo, valor, color_texto=..., color_fondo=...)
        .set_valor(valor)
    """

    def __init__(
        self,
        titulo: str,
        valor: str,
        color_texto: str = theme.COLORES["on_surface"],
        color_fondo: str = theme.COLORES["surface"],
    ):
        super().__init__()
        self.setObjectName("metricCard")
        self.setMinimumHeight(100)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # Refuerzo: garantiza que el fondo se pinte aunque el estilo activo
        # no honre el selector de clase.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"""
            QFrame#metricCard {{
                background-color: {color_fondo};
                border: 1px solid {theme.COLORES['outline']};
                border-radius: {theme.BORDES['lg']}px;
            }}
            QFrame#metricCard QLabel {{ background: transparent; border: none; }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        self._lbl_titulo = QLabel(titulo)
        self._lbl_titulo.setStyleSheet(
            f"color: {theme.COLORES['on_surface_var']}; font-size: 13px; font-weight: 500;"
        )
        self._lbl_valor = QLabel(valor)
        self._lbl_valor.setStyleSheet(f"color: {color_texto}; font-size: 32px; font-weight: 700;")

        layout.addWidget(self._lbl_titulo)
        layout.addWidget(self._lbl_valor)
        layout.addStretch()

    def set_valor(self, valor: str) -> None:
        self._lbl_valor.setText(valor)
