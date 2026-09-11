from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from sgs.ui import theme

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
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._labels: list[QLabel] = []
        for i, paso in enumerate(PASOS):
            lbl = QLabel(f"{i + 1}. {paso}")
            lbl.setStyleSheet(self._estilo(activo=False, hecho=False))
            self._layout.addWidget(lbl)
            self._labels.append(lbl)
            if i < len(PASOS) - 1:
                separador = QLabel("→")
                separador.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
                self._layout.addWidget(separador)
        self._layout.addStretch()
        self.marcar_paso(0)

    def marcar_paso(self, indice_activo: int) -> None:
        for i, lbl in enumerate(self._labels):
            lbl.setStyleSheet(self._estilo(activo=(i == indice_activo), hecho=(i < indice_activo)))

    @staticmethod
    def _estilo(activo: bool, hecho: bool) -> str:
        if activo:
            return f"background-color: {theme.ACCENT_LIGHT}; color: {theme.ACCENT}; border-radius: 8px; padding: 5px 10px; font-weight: 600;"
        if hecho:
            return f"color: {theme.SEMAFORO_VERDE}; padding: 5px 10px; font-weight: 500;"
        return f"color: {theme.TEXT_SECONDARY}; padding: 5px 10px;"