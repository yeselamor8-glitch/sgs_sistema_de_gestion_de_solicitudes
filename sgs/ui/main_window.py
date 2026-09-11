from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sgs.ui.pages.configuracion import ConfiguracionPage
from sgs.ui.pages.dashboard_admin import DashboardAdminPage
from sgs.ui.pages.detalle_solicitud import DetalleSolicitudPage
from sgs.ui.pages.herramientas import HerramientasPage
from sgs.ui.pages.importar_sac import ImportarSacPage
from sgs.ui.pages.reportes import ReportesPage
from sgs.ui.pages.solicitudes import SolicitudesPage
from sgs.ui.widgets.sidebar import Sidebar

TITULOS_PAGINA = {
    "dashboard": "Dashboard",
    "solicitudes": "Solicitudes",
    "mis_solicitudes": "Mis solicitudes",
    "importar_sac": "Importar SAC",
    "reportes": "Reportes",
    "herramientas": "Herramientas",
    "configuracion": "Configuración",
    "auditoria": "Auditoría",
}


def usuario_tiene_permiso(usuario_id: int | None, nombre_permiso: str) -> bool:
    if usuario_id is None:
        return False
    try:
        from sgs.app.casos_de_uso import usuario_tiene_permiso as _usuario_tiene_permiso

        return bool(_usuario_tiene_permiso(usuario_id, nombre_permiso))
    except Exception:
        return False


class MainWindow(QMainWindow):
    logout_solicitado = Signal()

    """
    Ventana raíz post-login. La campana de notificaciones vive en el
    encabezado (no en el sidebar, ver sección 28 del documento
    funcional) — aquí solo el contador; el panel desplegable se
    implementa en la siguiente iteración de esta fase.
    """

    def __init__(self, rol: str, nombre_usuario: str, usuario_id: int | None = None):
        super().__init__()
        self.setWindowTitle("Sistema de Gestión de Solicitudes")
        self.resize(1200, 760)
        self._usuario_id = usuario_id
        self._tiene_permiso_importar_sac = rol == "ADMINISTRADOR" or usuario_tiene_permiso(
            usuario_id, "importar_sac"
        )

        contenedor = QWidget()
        layout_raiz = QHBoxLayout(contenedor)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        self.sidebar = Sidebar(
            rol=rol,
            nombre_usuario=nombre_usuario,
            tiene_permiso_importar_sac=self._tiene_permiso_importar_sac,
        )
        self.sidebar.pagina_seleccionada.connect(self._cambiar_pagina)
        self.sidebar.cerrar_sesion.connect(self._solicitar_logout)
        layout_raiz.addWidget(self.sidebar)

        columna_derecha = QWidget()
        col_layout = QVBoxLayout(columna_derecha)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(0)

        col_layout.addWidget(self._encabezado())

        self.stack = QStackedWidget()
        self._paginas: dict[str, QWidget] = {}
        self._registrar_pagina("dashboard", DashboardAdminPage(self._usuario_id, rol))

        clave_solicitudes = "solicitudes" if rol == "ADMINISTRADOR" else "mis_solicitudes"
        titulo_solicitudes = "Solicitudes" if rol == "ADMINISTRADOR" else "Mis solicitudes"
        pagina_solicitudes = SolicitudesPage(titulo=titulo_solicitudes, usuario_id=self._usuario_id, rol=rol)
        pagina_solicitudes.solicitud_seleccionada.connect(self._abrir_detalle_solicitud)
        self._registrar_pagina(clave_solicitudes, pagina_solicitudes)

        if self._tiene_permiso_importar_sac:
            pagina_importar = ImportarSacPage(usuario_id=self._usuario_id)
            pagina_importar.importacion_completada.connect(self._ir_al_dashboard)
            self._registrar_pagina("importar_sac", pagina_importar)
        self._registrar_pagina("reportes", ReportesPage())
        self._registrar_pagina("herramientas", HerramientasPage())
        if rol == "ADMINISTRADOR":
            self._registrar_pagina("configuracion", ConfiguracionPage())

        # Auditoría se agrega con el mismo patrón `_registrar_pagina`
        # en la siguiente iteración.
        col_layout.addWidget(self.stack)

        layout_raiz.addWidget(columna_derecha, stretch=1)
        self.setCentralWidget(contenedor)

    def _registrar_pagina(self, clave: str, widget: QWidget) -> None:
        self._paginas[clave] = widget
        self.stack.addWidget(widget)

    def _encabezado(self) -> QWidget:
        barra = QWidget()
        barra.setFixedHeight(52)
        barra.setStyleSheet("background-color: transparent; border-bottom: 1px solid #E3E5E9;")
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(24, 0, 24, 0)

        self.lbl_titulo_pagina = QLabel("Dashboard")
        self.lbl_titulo_pagina.setStyleSheet("font-weight: 600; font-size: 14px;")
        layout.addWidget(self.lbl_titulo_pagina)
        layout.addStretch()

        campana = QLabel("🔔 3")  # placeholder — conectar a notificaciones no leídas
        campana.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(campana)

        return barra

    def _cambiar_pagina(self, clave: str) -> None:
        if clave not in self._paginas:
            return  # página aún no implementada en esta iteración
        self.stack.setCurrentWidget(self._paginas[clave])
        self.lbl_titulo_pagina.setText(TITULOS_PAGINA.get(clave, clave))

    def _abrir_detalle_solicitud(self, numero_solicitud_sac: str) -> None:
        clave = "detalle_solicitud"
        if clave in self._paginas:
            widget_anterior = self._paginas.pop(clave)
            self.stack.removeWidget(widget_anterior)
            widget_anterior.deleteLater()

        pagina = DetalleSolicitudPage(numero_solicitud_sac)
        pagina.volver_solicitado.connect(self._volver_a_solicitudes)
        self._registrar_pagina(clave, pagina)
        self.stack.setCurrentWidget(pagina)
        self.lbl_titulo_pagina.setText(f"Detalle · {numero_solicitud_sac}")

    def _volver_a_solicitudes(self) -> None:
        clave = "solicitudes" if "solicitudes" in self._paginas else "mis_solicitudes"
        self._cambiar_pagina(clave)
        # también refleja la selección en el sidebar
        boton = self.sidebar._botones.get(clave)
        if boton:
            boton.setChecked(True)

    def _solicitar_logout(self) -> None:
        self.logout_solicitado.emit()

    def _ir_al_dashboard(self) -> None:
        self._cambiar_pagina("dashboard")
        boton = self.sidebar._botones.get("dashboard")
        if boton:
            boton.setChecked(True)