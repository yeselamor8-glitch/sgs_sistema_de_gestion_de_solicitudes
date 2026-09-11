from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class MetricCard(QFrame):
    def __init__(self, titulo: str, valor: str, color_texto: str = "#1A1D23", color_fondo: str = "#FFFFFF"):
        super().__init__()
        self.setStyleSheet(
            f"QFrame {{ background-color: {color_fondo}; border-radius: 10px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet(f"color: {color_texto}; font-size: 12px;")
        lbl_valor = QLabel(valor)
        lbl_valor.setStyleSheet(f"color: {color_texto}; font-size: 24px; font-weight: 600;")

        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_valor)
