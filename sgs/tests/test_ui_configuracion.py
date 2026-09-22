from PySide6.QtWidgets import QApplication

import sgs.app.casos_de_uso as casos_de_uso
from sgs.ui.pages.configuracion import ConfiguracionPage


def _pagina(monkeypatch):
    """ConfiguracionPage con los casos de uso de BD neutralizados para que
    la página se construya sin conexión real."""
    app = QApplication.instance() or QApplication([])
    # Las demás pestañas ya toleran fallos de BD (try/except), pero
    # evitamos ruido devolviendo listas vacías donde aplica.
    monkeypatch.setattr(casos_de_uso, "listar_usuarios", lambda: [])
    monkeypatch.setattr(casos_de_uso, "listar_procesos", lambda: [])
    return app


def test_semaforizacion_carga_umbral_amarillo(monkeypatch):
    app = _pagina(monkeypatch)
    monkeypatch.setattr(
        casos_de_uso,
        "obtener_parametros_semaforizacion",
        lambda: {"dias_verde_hasta": 1, "dias_amarillo_cerca": 4},
    )

    pagina = ConfiguracionPage()
    # el spinbox debe reflejar el umbral de amarillo guardado
    assert pagina.spin_dias_amarillo.value() == 4
    app.processEvents()


def test_semaforizacion_guarda_conservando_verde_hasta(monkeypatch):
    app = _pagina(monkeypatch)
    monkeypatch.setattr(
        casos_de_uso,
        "obtener_parametros_semaforizacion",
        lambda: {"dias_verde_hasta": 2, "dias_amarillo_cerca": 1},
    )
    guardados = []
    monkeypatch.setattr(
        casos_de_uso,
        "guardar_parametros_semaforizacion",
        lambda verde, amarillo: guardados.append((verde, amarillo)),
    )

    pagina = ConfiguracionPage()
    pagina.spin_dias_amarillo.setValue(5)
    pagina._guardar_semaforizacion()

    # conserva verde_hasta=2 y guarda el nuevo umbral amarillo=5
    assert guardados == [(2, 5)]
    assert "Guardado" in pagina.lbl_semaforizacion_estado.text()
    app.processEvents()
