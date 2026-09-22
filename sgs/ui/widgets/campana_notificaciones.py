from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sgs.ui import theme


class CampanaNotificaciones(QWidget):
    """Icono de campana del encabezado con contador de no leídas. Al hacer
    clic abre el panel de notificaciones acorde al rol del usuario."""

    def __init__(self, usuario_id: int | None, rol: str | None, parent=None):
        super().__init__(parent)
        self._usuario_id = usuario_id
        self._rol = rol

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._boton = QPushButton("🔔")
        self._boton.setProperty("variant", "ghost")
        self._boton.setCursor(Qt.CursorShape.PointingHandCursor)
        self._boton.clicked.connect(self._abrir_panel)
        layout.addWidget(self._boton)

        self.refrescar_contador()

    def refrescar_contador(self) -> None:
        total = 0
        if self._usuario_id is not None:
            try:
                from sgs.app.casos_de_uso import contar_notificaciones_no_leidas

                total = contar_notificaciones_no_leidas(self._usuario_id)
            except Exception:
                total = 0
        if total:
            self._boton.setText(f"🔔  {total}")
            self._boton.setStyleSheet(
                f"QPushButton {{ color: {theme.SEMAFORO_ROJO}; font-weight: 700; "
                f"border: 1px solid {theme.BORDER}; }}"
            )
        else:
            self._boton.setText("🔔")
            self._boton.setStyleSheet("")

    def _abrir_panel(self) -> None:
        panel = PanelNotificaciones(self._usuario_id, self._rol, parent=self)
        panel.exec()
        # al cerrar, las notificaciones se marcaron leídas -> refrescar contador
        self.refrescar_contador()


class _Tarjeta(QFrame):
    """Contenedor blanco con borde redondeado, para agrupar contenido."""

    def __init__(self, borde_izquierdo: str | None = None, fondo: str | None = None, parent=None):
        super().__init__(parent)
        borde = (
            f"border-left: 4px solid {borde_izquierdo};" if borde_izquierdo else ""
        )
        self.setStyleSheet(
            f"""
            _Tarjeta {{
                background-color: {fondo or theme.BG_CARD};
                border: 1px solid {theme.BORDER};
                {borde}
                border-radius: {theme.RADIUS}px;
            }}
            """
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 12)
        self._layout.setSpacing(8)

    def layout_interno(self) -> QVBoxLayout:
        return self._layout


class PanelNotificaciones(QDialog):
    """Panel de notificaciones. El administrador ve las solicitudes de
    cambio pendientes con Aprobar/Rechazar; el funcionario ve las suyas con
    estado y observación. Debajo, el historial de avisos."""

    cambios_resueltos = Signal()

    _ESTADOS = {
        "pendiente": (theme.SEMAFORO_AMARILLO, theme.SEMAFORO_AMARILLO_BG, "Pendiente"),
        "aprobada": (theme.SEMAFORO_VERDE, theme.SEMAFORO_VERDE_BG, "Aprobada"),
        "rechazada": (theme.SEMAFORO_ROJO, theme.SEMAFORO_ROJO_BG, "Rechazada"),
    }

    def __init__(self, usuario_id: int | None, rol: str | None, parent=None):
        super().__init__(parent)
        self._usuario_id = usuario_id
        self._rol = rol
        self.setWindowTitle("Notificaciones")
        self.resize(600, 620)
        self.setStyleSheet(f"QDialog {{ background-color: {theme.BG_APP}; }}")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 18)
        self._layout.setSpacing(14)

        titulo = QLabel("Notificaciones")
        titulo.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {theme.TEXT_PRIMARY};"
        )
        self._layout.addWidget(titulo)

        contenedor = QScrollArea()
        contenedor.setWidgetResizable(True)
        contenedor.setStyleSheet(
            f"QScrollArea {{ background-color: {theme.BG_APP}; border: none; }}"
        )
        self._cuerpo = QWidget()
        self._cuerpo.setStyleSheet(f"background-color: {theme.BG_APP};")
        self._cuerpo_layout = QVBoxLayout(self._cuerpo)
        self._cuerpo_layout.setContentsMargins(0, 0, 0, 0)
        self._cuerpo_layout.setSpacing(12)
        contenedor.setWidget(self._cuerpo)
        self._layout.addWidget(contenedor, stretch=1)

        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.accept)
        self._layout.addWidget(cerrar, alignment=Qt.AlignmentFlag.AlignRight)

        self._poblar()
        self._marcar_leidas()

    # ------------------------------------------------------------------
    def _limpiar_cuerpo(self) -> None:
        while self._cuerpo_layout.count():
            item = self._cuerpo_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _seccion(self, texto: str) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {theme.TEXT_PRIMARY}; margin-top: 4px;"
        )
        return etiqueta

    def _texto_vacio(self, texto: str) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
        return etiqueta

    def _poblar(self) -> None:
        self._limpiar_cuerpo()
        if self._rol == "ADMINISTRADOR":
            self._poblar_admin()
        else:
            self._poblar_funcionario()
        self._poblar_historial()
        self._cuerpo_layout.addStretch()

    # ------------------------------------------------------------------
    # Administrador
    # ------------------------------------------------------------------
    def _poblar_admin(self) -> None:
        try:
            from sgs.app.casos_de_uso import listar_solicitudes_cambio_pendientes

            pendientes = listar_solicitudes_cambio_pendientes()
        except Exception as exc:
            self._cuerpo_layout.addWidget(self._texto_vacio(f"No se pudieron cargar las solicitudes: {exc}"))
            return

        self._cuerpo_layout.addWidget(self._seccion("Solicitudes de cambio pendientes de aprobación"))

        if not pendientes:
            self._cuerpo_layout.addWidget(self._texto_vacio("No hay solicitudes pendientes."))
            return

        for c in pendientes:
            self._cuerpo_layout.addWidget(self._tarjeta_pendiente(c))

    def _tarjeta_pendiente(self, cambio: dict) -> QWidget:
        tarjeta = _Tarjeta(borde_izquierdo=theme.SEMAFORO_AMARILLO)
        layout = tarjeta.layout_interno()

        cabecera = QLabel(
            f"Reasignación de <b>{cambio['numero_solicitud_sac']}</b>"
        )
        cabecera.setTextFormat(Qt.TextFormat.RichText)
        cabecera.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 13px;")
        layout.addWidget(cabecera)

        ruta = QLabel(f"«{cambio['proceso_actual']}»  →  «{cambio['proceso_solicitado']}»")
        ruta.setStyleSheet(f"color: {theme.ACCENT}; font-weight: 600;")
        layout.addWidget(ruta)

        meta = QLabel(f"Solicitado por {cambio['solicitado_por']} · {cambio['creado_en']}")
        meta.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(meta)

        motivo = QLabel(f"Motivo: {cambio['motivo']}")
        motivo.setWordWrap(True)
        motivo.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")
        layout.addWidget(motivo)

        campo_obs = QPlainTextEdit()
        campo_obs.setPlaceholderText("Observación (opcional al aprobar, recomendada al rechazar)")
        campo_obs.setFixedHeight(56)
        campo_obs.setStyleSheet(
            f"QPlainTextEdit {{ background-color: white; color: {theme.TEXT_PRIMARY}; "
            f"border: 1px solid {theme.BORDER}; border-radius: {theme.RADIUS}px; padding: 6px; }}"
        )
        layout.addWidget(campo_obs)

        fila = QHBoxLayout()
        fila.addStretch()
        boton_rechazar = QPushButton("Rechazar")
        boton_rechazar.setProperty("variant", "ghost")
        boton_rechazar.clicked.connect(
            lambda: self._resolver(cambio["id"], False, campo_obs.toPlainText().strip())
        )
        boton_aprobar = QPushButton("Aprobar")
        boton_aprobar.setProperty("variant", "primary")
        boton_aprobar.clicked.connect(
            lambda: self._resolver(cambio["id"], True, campo_obs.toPlainText().strip())
        )
        fila.addWidget(boton_rechazar)
        fila.addWidget(boton_aprobar)
        layout.addLayout(fila)
        return tarjeta

    def _resolver(self, cambio_id: int, aprobada: bool, observacion: str) -> None:
        if not aprobada and not observacion:
            confirmar = QMessageBox.question(
                self, "Rechazar sin observación",
                "¿Rechazar sin escribir un motivo? Es mejor indicar por qué.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirmar != QMessageBox.StandardButton.Yes:
                return
        try:
            from sgs.app.casos_de_uso import resolver_solicitud_cambio

            resolver_solicitud_cambio(cambio_id, aprobada, self._usuario_id, observacion or None)
            self.cambios_resueltos.emit()
            self._poblar()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo resolver", str(exc))

    # ------------------------------------------------------------------
    # Funcionario
    # ------------------------------------------------------------------
    def _poblar_funcionario(self) -> None:
        try:
            from sgs.app.casos_de_uso import listar_mis_solicitudes_cambio

            mias = listar_mis_solicitudes_cambio(self._usuario_id)
        except Exception as exc:
            self._cuerpo_layout.addWidget(self._texto_vacio(f"No se pudieron cargar tus solicitudes: {exc}"))
            return

        self._cuerpo_layout.addWidget(self._seccion("Mis solicitudes de cambio"))

        if not mias:
            self._cuerpo_layout.addWidget(self._texto_vacio("No has enviado solicitudes de cambio."))
            return

        for c in mias:
            self._cuerpo_layout.addWidget(self._tarjeta_mia(c))

    def _tarjeta_mia(self, cambio: dict) -> QWidget:
        color, fondo, etiqueta = self._ESTADOS.get(
            cambio["estado"], (theme.TEXT_SECONDARY, theme.BG_CARD, cambio["estado"])
        )
        tarjeta = _Tarjeta(borde_izquierdo=color)
        layout = tarjeta.layout_interno()

        fila_top = QHBoxLayout()
        titulo = QLabel(f"<b>{cambio['numero_solicitud_sac']}</b>")
        titulo.setTextFormat(Qt.TextFormat.RichText)
        titulo.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 13px;")
        fila_top.addWidget(titulo)
        fila_top.addStretch()

        badge = QLabel(etiqueta)
        badge.setStyleSheet(
            f"background-color: {fondo}; color: {color}; font-weight: 700; "
            f"padding: 2px 10px; border-radius: 8px; font-size: 12px;"
        )
        fila_top.addWidget(badge)
        layout.addLayout(fila_top)

        ruta = QLabel(f"«{cambio['proceso_actual']}»  →  «{cambio['proceso_solicitado']}»")
        ruta.setStyleSheet(f"color: {theme.ACCENT}; font-weight: 600;")
        layout.addWidget(ruta)

        motivo = QLabel(f"Motivo: {cambio['motivo']}")
        motivo.setWordWrap(True)
        motivo.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")
        layout.addWidget(motivo)

        if cambio["observacion_admin"]:
            obs = QLabel(f"Observación del administrador: {cambio['observacion_admin']}")
            obs.setWordWrap(True)
            obs.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
            layout.addWidget(obs)
        return tarjeta

    # ------------------------------------------------------------------
    # Historial de avisos
    # ------------------------------------------------------------------
    def _poblar_historial(self) -> None:
        try:
            from sgs.app.casos_de_uso import listar_notificaciones

            notificaciones = listar_notificaciones(self._usuario_id)
        except Exception:
            notificaciones = []

        if not notificaciones:
            return

        self._cuerpo_layout.addWidget(self._seccion("Avisos recientes"))
        for n in notificaciones:
            tarjeta = _Tarjeta(fondo=(theme.BG_CARD if n["leida"] else theme.ACCENT_LIGHT))
            layout = tarjeta.layout_interno()
            layout.setContentsMargins(14, 10, 14, 10)
            layout.setSpacing(2)

            mensaje = QLabel(n["mensaje"])
            mensaje.setWordWrap(True)
            peso = "600" if not n["leida"] else "400"
            mensaje.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-weight: {peso};")
            layout.addWidget(mensaje)

            fecha = QLabel(n["creado_en"])
            fecha.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px;")
            layout.addWidget(fecha)
            self._cuerpo_layout.addWidget(tarjeta)

    def _marcar_leidas(self) -> None:
        if self._usuario_id is None:
            return
        try:
            from sgs.app.casos_de_uso import marcar_notificaciones_leidas

            marcar_notificaciones_leidas(self._usuario_id)
        except Exception:
            pass
