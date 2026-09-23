from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

PASOS = [
    "Seleccionar archivo",
    "Validar estructura",
    "Vista previa",
    "Clasificar y duplicados",
    "Resumen y confirmar",
]


class IndicadorPasos(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 4, 0, 8)
        self._layout.setSpacing(8)
        self._labels: list[QLabel] = []
        for i, paso in enumerate(PASOS):
            lbl = QLabel(f"{i + 1}. {paso}")
            lbl.setStyleSheet(self._estilo(activo=False, hecho=False))
            self._layout.addWidget(lbl)
            self._labels.append(lbl)
            if i < len(PASOS) - 1:
                separador = QLabel("→")
                separador.setStyleSheet("color: #CBD5E1; font-size: 14px; font-weight: 700;")
                self._layout.addWidget(separador)
        self._layout.addStretch()
        self.marcar_paso(0)

    def marcar_paso(self, indice_activo: int) -> None:
        for i, lbl in enumerate(self._labels):
            lbl.setStyleSheet(self._estilo(activo=(i == indice_activo), hecho=(i < indice_activo)))

    @staticmethod
    def _estilo(activo: bool, hecho: bool) -> str:
        if activo:
            return (
                "background-color: #E0F2FE; color: #0284C7; border: 1px solid #BAE6FD; "
                "border-radius: 8px; padding: 6px 14px; font-weight: 700; font-size: 12px;"
            )
        if hecho:
            return (
                "background-color: #DCFCE7; color: #15803D; border: 1px solid #BBF7D0; "
                "border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 12px;"
            )
        return (
            "background-color: #F8FAFC; color: #94A3B8; border: 1px solid #E2E8F0; "
            "border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 500;"
        )