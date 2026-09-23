from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from sgs.ui import theme


class MetricCard(QFrame):
    """Tarjeta de métrica moderna (Material Design 3): título arriba,
    valor numérico destacado, subtítulo explicativo, acento superior
    y esquinas redondeadas.

    API estable (usada por dashboard e importar_sac):
        MetricCard(titulo, valor, color_texto=..., color_fondo=..., subtitulo=...)
        .set_valor(valor)
    """

    def __init__(
        self,
        titulo: str,
        valor: str,
        color_texto: str = "#0F172A",
        color_fondo: str = "#FFFFFF",
        subtitulo: str = "",
    ):
        super().__init__()
        self.setObjectName("metricCard")
        self.setMinimumHeight(115)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._color_texto = color_texto
        self._color_fondo = color_fondo

        self.setStyleSheet(
            f"""
            QFrame#metricCard {{
                background-color: {color_fondo};
                border: 1px solid #E2E8F0;
                border-top: 3px solid {color_texto};
                border-radius: {theme.BORDES['lg']}px;
            }}
            QFrame#metricCard:hover {{
                border-color: #CBD5E1;
                border-top: 3px solid {color_texto};
            }}
            QFrame#metricCard QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)

        self._lbl_titulo = QLabel(titulo)
        self._lbl_titulo.setStyleSheet(
            "color: #64748B; font-size: 13px; font-weight: 600; letter-spacing: 0.1px;"
        )

        self._lbl_valor = QLabel(valor)
        self._lbl_valor.setStyleSheet(
            f"color: {color_texto}; font-size: 34px; font-weight: 800; letter-spacing: -0.5px;"
        )

        layout.addWidget(self._lbl_titulo)
        layout.addWidget(self._lbl_valor)

        if subtitulo:
            self._lbl_subtitulo = QLabel(subtitulo)
            self._lbl_subtitulo.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")
            layout.addWidget(self._lbl_subtitulo)
        else:
            self._lbl_subtitulo = None

        layout.addStretch()

    def set_valor(self, valor: str) -> None:
        self._lbl_valor.setText(valor)

    def set_subtitulo(self, texto: str) -> None:
        if self._lbl_subtitulo is not None:
            self._lbl_subtitulo.setText(texto)
