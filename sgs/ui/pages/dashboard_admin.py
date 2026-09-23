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


class DashboardAdminPage(QWidget):
    """
    Consume el dashboard mediante la capa de aplicación y no importa
    repositorios ni modelos directamente.
    """

    def __init__(self, usuario_id: int | None = None, rol: str = "ADMINISTRADOR"):
        super().__init__()
        self._usuario_id = usuario_id
        self._rol = rol
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
        self._fila_inferior = fila_inferior
        layout.addLayout(fila_inferior)

        layout.addStretch()
        contenedor.setWidget(cuerpo)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.addWidget(contenedor)

    def al_mostrar(self) -> None:
        """Re-consulta al mostrar la página — el semáforo se calcula contra
        la fecha actual, así que el dashboard siempre refleja el 'hoy'."""
        self._datos, self._error = self._cargar_datos(self._usuario_id, self._rol)
        claves = ("total", "en_tiempo", "proximas_vencer", "vencidas")
        for tarjeta, clave in zip(self._tarjetas, claves):
            tarjeta.set_valor(str(self._datos.get(clave, 0)))
        self._repoblar_paneles()

    def _repoblar_paneles(self) -> None:
        while self._fila_inferior.count():
            item = self._fila_inferior.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self._fila_inferior.removeWidget(widget)
                widget.deleteLater()
        self._fila_inferior.addWidget(self._panel_atencion_prioritaria(), stretch=13)
        self._fila_inferior.addWidget(self._panel_por_proceso(), stretch=10)

    def _encabezado(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        col_titulos = QVBoxLayout()
        col_titulos.setSpacing(2)
        titulo = QLabel("Panel de control")
        titulo.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A; letter-spacing: -0.3px;")
        sub = QLabel("Monitoreo en tiempo real de términos legales y oportunidad de respuesta")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        col_titulos.addWidget(titulo)
        col_titulos.addWidget(sub)
        fila.addLayout(col_titulos)
        fila.addStretch()
        return fila

    def _tarjetas_metricas(self) -> QGridLayout:
        datos = self._datos
        grilla = QGridLayout()
        grilla.setSpacing(12)

        tarjetas = [
            MetricCard("Total solicitudes", str(datos["total"]), "#0082C8", "#FFFFFF", "En gestión activa"),
            MetricCard("En tiempo", str(datos["en_tiempo"]), "#16A34A", "#F0FDF4", "Dentro del plazo"),
            MetricCard("Próximas a vencer", str(datos["proximas_vencer"]), "#D97706", "#FFFBEB", "Atención prioritaria"),
            MetricCard("Vencidas", str(datos["vencidas"]), "#DC2626", "#FEF2F2", "Término superado"),
        ]
        for i, tarjeta in enumerate(tarjetas):
            grilla.addWidget(tarjeta, 0, i)
        self._tarjetas = tarjetas
        return grilla

    _COLOR_PUNTO = {
        "VENCIDO": theme.COLORES_SEMAFORO["ROJO"],
        "CERCA_DE_VENCIMIENTO": theme.COLORES_SEMAFORO["AMARILLO"],
        "A_TIEMPO": theme.COLORES_SEMAFORO["VERDE"],
        "COMPLETADO": theme.COLORES_SEMAFORO["VERDE"],
        "SIN_FECHA": theme.COLORES_SEMAFORO["GRIS"],
    }

    def _panel_atencion_prioritaria(self) -> QFrame:
        panel = self._panel_base("Atención prioritaria")
        layout = panel.layout()
        prioritarias = self._datos.get("atencion_prioritaria", [])
        if not prioritarias:
            vacio = QLabel("Sin solicitudes prioritarias por ahora.")
            vacio.setProperty("role", "secondary")
            layout.addWidget(vacio)
            return panel
        for numero, proceso, color, detalle in prioritarias:
            fila = QFrame()
            fila.setObjectName("filaPrioritaria")
            fila.setStyleSheet(
                """
                QFrame#filaPrioritaria {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
                QFrame#filaPrioritaria:hover {
                    background-color: #F0F9FF;
                    border-color: #BAE6FD;
                }
                QFrame#filaPrioritaria QLabel {
                    border: none;
                }
                """
            )
            fila_layout = QHBoxLayout(fila)
            fila_layout.setContentsMargins(14, 10, 14, 10)
            fila_layout.setSpacing(10)
            fila_layout.addWidget(self._punto_color(color))
            texto = QLabel(f"<b>{numero}</b> · <span style='color: #475569;'>{proceso}</span>")
            texto.setStyleSheet("font-size: 13px; color: #0F172A; border: none;")
            fila_layout.addWidget(texto)
            fila_layout.addStretch()
            lbl_detalle = QLabel(detalle)
            lbl_detalle.setStyleSheet(
                "background-color: #FEF2F2; color: #DC2626; font-size: 11px; "
                "font-weight: 600; padding: 3px 8px; border-radius: 6px; border: none;"
            )
            fila_layout.addWidget(lbl_detalle)
            layout.addWidget(fila)
        return panel

    def _punto_color(self, semaforo: str) -> QLabel:
        color = self._COLOR_PUNTO.get(semaforo, theme.COLORES_SEMAFORO["GRIS"])
        punto = QLabel()
        punto.setFixedSize(12, 12)
        punto.setStyleSheet(f"background-color: {color}; border-radius: 6px; border: none;")
        return punto

    def _panel_por_proceso(self) -> QFrame:
        panel = self._panel_base("Solicitudes por proceso")
        layout = panel.layout()
        por_proceso = self._datos.get("por_proceso", [])
        if not por_proceso:
            vacio = QLabel("Sin datos por proceso.")
            vacio.setProperty("role", "secondary")
            layout.addWidget(vacio)
            return panel
        for nombre, total, porcentaje in por_proceso:
            fila_titulo = QHBoxLayout()
            lbl_nombre = QLabel(nombre)
            lbl_nombre.setStyleSheet("font-size: 13px; font-weight: 500; color: #1E293B; border: none;")
            fila_titulo.addWidget(lbl_nombre)
            fila_titulo.addStretch()
            lbl_total = QLabel(f"{total}  ({int(porcentaje)}%)")
            lbl_total.setStyleSheet(
                "font-size: 12px; font-weight: 700; color: #0369A1; "
                "background-color: #E0F2FE; padding: 2px 8px; border-radius: 6px; border: none;"
            )
            fila_titulo.addWidget(lbl_total)
            layout.addLayout(fila_titulo)

            barra_fondo = QFrame()
            barra_fondo.setFixedHeight(6)
            barra_fondo.setStyleSheet("background-color: #F1F5F9; border-radius: 3px; border: none;")
            barra_layout = QHBoxLayout(barra_fondo)
            barra_layout.setContentsMargins(0, 0, 0, 0)
            barra_rellena = QFrame()
            barra_rellena.setFixedHeight(6)
            barra_rellena.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38BDF8, stop:1 #0082C8); "
                "border-radius: 3px; border: none;"
            )
            pct = max(0, min(100, int(porcentaje)))
            barra_layout.addWidget(barra_rellena, stretch=pct)
            barra_layout.addStretch(100 - pct)
            layout.addWidget(barra_fondo)
            layout.addSpacing(6)
        return panel

    def _panel_base(self, titulo: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panelBase")
        panel.setStyleSheet(
            """
            QFrame#panelBase {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
            QFrame#panelBase QLabel {
                border: none;
            }
            """
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        lbl = QLabel(titulo)
        lbl.setStyleSheet("font-weight: 700; font-size: 15px; color: #0F172A; border: none;")
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
