from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from sgs.ui import theme


class SectionCard(QFrame):
    """Tarjeta de sección con título + grilla de campos etiqueta/valor.
    Toda la información visible directamente, sin acordeones (sección
    11 / 33 del documento funcional).

    `protegida=True` da un tratamiento visual distinto (fondo gris +
    ícono de candado) para las secciones Nivel 3 (solo lectura, vienen
    de SAC o son calculadas). Las secciones editables (Nivel 1) usan
    el estilo normal — sin marca especial, porque son la mayoría."""

    def __init__(self, titulo: str, columnas: int = 2, protegida: bool = False):
        super().__init__()
        color_fondo = theme.BG_APP if protegida else theme.BG_CARD
        self.setStyleSheet(f"QFrame {{ background-color: {color_fondo}; border-radius: 10px; }}")
        self._columnas = columnas
        self._fila_actual = 0
        self._col_actual = 0

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(10)

        titulo_texto = f"🔒  {titulo}" if protegida else titulo
        lbl_titulo = QLabel(titulo_texto)
        color_texto = theme.TEXT_SECONDARY if protegida else theme.TEXT_PRIMARY
        lbl_titulo.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {color_texto};")
        self._layout.addWidget(lbl_titulo)

        self._grilla = QGridLayout()
        self._grilla.setHorizontalSpacing(28)
        self._grilla.setVerticalSpacing(10)
        for c in range(columnas):
            self._grilla.setColumnStretch(c, 1)
        self._layout.addLayout(self._grilla)

    def agregar_campo(self, etiqueta: str, valor: str, ancho_completo: bool = False) -> QLabel:
        contenedor = QWidget()
        v = QVBoxLayout(contenedor)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        lbl_etiqueta = QLabel(etiqueta)
        lbl_etiqueta.setProperty("role", "secondary")
        lbl_valor = QLabel(_texto_valor(valor))
        lbl_valor.setWordWrap(True)
        lbl_valor.setStyleSheet("font-size: 13px;")

        v.addWidget(lbl_etiqueta)
        v.addWidget(lbl_valor)

        if ancho_completo:
            self._grilla.addWidget(contenedor, self._fila_actual, 0, 1, self._columnas)
            self._fila_actual += 1
            self._col_actual = 0
            return lbl_valor

        self._grilla.addWidget(contenedor, self._fila_actual, self._col_actual)
        self._col_actual += 1
        if self._col_actual >= self._columnas:
            self._col_actual = 0
            self._fila_actual += 1
        return lbl_valor

    def agregar_campo_editable(self, etiqueta: str, widget: QWidget, ancho_completo: bool = False) -> None:
        contenedor = QWidget()
        v = QVBoxLayout(contenedor)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        lbl_etiqueta = QLabel(etiqueta)
        lbl_etiqueta.setProperty("role", "secondary")
        v.addWidget(lbl_etiqueta)
        v.addWidget(widget)

        if ancho_completo:
            self._grilla.addWidget(contenedor, self._fila_actual, 0, 1, self._columnas)
            self._fila_actual += 1
            self._col_actual = 0
            return

        self._grilla.addWidget(contenedor, self._fila_actual, self._col_actual)
        self._col_actual += 1
        if self._col_actual >= self._columnas:
            self._col_actual = 0
            self._fila_actual += 1

    def agregar_widget_ancho_completo(self, widget: QWidget) -> None:
        if self._col_actual != 0:
            self._fila_actual += 1
            self._col_actual = 0
        self._grilla.addWidget(widget, self._fila_actual, 0, 1, self._columnas)
        self._fila_actual += 1


def _texto_valor(valor) -> str:
    """Normaliza el valor de un campo a texto para el QLabel.

    `agregar_campo` recibe a veces valores numéricos (p. ej. 'Días
    restantes', que la capa de aplicación entrega como int) — QLabel solo
    acepta str, así que hay que convertir siempre. Se muestra '—' cuando el
    valor es None o una cadena vacía; el 0 SÍ se muestra (para 'Días
    restantes' significa 'vence hoy', que es información válida)."""
    if valor is None:
        return "—"
    if isinstance(valor, str):
        return valor if valor.strip() else "—"
    return str(valor)