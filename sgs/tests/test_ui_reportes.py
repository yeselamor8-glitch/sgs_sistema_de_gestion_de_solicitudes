from PySide6.QtWidgets import QApplication

import sgs.app.casos_de_uso as casos_de_uso
import sgs.ui.pages.reportes as reportes_module
from sgs.motores.motor_analisis import cargar_dataframe
from sgs.ui.pages.reportes import ReportesPage
from sgs.ui.widgets.dialogo_columnas_analisis import DialogoColumnasAnalisis


# ----------------------------------------------------------------------
# Caso de uso: datos del sistema para análisis
# ----------------------------------------------------------------------

def test_obtener_solicitudes_para_analisis_excluye_objetos_orm(monkeypatch):
    # obtener_solicitudes devuelve dicts con campos planos + objetos ORM
    # internos que el análisis no debe tabular.
    fila = {
        "numero_solicitud_sac": "SAC-001",
        "proceso": "Traslado",
        "eps": "Savia Salud",
        "estado_gestion": "En trámite",
        "obj_solicitud": object(),
        "traslado": object(),
        "respuesta": object(),
        "ente_control": object(),
    }
    monkeypatch.setattr(casos_de_uso, "obtener_solicitudes", lambda f, u, r: [fila])

    resultado = casos_de_uso.obtener_solicitudes_para_analisis(usuario_id=1, rol="ADMINISTRADOR")

    assert len(resultado) == 1
    claves = set(resultado[0].keys())
    assert "numero_solicitud_sac" in claves
    assert "proceso" in claves
    assert claves.isdisjoint({"obj_solicitud", "traslado", "respuesta", "ente_control"})


# ----------------------------------------------------------------------
# Filtros múltiples acumulables
# ----------------------------------------------------------------------

def _pagina_con_datos():
    app = QApplication.instance() or QApplication([])
    pagina = ReportesPage(usuario_id=1, rol="ADMINISTRADOR")
    filas = [
        {"proceso": "Traslado", "eps": "Savia Salud", "estado_gestion": "En trámite"},
        {"proceso": "Traslado", "eps": "Suramericana", "estado_gestion": "Solucionada"},
        {"proceso": "Especialistas", "eps": "Savia Salud", "estado_gestion": "En trámite"},
    ]
    pagina._df_original = cargar_dataframe(filas)
    pagina._df_resultado = pagina._df_original
    pagina._actualizar_listas_columnas()
    pagina._columnas_visibles = list(pagina._df_original.columns)
    return app, pagina


def test_filtros_se_acumulan_y_aplican_en_conjunto():
    app, pagina = _pagina_con_datos()

    # Filtro 1: eps=Savia Salud -> deja filas 0 (Traslado) y 2 (Especialistas)
    pagina.combo_filtro_columna.setCurrentText("eps")
    pagina.combo_filtro_operador.setCurrentText("igual_a")
    pagina.campo_filtro_valor.setText("Savia Salud")
    pagina._agregar_filtro()
    assert len(pagina._df_resultado) == 2

    # Filtro 2 (AND): proceso=Especialistas -> deja solo la fila 2
    pagina.combo_filtro_columna.setCurrentText("proceso")
    pagina.combo_filtro_operador.setCurrentText("igual_a")
    pagina.campo_filtro_valor.setText("Especialistas")
    pagina._agregar_filtro()

    assert len(pagina._filtros_activos) == 2
    assert pagina.lista_filtros_activos.count() == 2
    # Savia Salud + Especialistas deja solo una fila
    assert len(pagina._df_resultado) == 1
    assert pagina._df_resultado.iloc[0]["proceso"] == "Especialistas"
    app.processEvents()


def test_quitar_y_limpiar_filtros():
    app, pagina = _pagina_con_datos()
    for columna, valor in (("eps", "Savia Salud"), ("estado_gestion", "En trámite")):
        pagina.combo_filtro_columna.setCurrentText(columna)
        pagina.combo_filtro_operador.setCurrentText("igual_a")
        pagina.campo_filtro_valor.setText(valor)
        pagina._agregar_filtro()

    pagina.lista_filtros_activos.setCurrentRow(0)
    pagina._quitar_filtro_seleccionado()
    assert len(pagina._filtros_activos) == 1

    pagina._limpiar_filtros()
    assert pagina._filtros_activos == []
    # sin filtros: vuelve al df completo
    assert len(pagina._df_resultado) == 3
    app.processEvents()


def test_filtro_vacio_no_se_agrega():
    app, pagina = _pagina_con_datos()
    pagina.combo_filtro_columna.setCurrentText("eps")
    pagina.campo_filtro_valor.setText("")  # sin valor
    pagina._agregar_filtro()
    assert pagina._filtros_activos == []
    app.processEvents()


# ----------------------------------------------------------------------
# Diálogo de columnas: predeterminado
# ----------------------------------------------------------------------

def test_dialogo_columnas_restablecer_predeterminado():
    app = QApplication.instance() or QApplication([])
    disponibles = ["a", "b", "c", "d"]
    # selección parcial y reordenada
    dialogo = DialogoColumnasAnalisis(disponibles, ["c", "a"], parent=None)

    assert dialogo.columnas_seleccionadas() == ["c", "a"]

    dialogo._restablecer_predeterminado()
    # todas visibles, en el orden original de la fuente
    assert dialogo.columnas_seleccionadas() == disponibles
    app.processEvents()
