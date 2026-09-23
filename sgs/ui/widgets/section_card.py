from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from sgs.ui import theme
from sgs.ui.assets_loader import assets


class SectionCard(QFrame):
    """Tarjeta de sección con título + grilla de campos etiqueta/valor.
    Toda la información visible directamente, sin acordeones (sección
    11 / 33 del documento funcional).

    `protegida=True` da un tratamiento visual de solo lectura
    (fondo pizarra claro, borde sutil y badge de protección SAC).
    Las secciones editables usan fondo blanco con campos resaltados."""

    def __init__(self, titulo: str, columnas: int = 2, protegida: bool = False):
        super().__init__()
        self.setObjectName("sectionCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        color_fondo = "#F8FAFC" if protegida else "#FFFFFF"
        borde_color = "#E2E8F0"
        self.setStyleSheet(
            f"""
            QFrame#sectionCard {{
                background-color: {color_fondo};
                border: 1px solid {borde_color};
                border-radius: {theme.BORDES['lg']}px;
            }}
            QFrame#sectionCard QLabel {{
                border: none;
            }}
            """
        )

        self._columnas = columnas
        self._fila_actual = 0
        self._col_actual = 0

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 18)
        self._layout.setSpacing(12)

        # Encabezado de la tarjeta
        header_fila = QHBoxLayout()
        header_fila.setSpacing(8)

        lbl_titulo = QLabel(titulo)
        color_texto = "#334155" if protegida else "#0F172A"
        lbl_titulo.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {color_texto}; border: none;")
        header_fila.addWidget(lbl_titulo)
        header_fila.addStretch()

        if protegida:
            badge_prot = QLabel(" Solo lectura · SAC")
            badge_prot.setStyleSheet(
                "background-color: #F1F5F9; color: #475569; font-size: 11px; "
                "font-weight: 600; padding: 3px 8px; border-radius: 6px; border: 1px solid #CBD5E1;"
            )
            qicon_lock = assets.icono("candado")
            if not qicon_lock.isNull():
                badge_prot.setText(" Solo lectura · SAC")
            header_fila.addWidget(badge_prot)
        else:
            badge_edit = QLabel("Editable · Gestión Secretaría")
            badge_edit.setStyleSheet(
                "background-color: #E0F2FE; color: #0369A1; font-size: 11px; "
                "font-weight: 600; padding: 3px 8px; border-radius: 6px; border: 1px solid #BAE6FD;"
            )
            header_fila.addWidget(badge_edit)

        self._layout.addLayout(header_fila)

        # Grilla de campos
        self._grilla = QGridLayout()
        self._grilla.setHorizontalSpacing(24)
        self._grilla.setVerticalSpacing(12)
        for c in range(columnas):
            self._grilla.setColumnStretch(c, 1)
        self._layout.addLayout(self._grilla)

    def agregar_campo(self, etiqueta: str, valor: str, ancho_completo: bool = False) -> QLabel:
        contenedor = QWidget()
        v = QVBoxLayout(contenedor)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)

        lbl_etiqueta = QLabel(etiqueta)
        lbl_etiqueta.setStyleSheet(
            "color: #64748B; font-size: 11px; font-weight: 600; letter-spacing: 0.2px; border: none;"
        )

        lbl_valor = QLabel(_texto_valor(valor))
        lbl_valor.setWordWrap(True)
        lbl_valor.setStyleSheet(
            "font-size: 13px; font-weight: 500; color: #0F172A; border: none;"
        )

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
        v.setSpacing(4)

        lbl_etiqueta = QLabel(etiqueta)
        lbl_etiqueta.setStyleSheet(
            "color: #334155; font-size: 11px; font-weight: 600; letter-spacing: 0.2px; border: none;"
        )
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