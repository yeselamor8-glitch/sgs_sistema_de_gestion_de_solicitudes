from __future__ import annotations

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sgs.motores import motor_semaforo
from sgs.ui import theme
from sgs.ui.widgets.campo_fecha import CampoFecha
from sgs.ui.widgets.section_card import SectionCard
from sgs.ui.widgets.semaforo_badge import SemaforoBadge

ESTADOS_GESTION = ["En trámite", "Solucionada"]
ESTADOS_SAC = ["En trámite", "Solucionada"]

# Etiquetas de presentación (maestra): los motores guardan códigos
# (A_TIEMPO, CERRAR_SAC, OPORTUNA, ...) y aquí se muestran en español.
_ETIQUETA_INDICADOR = {
    "A_TIEMPO": "A tiempo",
    "CERCA_DE_VENCIMIENTO": "Cerca de vencimiento",
    "VENCIDO": "Vencido",
    "SIN_FECHA": "Sin fechas",
}
_ETIQUETA_DECISION = {
    "CERRAR_SAC": "Cerrar en SAC",
    "REMITIR_ENTE_CONTROL": "Remitir a ente de control",
    "N_A": "No aplica",
}
_ETIQUETA_OPORTUNIDAD_RESPUESTA = {
    "OPORTUNA": "Oportuna",
    "INOPORTUNA": "Inoportuna",
    "NO_HUBO_RESPUESTA": "No hubo respuesta",
    "INCONSISTENTE": "Inconsistente",
    "N_A": "No aplica",
}


def _etiqueta(mapa: dict[str, str], codigo: str | None) -> str:
    return mapa.get(codigo or "", codigo or "")


class DetalleSolicitudPage(QWidget):
    """
    Pantalla de Detalle de una solicitud (sección 11 del documento
    funcional). Estructura fija por secciones, todas visibles a la
    vez, sin menús desplegables ni acordeones.

    Carga los datos mediante la capa de aplicación y guarda la gestión
    mediante `guardar_gestion_solicitud`.
    """

    volver_solicitado = Signal()

    def __init__(self, numero_solicitud_sac: str):
        super().__init__()
        self.numero_solicitud_sac = numero_solicitud_sac
        try:
            from sgs.app.casos_de_uso import obtener_detalle_solicitud

            self._datos = obtener_detalle_solicitud(numero_solicitud_sac)
            self._error_carga = ""
        except Exception as exc:
            self._datos = self._datos_vacio(numero_solicitud_sac)
            self._error_carga = f"No se pudo cargar la solicitud: {exc}"

        contenedor = QScrollArea()
        contenedor.setWidgetResizable(True)

        cuerpo = QWidget()
        layout = QVBoxLayout(cuerpo)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        layout.addLayout(self._encabezado())
        if self._error_carga:
            aviso = QLabel(self._error_carga)
            aviso.setProperty("role", "secondary")
            layout.addWidget(aviso)
        layout.addWidget(self._seccion_ciudadano())
        layout.addWidget(self._seccion_informacion_sac())
        layout.addWidget(self._seccion_traslado())
        layout.addWidget(self._seccion_tiempos())
        layout.addWidget(self._seccion_respuesta())
        layout.addWidget(self._seccion_ente_control())
        layout.addWidget(self._seccion_gestion())
        layout.addWidget(self._seccion_observaciones())
        layout.addLayout(self._fila_guardar())
        layout.addStretch()

        contenedor.setWidget(cuerpo)
        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.addWidget(contenedor)
        self.campo_fecha_traslado.dateChanged.connect(self._actualizar_preview_traslado)
        self._actualizar_estado_controles()

    # ------------------------------------------------------------------
    def _encabezado(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(14)

        boton_volver = QPushButton("← Volver a solicitudes")
        boton_volver.setProperty("variant", "ghost")
        boton_volver.clicked.connect(self.volver_solicitado.emit)
        fila.addWidget(boton_volver)

        titulo = QLabel(self._datos["numero_solicitud_sac"])
        titulo.setProperty("role", "title")
        fila.addWidget(titulo)

        self.badge_encabezado = SemaforoBadge(self._datos["semaforo"])
        fila.addWidget(self.badge_encabezado)

        lbl_proceso = QLabel(f"{self._datos['proceso']} · {self._datos['funcionario']}")
        lbl_proceso.setProperty("role", "secondary")
        fila.addWidget(lbl_proceso)

        fila.addStretch()
        return fila

    # ------------------------------------------------------------------
    def _seccion_ciudadano(self) -> SectionCard:
        d = self._datos
        card = SectionCard("Datos del ciudadano", columnas=3, protegida=True)
        card.agregar_campo("Tipo y número de documento", f"{d['tipo_documento']} {d['documento']}")
        card.agregar_campo("Nombre", d["nombre_ciudadano"])
        card.agregar_campo("Sexo", d["sexo"])
        card.agregar_campo("Fecha de nacimiento", d["fecha_nacimiento"])
        card.agregar_campo("Edad", str(d["edad"]))
        card.agregar_campo("Teléfono", d["telefono"])
        card.agregar_campo("Correo", d["correo"])
        card.agregar_campo("Municipio de origen", d["municipio_origen"])
        card.agregar_campo("Municipio de residencia", d["municipio_residencia"])
        card.agregar_campo("Población priorizada", d["poblacion_priorizada"])
        card.agregar_campo("Régimen", d["regimen"])
        card.agregar_campo("EPS", d["eps"])
        return card

    def _seccion_informacion_sac(self) -> SectionCard:
        """Bloque SAC — protegido (Nivel 3), solo lectura (sección 13)."""
        d = self._datos
        card = SectionCard("Información SAC · protegida — solo lectura", columnas=3, protegida=True)
        card.agregar_campo("Motivo", d["motivo"])
        card.agregar_campo("Tipo de asunto", d["tipo_asunto"])
        card.agregar_campo("Solicitud", d["solicitud"])
        card.agregar_campo("Subclasificación", d["subclasificacion"])
        card.agregar_campo("Prioridad del caso", d["prioridad_caso"])
        card.agregar_campo("Barrera en el acceso", d["barrera_acceso"])
        card.agregar_campo("Usuario SAC", d["usuario_sac"])
        card.agregar_campo("Fecha de ingreso", d["fecha_ingreso"])
        card.agregar_campo("Detalle", d["detalle"], ancho_completo=True)
        card.agregar_campo("Actuación del funcionario", d["actuacion_funcionario"], ancho_completo=True)
        return card

    def _seccion_traslado(self) -> SectionCard:
        d = self._datos
        card = SectionCard("Traslado a institución competente", columnas=3)

        self.campo_fecha_traslado = self._crear_fecha_edit(d["fecha_traslado"])
        card.agregar_campo_editable("Fecha de traslado", self.campo_fecha_traslado)

        self.campo_institucion_competente = QLineEdit(d["institucion_competente"])
        card.agregar_campo_editable("Institución competente", self.campo_institucion_competente)

        # Calculados por el motor de tiempos — no editables
        self.lbl_oportunidad_traslado = card.agregar_campo(
            "Oportunidad del traslado", f"{d['oportunidad_traslado_dias']} días hábiles"
        )
        self.lbl_indicador_traslado = card.agregar_campo(
            "Indicador de oportunidad", _etiqueta(_ETIQUETA_INDICADOR, d["indicador_oportunidad_traslado"])
        )
        return card

    def _seccion_tiempos(self) -> SectionCard:
        """Tiempos y oportunidades — calculado automáticamente (sección 17)."""
        d = self._datos
        card = SectionCard("Tiempos y oportunidades · calculado automáticamente", columnas=4, protegida=True)
        card.agregar_campo("Fecha de ingreso", d["fecha_ingreso"])
        card.agregar_campo("Fecha de traslado", d["fecha_traslado"])
        self.lbl_fecha_limite = card.agregar_campo("Fecha límite de respuesta", d["fecha_limite"])
        self.lbl_dias_restantes = card.agregar_campo("Días restantes", d["dias_restantes"])
        badge_tiempos = SemaforoBadge(d["semaforo"])
        self.badge_tiempos = badge_tiempos
        card.agregar_widget_ancho_completo(badge_tiempos)
        return card

    def _seccion_respuesta(self) -> SectionCard:
        d = self._datos
        card = SectionCard("Respuesta", columnas=3)

        self.combo_hubo_respuesta = QComboBox()
        self.combo_hubo_respuesta.addItems(["SI", "NO", "N_A"])
        self.combo_hubo_respuesta.setCurrentText(d["hubo_respuesta"])
        self.combo_hubo_respuesta.currentTextChanged.connect(self._actualizar_estado_controles)
        card.agregar_campo_editable("¿Hubo respuesta?", self.combo_hubo_respuesta)

        # Calculado a partir de "¿Hubo respuesta?" — no editable
        self.lbl_decision = card.agregar_campo("Decisión", _etiqueta(_ETIQUETA_DECISION, d["decision"]))

        self.campo_fecha_respuesta = self._crear_fecha_edit(d["fecha_respuesta"])
        card.agregar_campo_editable("Fecha de respuesta", self.campo_fecha_respuesta)

        # Calculado por el motor de tiempos — no editable
        card.agregar_campo(
            "Oportunidad de la respuesta", _etiqueta(_ETIQUETA_OPORTUNIDAD_RESPUESTA, d["oportunidad_respuesta"])
        )

        self.combo_notificacion_usuario = QComboBox()
        self.combo_notificacion_usuario.addItems(["Pendiente", "Enviada"])
        self.combo_notificacion_usuario.setCurrentText(d["notificacion_usuario"])
        card.agregar_campo_editable("Notificación al usuario", self.combo_notificacion_usuario)

        self.campo_respuesta_entidad = QPlainTextEdit(d["respuesta_entidad"])
        self.campo_respuesta_entidad.setFixedHeight(60)
        self.campo_respuesta_entidad.setStyleSheet(self._estilo_textarea())
        card.agregar_campo_editable("Respuesta de la entidad", self.campo_respuesta_entidad, ancho_completo=True)
        return card

    def _seccion_ente_control(self) -> SectionCard:
        """Aquí sí vive el radicado — nunca reemplaza el número de solicitud (sección 16)."""
        d = self._datos
        card = SectionCard("Traslado a ente de control", columnas=3)

        self.campo_radicado = QLineEdit(d["radicado_ente_control"])
        card.agregar_campo_editable("Radicado", self.campo_radicado)

        self.campo_entidad_control = QLineEdit(d["entidad_control"])
        card.agregar_campo_editable("Entidad", self.campo_entidad_control)

        self.campo_fecha_reporte_control = self._crear_fecha_edit(d["fecha_reporte_control"])
        card.agregar_campo_editable("Fecha del reporte", self.campo_fecha_reporte_control)

        self._widgets_ente_control = [
            self.campo_radicado,
            self.campo_entidad_control,
            self.campo_fecha_reporte_control,
        ]
        return card

    def _seccion_gestion(self) -> SectionCard:
        card = SectionCard("Gestión", columnas=1)
        contenedor = QVBoxLayout()
        lbl = QLabel("Estado de gestión")
        lbl.setProperty("role", "secondary")
        self.combo_estado = QComboBox()
        self.combo_estado.addItems(ESTADOS_GESTION)
        if self._datos["estado_gestion"] not in ESTADOS_GESTION and self._datos["estado_gestion"]:
            self.combo_estado.addItem(self._datos["estado_gestion"])
        self.combo_estado.setCurrentText(self._datos["estado_gestion"])
        self.combo_estado.setFixedWidth(200)
        contenedor.addWidget(lbl)
        contenedor.addWidget(self.combo_estado)

        lbl_sac = QLabel("Estado SAC")

        lbl_sac.setProperty("role", "secondary")
        # `estado_sac` es la excepción gestionable del bloque SAC (estado
        # operativo); los demás campos sac_* son solo lectura.
        self.combo_estado_sac = QComboBox()
        self.combo_estado_sac.addItems(ESTADOS_SAC)
        if self._datos["estado_sac"] not in ESTADOS_SAC and self._datos["estado_sac"]:
            self.combo_estado_sac.addItem(self._datos["estado_sac"])
        self.combo_estado_sac.setCurrentText(self._datos["estado_sac"])
        self.combo_estado_sac.setFixedWidth(200)
        contenedor.addWidget(lbl_sac)
        contenedor.addWidget(self.combo_estado_sac)

        widget = QWidget()
        widget.setLayout(contenedor)
        card.agregar_widget_ancho_completo(widget)
        return card

    def _seccion_observaciones(self) -> SectionCard:
        """Un único campo de observaciones (sección 19 — no múltiples campos)."""
        card = SectionCard("Observaciones", columnas=1)
        self.texto_observaciones = QPlainTextEdit()
        self.texto_observaciones.setPlainText(self._datos["observaciones"])
        self.texto_observaciones.setFixedHeight(90)
        self.texto_observaciones.setStyleSheet(
            f"border: 1px solid {theme.BORDER}; border-radius: 8px; padding: 8px; background-color: white;"
        )
        card.agregar_widget_ancho_completo(self.texto_observaciones)
        return card

    # ------------------------------------------------------------------
    def _fila_guardar(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        self.lbl_estado_guardado = QLabel("")
        self.lbl_estado_guardado.setProperty("role", "secondary")
        fila.addWidget(self.lbl_estado_guardado)
        fila.addStretch()

        boton_guardar = QPushButton("Guardar cambios")
        boton_guardar.setProperty("variant", "primary")
        boton_guardar.clicked.connect(self._guardar_cambios)
        fila.addWidget(boton_guardar)
        return fila

    def _guardar_cambios(self) -> None:
        cambios = {
            "fecha_traslado": self._fecha_del_campo(self.campo_fecha_traslado),
            "institucion_competente": self.campo_institucion_competente.text().strip(),
            "hubo_respuesta": self.combo_hubo_respuesta.currentText(),
            "fecha_respuesta": self._fecha_del_campo(self.campo_fecha_respuesta),
            "notificacion_usuario": self.combo_notificacion_usuario.currentText(),
            "respuesta_entidad": self.campo_respuesta_entidad.toPlainText().strip(),
            "radicado_ente_control": self.campo_radicado.text().strip(),
            "entidad_control": self.campo_entidad_control.text().strip(),
            "fecha_reporte_control": self._fecha_del_campo(self.campo_fecha_reporte_control),
            "estado_gestion": self.combo_estado.currentText(),
            "estado_sac": self.combo_estado_sac.currentText(),
            "observaciones": self.texto_observaciones.toPlainText().strip(),
        }
        try:
            from sgs.app.casos_de_uso import guardar_gestion_solicitud

            guardar_gestion_solicitud(self.numero_solicitud_sac, cambios)
            self.lbl_estado_guardado.setText("Cambios guardados.")
            self.volver_solicitado.emit()
        except Exception as exc:
            self.lbl_estado_guardado.setText(f"No se pudo guardar: {exc}")

    def _actualizar_estado_controles(self) -> None:
        """¿Hubo respuesta? -> SI activa los campos de respuesta y bloquea el
        ente de control; NO activa el ente de control y bloquea la respuesta;
        N_A los bloquea todos. También actualiza en vivo la Decisión."""
        hubo = self.combo_hubo_respuesta.currentText()
        hubo_si = hubo == "SI"
        hubo_no = hubo == "NO"
        for widget in (
            self.campo_fecha_respuesta,
            self.combo_notificacion_usuario,
            self.campo_respuesta_entidad,
        ):
            widget.setEnabled(hubo_si)
        for widget in self._widgets_ente_control:
            widget.setEnabled(hubo_no)
        texto_decision = {
            "SI": "Cerrar en SAC",
            "NO": "Remitir a ente de control",
            "N_A": "No aplica",
        }.get(hubo, "No aplica")
        self.lbl_decision.setText(texto_decision)

    def _actualizar_preview_traslado(self) -> None:
        """Al elegir la fecha de traslado recalcula en vivo el bloque de
        tiempos (oportunidad, indicador, fecha límite, días y semáforo)."""
        fecha = self._fecha_del_campo(self.campo_fecha_traslado)
        if not fecha:
            self.lbl_oportunidad_traslado.setText("—")
            self.lbl_indicador_traslado.setText("—")
            self.lbl_fecha_limite.setText("—")
            self.lbl_dias_restantes.setText("—")
            self._aplicar_semaforo_en_vivo(motor_semaforo.SIN_FECHA)
            return
        try:
            from sgs.app.casos_de_uso import previsualizar_traslado

            prev = previsualizar_traslado(
                self.numero_solicitud_sac,
                QDate.fromString(fecha, "yyyy-MM-dd").toPython(),
            )
        except Exception as exc:
            self.lbl_estado_guardado.setText(f"No se pudo previsualizar el traslado: {exc}")
            return
        self.lbl_oportunidad_traslado.setText(
            f"{prev['oportunidad_dias']} días hábiles" if prev["oportunidad_dias"] is not None else "—"
        )
        self.lbl_indicador_traslado.setText(_etiqueta(_ETIQUETA_INDICADOR, prev["indicador_oportunidad"]) or "—")
        self.lbl_fecha_limite.setText(prev["fecha_limite"] or "—")
        self.lbl_dias_restantes.setText(str(prev["dias_restantes"]) if prev["dias_restantes"] != "" else "—")
        self._aplicar_semaforo_en_vivo(prev["semaforo"])

    def _aplicar_semaforo_en_vivo(self, color: str) -> None:
        self.badge_encabezado.cambiar_color(color)
        self.badge_tiempos.cambiar_color(color)

    @staticmethod
    def _fecha_del_campo(campo: QDateEdit) -> str:
        """La fecha mínima (que se muestra en blanco) es el valor vacío."""
        if campo.date() == campo.minimumDate():
            return ""
        return campo.date().toString("yyyy-MM-dd")

    @staticmethod
    def _crear_fecha_edit(valor_str: str) -> CampoFecha:
        """Campo de fecha cuyo calendario, cuando está vacío, se abre en el
        mes actual (no en enero de 1900). El valor vacío se conserva hasta
        que el usuario elija un día — ver `CampoFecha`."""
        return CampoFecha(valor_str)

    @staticmethod
    def _estilo_textarea() -> str:
        return f"border: 1px solid {theme.BORDER}; border-radius: 8px; padding: 8px; background-color: white;"

    # ------------------------------------------------------------------
    @staticmethod
    def _datos_vacio(numero_solicitud_sac: str) -> dict:
        claves = (
            "semaforo proceso funcionario tipo_documento documento nombre_ciudadano sexo fecha_nacimiento edad "
            "telefono correo municipio_origen municipio_residencia poblacion_priorizada regimen eps motivo "
            "tipo_asunto solicitud subclasificacion prioridad_caso barrera_acceso usuario_sac fecha_ingreso "
            "estado_sac detalle actuacion_funcionario fecha_traslado institucion_competente oportunidad_traslado_dias "
            "indicador_oportunidad_traslado fecha_limite dias_restantes hubo_respuesta decision fecha_respuesta "
            "oportunidad_respuesta notificacion_usuario respuesta_entidad radicado_ente_control entidad_control "
            "fecha_reporte_control estado_gestion observaciones"
        ).split()
        datos = {clave: "" for clave in claves}
        datos.update({"numero_solicitud_sac": numero_solicitud_sac, "semaforo": "SIN_FECHA", "edad": ""})
        return datos