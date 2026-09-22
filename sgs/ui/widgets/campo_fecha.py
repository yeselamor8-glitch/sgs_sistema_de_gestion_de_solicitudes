"""
Campo de fecha reutilizable para el Detalle de solicitud.

Comportamiento: cuando el campo está VACÍO (su valor real es la fecha
mínima, que se muestra en blanco), el calendario emergente se abre
posicionado en el MES ACTUAL en vez de en enero de 1900. Así el usuario
no tiene que navegar décadas para elegir una fecha. El valor del campo
sigue siendo "vacío" hasta que el usuario seleccione un día — no se
rellena solo con la fecha de hoy.

Implementación: el popup del calendario lo crea y lo muestra Qt
internamente al pulsar la flecha del QDateEdit, y en ese instante Qt
reposiciona la vista al valor del campo (1900). Para ganarle a ese
reposicionamiento se instala un event filter sobre el propio
QCalendarWidget y se corrige la página mostrada JUSTO cuando el popup se
hace visible (evento Show).
"""
from __future__ import annotations

from PySide6.QtCore import QDate, QEvent, QObject
from PySide6.QtWidgets import QDateEdit


class CampoFecha(QDateEdit):
    """QDateEdit con popup de calendario que, si el campo está vacío, se
    abre en el mes actual (no en la fecha mínima)."""

    def __init__(self, valor_str: str = "", parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy-MM-dd")
        self.setSpecialValueText(" ")  # la fecha mínima se muestra en blanco
        self._fecha_vacia = QDate(1900, 1, 1)
        self.setMinimumDate(self._fecha_vacia)
        fecha = QDate.fromString(valor_str, "yyyy-MM-dd")
        self.setDate(fecha if fecha.isValid() else self._fecha_vacia)

        # El calendarWidget existe al activar calendarPopup: le instalamos
        # un filtro para reposicionarlo cuando su popup se muestre.
        calendario = self.calendarWidget()
        if calendario is not None:
            calendario.installEventFilter(self)

    def esta_vacio(self) -> bool:
        return self.date() == self.minimumDate()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        """Cuando el popup del calendario se muestra y el campo está vacío,
        posiciona la vista en el mes/año actual (sin cambiar el valor)."""
        if event.type() == QEvent.Type.Show and obj is self.calendarWidget():
            self._posicionar_calendario_en_hoy()
        return super().eventFilter(obj, event)

    def _posicionar_calendario_en_hoy(self) -> None:
        if not self.esta_vacio():
            return
        calendario = self.calendarWidget()
        if calendario is not None:
            # Solo cambiamos la PÁGINA mostrada (mes/año), no la fecha
            # seleccionada: `setSelectedDate` rellenaría el campo con hoy y
            # rompería la lógica de "vacío hasta que el usuario elija".
            hoy = QDate.currentDate()
            calendario.setCurrentPage(hoy.year(), hoy.month())
