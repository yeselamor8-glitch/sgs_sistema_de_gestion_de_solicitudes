from PySide6.QtWidgets import QApplication

import sgs.ui.main_window as main_window_module
from sgs.ui.main_window import MainWindow


def test_main_window_oculta_importar_sac_si_el_funcionario_no_tiene_permiso(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(main_window_module, "usuario_tiene_permiso", lambda usuario_id, nombre: False)

    ventana = MainWindow(rol="FUNCIONARIO", nombre_usuario="Ana", usuario_id=7)

    assert "importar_sac" not in ventana._paginas
    assert "importar_sac" not in ventana.sidebar._botones
    app.processEvents()


def test_permiso_cambia_en_vivo_agrega_y_quita_pagina_y_sidebar(monkeypatch):
    app = QApplication.instance() or QApplication([])
    permiso = {"valor": False}
    monkeypatch.setattr(
        main_window_module, "usuario_tiene_permiso", lambda usuario_id, nombre: permiso["valor"]
    )

    ventana = MainWindow(rol="FUNCIONARIO", nombre_usuario="Ana", usuario_id=7)
    assert "importar_sac" not in ventana._paginas
    assert "importar_sac" not in ventana.sidebar._botones

    permiso["valor"] = True
    ventana.refrescar_acceso_importar_sac()
    assert "importar_sac" in ventana._paginas
    assert "importar_sac" in ventana.sidebar._botones

    permiso["valor"] = False
    ventana.refrescar_acceso_importar_sac()
    assert "importar_sac" not in ventana._paginas
    assert "importar_sac" not in ventana.sidebar._botones
    app.processEvents()
