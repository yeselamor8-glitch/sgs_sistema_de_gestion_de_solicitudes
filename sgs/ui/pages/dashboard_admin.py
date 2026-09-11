from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sgs.ui import theme
from sgs.ui.widgets.metric_card import MetricCard
from sgs.ui.widgets.semaforo_badge import SemaforoBadge


class DashboardAdminPage(QWidget):
    """
    Consume el dashboard mediante la capa de aplicación y no importa
    repositorios ni modelos directamente.
    """

    def __init__(self, usuario_id: int | None = None, rol: str = "ADMINISTRADOR"):
        super().__init__()
        self._datos, self._error = self._cargar_datos(usuario_id, rol)
        contenedor = QScrollArea()
        contenedor.setWidgetResizable(True)
        contenedor.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cuerpo = QWidget()
        layout = QVBoxLayout(cuerpo)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        layout.addLayout(self._encabezado())
        layout.addLayout(self._tarjetas_metricas())
        if self._error:
            aviso = QLabel(self._error)
            aviso.setProperty("role", "secondary")
            layout.addWidget(aviso)

        fila_inferior = QHBoxLayout()
        fila_inferior.setSpacing(12)
        fila_inferior.addWidget(self._panel_atencion_prioritaria(), stretch=13)
        fila_inferior.addWidget(self._panel_por_proceso(), stretch=10)
        layout.addLayout(fila_inferior)

        layout.addStretch()
        contenedor.setWidget(cuerpo)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.addWidget(contenedor)

    def _encabezado(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        titulo = QLabel("Dashboard")
        titulo.setProperty("role", "title")
        fila.addWidget(titulo)
        fila.addStretch()
        return fila

    def _tarjetas_metricas(self) -> QGridLayout:
        datos = self._datos
        grilla = QGridLayout()
        grilla.setSpacing(12)

        tarjetas = [
            MetricCard("Total solicitudes", str(datos["total"])),
            MetricCard("En tiempo", str(datos["en_tiempo"]), theme.SEMAFORO_VERDE, theme.SEMAFORO_VERDE_BG),
            MetricCard(
                "Próximas a vencer", str(datos["proximas_vencer"]), theme.SEMAFORO_AMARILLO, theme.SEMAFORO_AMARILLO_BG
            ),
            MetricCard("Vencidas", str(datos["vencidas"]), theme.SEMAFORO_ROJO, theme.SEMAFORO_ROJO_BG),
        ]
        for i, tarjeta in enumerate(tarjetas):
            grilla.addWidget(tarjeta, 0, i)
        return grilla

    def _panel_atencion_prioritaria(self) -> QFrame:
        panel = self._panel_base("Atención prioritaria")
        layout = panel.layout()
        for numero, proceso, color, detalle in self._datos["atencion_prioritaria"]:
            fila = QFrame()
            fila.setStyleSheet(
                f"background-color: {theme.BG_APP}; border-radius: 8px;"
            )
            fila_layout = QHBoxLayout(fila)
            fila_layout.setContentsMargins(10, 8, 10, 8)
            fila_layout.addWidget(SemaforoBadge(color, mostrar_texto=False))
            fila_layout.addWidget(QLabel(f"{numero} · {proceso}"))
            fila_layout.addStretch()
            lbl_detalle = QLabel(detalle)
            lbl_detalle.setProperty("role", "secondary")
            fila_layout.addWidget(lbl_detalle)
            layout.addWidget(fila)
        return panel

    def _panel_por_proceso(self) -> QFrame:
        panel = self._panel_base("Solicitudes por proceso")
        layout = panel.layout()
        for nombre, total, porcentaje in self._datos["por_proceso"]:
            fila_titulo = QHBoxLayout()
            fila_titulo.addWidget(self._label_secundaria(nombre))
            fila_titulo.addStretch()
            fila_titulo.addWidget(self._label_secundaria(str(total)))
            layout.addLayout(fila_titulo)

            barra_fondo = QFrame()
            barra_fondo.setFixedHeight(6)
            barra_fondo.setStyleSheet(f"background-color: {theme.BG_APP}; border-radius: 3px;")
            barra_layout = QHBoxLayout(barra_fondo)
            barra_layout.setContentsMargins(0, 0, 0, 0)
            barra_rellena = QFrame()
            barra_rellena.setFixedHeight(6)
            barra_rellena.setStyleSheet(f"background-color: {theme.ACCENT}; border-radius: 3px;")
            barra_layout.addWidget(barra_rellena, stretch=porcentaje)
            barra_layout.addStretch(100 - porcentaje)
            layout.addWidget(barra_fondo)
        return panel

    def _panel_base(self, titulo: str) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(f"QFrame {{ background-color: {theme.BG_CARD}; border-radius: 10px; }}")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        lbl = QLabel(titulo)
        lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(lbl)
        return panel

    @staticmethod
    def _label_secundaria(texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setProperty("role", "secondary")
        return lbl

    @staticmethod
    def _cargar_datos(usuario_id: int | None, rol: str) -> tuple[dict, str | None]:
        try:
            from sgs.app.casos_de_uso import obtener_dashboard

            datos = obtener_dashboard(usuario_id, rol)
            return datos, None
        except Exception:
            return {
                "total": 0,
                "en_tiempo": 0,
                "proximas_vencer": 0,
                "vencidas": 0,
                "atencion_prioritaria": [],
                "por_proceso": [],
            }, "No se pudo consultar la base de datos; se muestran datos en cero."
