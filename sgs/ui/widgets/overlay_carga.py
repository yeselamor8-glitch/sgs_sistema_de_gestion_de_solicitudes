from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from sgs.ui import theme


class OverlayCarga(QWidget):
    """Capa de carga semitransparente que se superpone a un widget mientras
    corre una operación pesada. Muestra una barra indeterminada y un mensaje.

    Se mantiene sincronizada con el tamaño del padre (sigue sus resize) y se
    coloca por encima del contenido.
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("overlayCarga")
        self.setStyleSheet(
            f"#overlayCarga {{ background-color: rgba(26, 26, 26, 0.35); }}"
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjetaCarga")
        tarjeta.setStyleSheet(
            f"""
            #tarjetaCarga {{
                background-color: {theme.COLORES['surface']};
                border: 1px solid {theme.COLORES['outline']};
                border-radius: {theme.BORDES['lg']}px;
            }}
            """
        )
        tarjeta.setFixedWidth(300)
        tarjeta_layout = QVBoxLayout(tarjeta)
        tarjeta_layout.setContentsMargins(24, 22, 24, 22)
        tarjeta_layout.setSpacing(14)

        self._lbl_mensaje = QLabel("Procesando…")
        self._lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_mensaje.setWordWrap(True)
        self._lbl_mensaje.setStyleSheet(
            f"color: {theme.COLORES['on_surface']}; font-size: 14px; font-weight: 600; background: transparent;"
        )

        self._barra = QProgressBar()
        self._barra.setRange(0, 0)  # indeterminada
        self._barra.setTextVisible(False)
        self._barra.setFixedHeight(6)
        self._barra.setStyleSheet(
            f"""
            QProgressBar {{ background-color: {theme.COLORES['outline_variant']}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {theme.COLORES['primary']}; border-radius: 3px; }}
            """
        )

        sub = QLabel("Esto puede tardar con archivos grandes. La ventana seguirá disponible.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {theme.COLORES['on_surface_var']}; font-size: 11px; background: transparent;")

        tarjeta_layout.addWidget(self._lbl_mensaje)
        tarjeta_layout.addWidget(self._barra)
        tarjeta_layout.addWidget(sub)

        layout.addWidget(tarjeta)

        parent.installEventFilter(self)
        self.hide()

    # ------------------------------------------------------------------
    def mostrar(self, mensaje: str = "Procesando…") -> None:
        self._lbl_mensaje.setText(mensaje)
        self._ajustar_al_padre()
        self.raise_()
        self.show()

    def ocultar(self) -> None:
        self.hide()

    # ------------------------------------------------------------------
    def _ajustar_al_padre(self) -> None:
        if self.parent() is not None:
            self.setGeometry(self.parentWidget().rect())

    def eventFilter(self, obj, evento):  # noqa: N802 (API de Qt)
        if obj is self.parent() and evento.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._ajustar_al_padre()
        return super().eventFilter(obj, evento)
