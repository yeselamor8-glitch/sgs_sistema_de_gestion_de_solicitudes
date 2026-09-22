from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

from sgs.ui.widgets.campo_fecha import CampoFecha


def test_campo_vacio_posiciona_calendario_en_mes_actual_al_mostrarse():
    """Un campo sin fecha se muestra en blanco (valor = fecha mínima) pero
    su calendario, al desplegarse el popup (evento Show), se reposiciona en
    el mes/año de hoy en vez de enero de 1900."""
    from PySide6.QtGui import QShowEvent

    app = QApplication.instance() or QApplication([])
    campo = CampoFecha("")
    calendario = campo.calendarWidget()

    # Antes de mostrar el popup arranca en la fecha mínima (1900).
    assert calendario.yearShown() == 1900

    # Simular que Qt despliega el popup del calendario.
    app.sendEvent(calendario, QShowEvent())

    hoy = QDate.currentDate()
    assert calendario.monthShown() == hoy.month()
    assert calendario.yearShown() == hoy.year()
    app.processEvents()


def test_campo_con_fecha_conserva_su_valor():
    """Si viene con una fecha, la respeta (no la pisa con hoy)."""
    app = QApplication.instance() or QApplication([])
    campo = CampoFecha("2026-03-15")

    assert not campo.esta_vacio()
    assert campo.date() == QDate(2026, 3, 15)
    app.processEvents()


def test_campo_vacio_no_se_rellena_solo_con_hoy():
    """Posicionar el calendario en hoy NO cambia el valor del campo: sigue
    vacío hasta que el usuario elija un día."""
    app = QApplication.instance() or QApplication([])
    campo = CampoFecha("")
    campo._posicionar_calendario_en_hoy()

    assert campo.esta_vacio()  # el valor sigue siendo vacío
    app.processEvents()
