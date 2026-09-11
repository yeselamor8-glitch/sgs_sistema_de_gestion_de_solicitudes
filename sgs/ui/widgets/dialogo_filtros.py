from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)
from PySide6.QtCore import QDate

ESTADOS_GESTION = ["Todos", "En trámite", "Solucionada"]
SEMAFOROS = ["Todos", "VERDE", "AMARILLO", "ROJO"]


class DialogoFiltros(QDialog):
    """Filtros avanzados de la pantalla Solicitudes/Mis solicitudes:
    rango de fechas de ingreso, proceso, estado de gestión y semáforo."""

    def __init__(self, filtros_actuales: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filtros")
        self.resize(360, 280)
        filtros_actuales = filtros_actuales or {}

        layout = QVBoxLayout(self)
        info = QLabel("Filtra la lista de solicitudes por fecha, proceso, estado o semaforización.")
        info.setProperty("role", "secondary")
        info.setWordWrap(True)
        layout.addWidget(info)

        formulario = QFormLayout()

        self.fecha_desde = QDateEdit(calendarPopup=True)
        self.fecha_desde.setDisplayFormat("yyyy-MM-dd")
        self.fecha_desde.setDate(filtros_actuales.get("fecha_desde") or QDate.currentDate().addMonths(-1))
        self.fecha_desde.setSpecialValueText(" ")

        self.fecha_hasta = QDateEdit(calendarPopup=True)
        self.fecha_hasta.setDisplayFormat("yyyy-MM-dd")
        self.fecha_hasta.setDate(filtros_actuales.get("fecha_hasta") or QDate.currentDate())

        self.combo_proceso = QComboBox()
        procesos = ["Todos"]
        try:
            from sgs.app.casos_de_uso import listar_procesos

            procesos.extend(p["nombre"] for p in listar_procesos() if p["activo"])
        except Exception:
            procesos.append("No se pudieron cargar los procesos")
        self.combo_proceso.addItems(procesos)
        self.combo_proceso.setCurrentText(filtros_actuales.get("proceso", "Todos"))

        self.combo_estado = QComboBox()
        self.combo_estado.addItems(ESTADOS_GESTION)
        self.combo_estado.setCurrentText(filtros_actuales.get("estado_gestion", "Todos"))

        self.combo_semaforo = QComboBox()
        self.combo_semaforo.addItems(SEMAFOROS)
        self.combo_semaforo.setCurrentText(filtros_actuales.get("semaforo", "Todos"))

        formulario.addRow("Fecha de ingreso desde:", self.fecha_desde)
        formulario.addRow("Fecha de ingreso hasta:", self.fecha_hasta)
        formulario.addRow("Proceso:", self.combo_proceso)
        formulario.addRow("Estado:", self.combo_estado)
        formulario.addRow("Semaforización:", self.combo_semaforo)
        layout.addLayout(formulario)

        boton_limpiar = QDialogButtonBox.StandardButton
        botones = QDialogButtonBox(boton_limpiar.Ok | boton_limpiar.Cancel | boton_limpiar.Reset)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        botones.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self._limpiar)
        layout.addWidget(botones)

    def _limpiar(self) -> None:
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_hasta.setDate(QDate.currentDate())
        self.combo_proceso.setCurrentText("Todos")
        self.combo_estado.setCurrentText("Todos")
        self.combo_semaforo.setCurrentText("Todos")

    def filtros_resultantes(self) -> dict:
        return {
            "fecha_desde": self.fecha_desde.date(),
            "fecha_hasta": self.fecha_hasta.date(),
            "proceso": self.combo_proceso.currentText(),
            "estado_gestion": self.combo_estado.currentText(),
            "semaforo": self.combo_semaforo.currentText(),
        }