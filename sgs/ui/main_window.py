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
        self._rol = rol
        self._nombre_usuario = nombre_usuario
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
        self._registrar_pagina("reportes", ReportesPage(usuario_id=self._usuario_id, rol=rol))
        self._registrar_pagina("herramientas", HerramientasPage())
        if rol == "ADMINISTRADOR":
            pagina_configuracion = ConfiguracionPage()
            pagina_configuracion.permisos_cambiados.connect(self.refrescar_acceso_importar_sac)
            self._registrar_pagina("configuracion", pagina_configuracion)

            from sgs.ui.pages.auditoria import AuditoriaPage
            self._registrar_pagina("auditoria", AuditoriaPage())

        col_layout.addWidget(self.stack)

        layout_raiz.addWidget(columna_derecha, stretch=1)
        self.setCentralWidget(contenedor)

    def _registrar_pagina(self, clave: str, widget: QWidget) -> None:
        self._paginas[clave] = widget
        self.stack.addWidget(widget)

    def _encabezado(self) -> QWidget:
        barra = QWidget()
        barra.setFixedHeight(58)
        barra.setStyleSheet(
            "background-color: #FFFFFF; border-bottom: 1px solid #E2E8F0;"
        )
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(10)

        # Migas de pan / indicador de sección
        badge_sgs = QLabel("SGS")
        badge_sgs.setStyleSheet(
            "background-color: #E0F2FE; color: #0284C7; font-weight: 800; "
            "font-size: 11px; padding: 3px 8px; border-radius: 6px;"
        )
        layout.addWidget(badge_sgs)

        separador_miga = QLabel("/")
        separador_miga.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 500;")
        layout.addWidget(separador_miga)

        self.lbl_titulo_pagina = QLabel("Dashboard")
        self.lbl_titulo_pagina.setStyleSheet("font-weight: 700; font-size: 15px; color: #0F172A;")
        layout.addWidget(self.lbl_titulo_pagina)
        layout.addStretch()

        # Pastilla de usuario y rol
        user_chip = QWidget()
        user_chip.setStyleSheet("background: transparent; border: none;")
        user_layout = QHBoxLayout(user_chip)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(8)

        lbl_nombre = QLabel(self._nombre_usuario)
        lbl_nombre.setStyleSheet("font-weight: 600; font-size: 13px; color: #1E293B;")
        user_layout.addWidget(lbl_nombre)

        color_rol_bg = "#E0F2FE" if self._rol == "ADMINISTRADOR" else "#DCFCE7"
        color_rol_fg = "#0369A1" if self._rol == "ADMINISTRADOR" else "#15803D"
        lbl_rol = QLabel(self._rol.capitalize())
        lbl_rol.setStyleSheet(
            f"background-color: {color_rol_bg}; color: {color_rol_fg}; "
            "font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px;"
        )
        user_layout.addWidget(lbl_rol)
        layout.addWidget(user_chip)

        # Separador vertical
        from PySide6.QtWidgets import QFrame
        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.Shape.VLine)
        sep_v.setFixedHeight(22)
        sep_v.setStyleSheet("background-color: #E2E8F0; border: none; margin: 0 4px;")
        layout.addWidget(sep_v)

        from sgs.ui.widgets.campana_notificaciones import CampanaNotificaciones

        self.campana = CampanaNotificaciones(self._usuario_id, self._rol)
        layout.addWidget(self.campana)

        return barra

    def refrescar_acceso_importar_sac(self) -> None:
        """Re-evalúa el permiso al momento (señal desde Configuración) y
        agrega/quita la página y el ítem del sidebar en vivo."""
        tiene = self._rol == "ADMINISTRADOR" or usuario_tiene_permiso(
            self._usuario_id, "importar_sac"
        )
        if tiene == self._tiene_permiso_importar_sac:
            return
        self._tiene_permiso_importar_sac = tiene
        self.sidebar.actualizar_permiso_importar_sac(tiene)

        clave = "importar_sac"
        if tiene and clave not in self._paginas:
            pagina_importar = ImportarSacPage(usuario_id=self._usuario_id)
            pagina_importar.importacion_completada.connect(self._ir_al_dashboard)
            self._registrar_pagina(clave, pagina_importar)
        elif not tiene and clave in self._paginas:
            widget_anterior = self._paginas.pop(clave)
            self.stack.removeWidget(widget_anterior)
            widget_anterior.deleteLater()
            if self.stack.currentWidget() is None or self.stack.currentWidget() is widget_anterior:
                self._cambiar_pagina("solicitudes" if "solicitudes" in self._paginas else "mis_solicitudes")

    def _cambiar_pagina(self, clave: str) -> None:
        if clave not in self._paginas:
            return  # página aún no implementada en esta iteración
        widget = self._paginas[clave]
        self.stack.setCurrentWidget(widget)
        self.lbl_titulo_pagina.setText(TITULOS_PAGINA.get(clave, clave))
        self.sidebar.seleccionar_sin_emitir(clave)
        al_mostrar = getattr(widget, "al_mostrar", None)
        if callable(al_mostrar):
            al_mostrar()

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