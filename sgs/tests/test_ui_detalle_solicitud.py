from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

import sgs.app.casos_de_uso as casos_de_uso
from sgs.ui.pages.detalle_solicitud import DetalleSolicitudPage


def _datos(numero: str) -> dict:
    datos = DetalleSolicitudPage._datos_vacio(numero)
    datos.update(
        {
            "hubo_respuesta": "N_A",
            "notificacion_usuario": "Pendiente",
            "estado_sac": "En trámite",
        }
    )
    return datos


def test_hubo_respuesta_si_activa_respuesta_y_bloquea_ente_control(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(casos_de_uso, "obtener_detalle_solicitud", lambda numero: _datos("S001"))

    pagina = DetalleSolicitudPage("S001")
    assert not pagina.campo_fecha_respuesta.isEnabled()
    assert not pagina._widgets_ente_control[0].isEnabled()

    pagina.combo_hubo_respuesta.setCurrentText("SI")
    assert pagina.campo_fecha_respuesta.isEnabled()
    assert pagina.combo_notificacion_usuario.isEnabled()
    assert pagina.campo_respuesta_entidad.isEnabled()
    assert not pagina._widgets_ente_control[0].isEnabled()


def test_hubo_respuesta_no_activa_ente_de_control(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(casos_de_uso, "obtener_detalle_solicitud", lambda numero: _datos("S002"))

    pagina = DetalleSolicitudPage("S002")
    pagina.combo_hubo_respuesta.setCurrentText("NO")

    assert not pagina.campo_fecha_respuesta.isEnabled()
    for widget in pagina._widgets_ente_control:
        assert widget.isEnabled()


def test_guardar_envia_estado_sac_fechas_opcionalmente_vacias_y_vuelve(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(casos_de_uso, "obtener_detalle_solicitud", lambda numero: _datos("S003"))

    capturado = {}

    def guardar_falso(numero, cambios):
        capturado.update(cambios)

    monkeypatch.setattr(casos_de_uso, "guardar_gestion_solicitud", guardar_falso)

    pagina = DetalleSolicitudPage("S003")
    llamado_volver = []
    pagina.volver_solicitado.connect(lambda: llamado_volver.append(1))

    pagina._guardar_cambios()

    assert capturado["estado_sac"] == "En trámite"
    assert capturado["fecha_traslado"] == ""
    assert capturado["fecha_respuesta"] == ""
    assert llamado_volver == [1]
    app.processEvents()


def test_decision_se_actualiza_en_vivo_al_cambiar_hubo_respuesta(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(casos_de_uso, "obtener_detalle_solicitud", lambda numero: _datos("S004"))

    pagina = DetalleSolicitudPage("S004")
    assert pagina.lbl_decision.text() == "No aplica"

    pagina.combo_hubo_respuesta.setCurrentText("SI")
    assert pagina.lbl_decision.text() == "Cerrar en SAC"
    pagina.combo_hubo_respuesta.setCurrentText("NO")
    assert pagina.lbl_decision.text() == "Remitir a ente de control"
    app.processEvents()


def test_detalle_abre_cuando_dias_restantes_es_entero(monkeypatch):
    """Regresión: cuando la solicitud ya tiene fecha límite, la capa de
    aplicación entrega 'dias_restantes' como int. La tarjeta debe abrir
    sin TypeError (antes QLabel(int) reventaba) y mostrarlo como texto,
    incluido el 0 ('vence hoy')."""
    app = QApplication.instance() or QApplication([])
    datos = _datos("S006")
    datos["dias_restantes"] = 3  # entero, como cuando hay fecha límite
    datos["oportunidad_traslado_dias"] = 0  # int también aparece aquí
    monkeypatch.setattr(casos_de_uso, "obtener_detalle_solicitud", lambda numero: datos)

    pagina = DetalleSolicitudPage("S006")

    assert pagina._error_carga == ""
    assert pagina.lbl_dias_restantes.text() == "3"
    app.processEvents()


def test_detalle_muestra_cero_dias_restantes_no_guion(monkeypatch):
    """El 0 en 'Días restantes' significa 'vence hoy': debe mostrarse como
    '0', no como '—'."""
    app = QApplication.instance() or QApplication([])
    datos = _datos("S007")
    datos["dias_restantes"] = 0
    monkeypatch.setattr(casos_de_uso, "obtener_detalle_solicitud", lambda numero: datos)

    pagina = DetalleSolicitudPage("S007")
    assert pagina.lbl_dias_restantes.text() == "0"
    app.processEvents()


def test_previsualizar_traslado_actualiza_bloque_de_tiempos_en_vivo(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(casos_de_uso, "obtener_detalle_solicitud", lambda numero: _datos("S005"))

    def previsualizar(numero, fecha):
        assert numero == "S005"
        assert fecha == QDate(2026, 3, 10).toPython()
        return {
            "fecha_limite": "2026-03-20",
            "oportunidad_dias": 2,
            "indicador_oportunidad": "CERCA_DE_VENCIMIENTO",
            "dias_restantes": 8,
            "semaforo": "CERCA_DE_VENCIMIENTO",
        }

    monkeypatch.setattr(casos_de_uso, "previsualizar_traslado", previsualizar)

    pagina = DetalleSolicitudPage("S005")
    pagina.campo_fecha_traslado.setDate(QDate(2026, 3, 10))
    app.processEvents()

    assert pagina.lbl_oportunidad_traslado.text() == "2 días hábiles"
    assert pagina.lbl_indicador_traslado.text() == "Cerca de vencimiento"
    assert pagina.lbl_fecha_limite.text() == "2026-03-20"
    assert pagina.lbl_dias_restantes.text() == "8"
    assert pagina.badge_tiempos._color_actual == "CERCA_DE_VENCIMIENTO"
    assert pagina.badge_encabezado._color_actual == "CERCA_DE_VENCIMIENTO"
    app.processEvents()