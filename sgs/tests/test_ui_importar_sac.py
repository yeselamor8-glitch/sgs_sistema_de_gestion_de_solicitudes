from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QMessageBox

import sgs.app.casos_de_uso as casos_de_uso
import sgs.ui.pages.importar_sac as importar_sac_module
from sgs.ui.pages.importar_sac import ImportarSacPage


def _resumen_simulado(**overrides):
    """ResumenImportacion mínimo para poblar el paso de resumen en la UI."""
    base = dict(
        total=0,
        nuevos=0,
        actualizados=0,
        sin_cambios=0,
        errores=0,
        sin_clasificar=0,
        conflictos=0,
        resultados=(),
        duplicados_archivo=(),
        duplicados_existentes=(),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_confirmar_importacion_muestra_mensaje_y_vuelve_al_inicio(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        casos_de_uso,
        "confirmar_importacion_sac",
        lambda ruta, nombre, usuario: {
            "nuevos": 5,
            "actualizados": 0,
            "sin_cambios": 0,
            "errores": 0,
            "sin_clasificar": 0,
        },
    )
    mensajes = []
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *args, **kwargs: mensajes.append(args[2]))
    )

    pagina = ImportarSacPage(usuario_id=1)
    pagina._ruta_archivo = "C:/exporte_sac.xlsx"
    pagina._resumen = type("Resumen", (), {"duplicados_archivo": [], "duplicados_existentes": []})()
    pagina._ir_a_paso(3)

    pagina._confirmar_importacion()

    assert mensajes == ["Datos importados satisfactoriamente."]
    assert pagina.stack.currentIndex() == 0
    assert pagina._ruta_archivo is None
    assert pagina._resumen is None
    app.processEvents()


def test_confirmar_importacion_bloqueada_con_duplicados(monkeypatch):
    app = QApplication.instance() or QApplication([])
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args, **kwargs: avisos.append(args[2])))

    pagina = ImportarSacPage(usuario_id=1)
    pagina._ruta_archivo = "C:/exporte_sac.xlsx"
    pagina._resumen = type(
        "Resumen", (), {"duplicados_archivo": ["S001"], "duplicados_existentes": []}
    )()
    pagina._ir_a_paso(3)

    pagina._confirmar_importacion()

    assert len(avisos) == 1
    assert "bloqueada" in avisos[0]
    assert pagina.stack.currentIndex() == 3
    app.processEvents()


def test_mensaje_duplicados_existentes_solo_muestra_cantidad():
    # Muchos duplicados ya en el sistema: no deben listarse uno por uno,
    # solo la cantidad para no llenar la pantalla.
    resumen = _resumen_simulado(
        duplicados_existentes=tuple(f"SAC-{i:04d}" for i in range(50)),
    )
    mensaje = ImportarSacPage._mensaje_duplicados(resumen)

    assert "50 registros" in mensaje
    assert "ya están cargados" in mensaje
    # ningún número individual aparece
    assert "SAC-0000" not in mensaje
    assert "SAC-0049" not in mensaje


def test_mensaje_duplicados_archivo_si_lista_los_numeros():
    # Los repetidos dentro del archivo sí se muestran (son pocos y es un
    # error de armado del exporte).
    resumen = _resumen_simulado(duplicados_archivo=("SAC-100", "SAC-200"))
    mensaje = ImportarSacPage._mensaje_duplicados(resumen)

    assert "SAC-100" in mensaje
    assert "SAC-200" in mensaje
    assert "dentro del archivo" in mensaje


def test_resumen_con_duplicados_existentes_bloquea_y_muestra_solo_cantidad(monkeypatch):
    app = QApplication.instance() or QApplication([])
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args, **kwargs: avisos.append(args[2])))

    resumen = _resumen_simulado(
        total=30, nuevos=0,
        duplicados_existentes=tuple(f"SAC-{i:04d}" for i in range(30)),
    )
    pagina = ImportarSacPage(usuario_id=1)
    pagina._resumen = resumen
    pagina._llenar_resumen()

    assert not pagina.boton_confirmar.isEnabled()
    assert "30 registros" in pagina.lbl_estado_confirmacion.text()
    assert "SAC-0000" not in pagina.lbl_estado_confirmacion.text()
    assert len(avisos) == 1
    app.processEvents()


def test_tabla_problemas_incluye_accionables_pero_no_duplicados_existentes(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args, **kwargs: None))

    resultados = (
        SimpleNamespace(
            numero_solicitud_sac="SAC-001", accion="error",
            clasificacion_estado=None, errores=("Falta valor en 'motivo'.",)
        ),
        SimpleNamespace(
            numero_solicitud_sac="SAC-002", accion="nuevo",
            clasificacion_estado="sin_clasificar", errores=()
        ),
        SimpleNamespace(
            numero_solicitud_sac="SAC-003", accion="nuevo",
            clasificacion_estado="conflicto", errores=()
        ),
    )
    resumen = _resumen_simulado(
        total=6, nuevos=2, errores=1, sin_clasificar=1, conflictos=1,
        resultados=resultados,
        duplicados_archivo=("SAC-004",),
        # muchos ya existentes: NO deben entrar a la tabla
        duplicados_existentes=tuple(f"SAC-{i:04d}" for i in range(20)),
    )

    pagina = ImportarSacPage(usuario_id=1)
    pagina._resumen = resumen
    pagina._llenar_resumen()

    assert not pagina.tabla_problemas.isHidden()
    # error + sin_clasificar + conflicto + duplicado_archivo = 4 (existentes no)
    assert pagina.tabla_problemas.rowCount() == 4
    tipos = {pagina.tabla_problemas.item(i, 1).text() for i in range(4)}
    assert tipos == {"Error", "Sin clasificación", "Conflicto", "Duplicado en archivo"}
    # los duplicados existentes solo aparecen como cantidad en el mensaje
    assert "20 registros" in pagina.lbl_estado_confirmacion.text()
    app.processEvents()


def test_tabla_problemas_oculta_cuando_no_hay_accionables():
    app = QApplication.instance() or QApplication([])
    pagina = ImportarSacPage(usuario_id=1)
    pagina._resumen = _resumen_simulado(total=2, nuevos=2)
    pagina._llenar_resumen()

    assert pagina.tabla_problemas.isHidden()
    assert pagina.tabla_problemas.rowCount() == 0
    app.processEvents()


def test_validar_estructura_muestra_error_de_formato_xls(monkeypatch):
    app = QApplication.instance() or QApplication([])

    def _lanzar_error(ruta):
        raise ValueError("Solo se admite el formato libro de Excel (.xlsx).")

    monkeypatch.setattr(casos_de_uso, "validar_y_previsualizar_archivo_sac", _lanzar_error)

    pagina = ImportarSacPage(usuario_id=1)
    pagina._ruta_archivo = "C:/exporte_viejo.xls"
    pagina._validar_estructura()

    assert pagina.stack.currentIndex() == 1
    assert "libro de Excel" in pagina.lbl_resultado_validacion.text()
    app.processEvents()