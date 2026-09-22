"""Pruebas de la capa de aplicación de reglas de clasificación (CRUD).

No se usa una BD SQLite en memoria porque la columna `valores` es un
ARRAY de PostgreSQL, que SQLite no compila. En su lugar se sustituye el
repositorio por un doble en memoria: así se prueban las validaciones y la
orquestación de los casos de uso sin depender del backend real.
"""
from contextlib import contextmanager

import pytest

import sgs.app.casos_de_uso as casos_de_uso


class _RepoFalso:
    """Doble en memoria de ReglaClasificacionRepo."""

    _almacen: dict[int, dict] = {}
    _siguiente_id = 1

    def __init__(self, db=None):
        pass

    # --- API usada por los casos de uso ---
    def crear_regla(self, proceso_id, tipo_regla, orden_evaluacion, condiciones, descripcion=None, activo=True):
        rid = _RepoFalso._siguiente_id
        _RepoFalso._siguiente_id += 1
        _RepoFalso._almacen[rid] = {
            "id": rid,
            "proceso_id": proceso_id,
            "tipo_regla": tipo_regla,
            "orden_evaluacion": orden_evaluacion,
            "activo": activo,
            "descripcion": descripcion or "",
            "condiciones": [
                {"campo": c, "operador": o, "valores": list(v)} for (c, o, v) in condiciones
            ],
        }
        return type("R", (), {"id": rid})()

    def obtener_para_editar(self, regla_id):
        fila = _RepoFalso._almacen.get(regla_id)
        return dict(fila) if fila else None

    def actualizar_regla(self, regla_id, proceso_id, tipo_regla, orden_evaluacion, condiciones, descripcion=None, activo=None):
        fila = _RepoFalso._almacen[regla_id]
        fila.update({
            "proceso_id": proceso_id,
            "tipo_regla": tipo_regla,
            "orden_evaluacion": orden_evaluacion,
            "descripcion": descripcion or "",
            "condiciones": [{"campo": c, "operador": o, "valores": list(v)} for (c, o, v) in condiciones],
        })
        if activo is not None:
            fila["activo"] = activo

    def eliminar_regla(self, regla_id):
        _RepoFalso._almacen.pop(regla_id, None)

    def cambiar_estado(self, regla_id, activo):
        _RepoFalso._almacen[regla_id]["activo"] = activo

    def listar_para_mostrar(self):
        return [
            {
                "id": f["id"], "proceso": f"proceso {f['proceso_id']}",
                "tipo": f["tipo_regla"], "orden": f["orden_evaluacion"],
                "activo": f["activo"], "resumen": "…",
            }
            for f in _RepoFalso._almacen.values()
        ]


@pytest.fixture()
def repo_falso(monkeypatch):
    _RepoFalso._almacen = {}
    _RepoFalso._siguiente_id = 1

    @contextmanager
    def _get_session():
        yield object()

    monkeypatch.setattr(casos_de_uso, "get_session", _get_session)
    monkeypatch.setattr(casos_de_uso, "ReglaClasificacionRepo", _RepoFalso)
    return _RepoFalso


def test_crear_regla_guarda_condiciones(repo_falso):
    rid = casos_de_uso.crear_regla_clasificacion(
        2, "normal", 100,
        [("motivo", "igual_a", ["A"]), ("solicitud", "igual_a", ["B", "C"])],
        "desc",
    )
    regla = casos_de_uso.obtener_regla_clasificacion(rid)
    assert regla["proceso_id"] == 2
    assert len(regla["condiciones"]) == 2
    assert regla["condiciones"][1]["valores"] == ["B", "C"]


def test_actualizar_regla_reemplaza_condiciones(repo_falso):
    rid = casos_de_uso.crear_regla_clasificacion(1, "normal", 100, [("motivo", "igual_a", ["A"])])
    casos_de_uso.actualizar_regla_clasificacion(
        rid, 2, "excepcion", 10, [("tipoidentificacion", "igual_a", ["PO"])], "ppna"
    )
    regla = casos_de_uso.obtener_regla_clasificacion(rid)
    assert regla["tipo_regla"] == "excepcion"
    assert regla["orden_evaluacion"] == 10
    assert regla["condiciones"] == [{"campo": "tipoidentificacion", "operador": "igual_a", "valores": ["PO"]}]


def test_cambiar_estado_y_eliminar(repo_falso):
    rid = casos_de_uso.crear_regla_clasificacion(1, "normal", 100, [("motivo", "igual_a", ["A"])])
    casos_de_uso.cambiar_estado_regla_clasificacion(rid, False)
    assert casos_de_uso.obtener_regla_clasificacion(rid)["activo"] is False

    casos_de_uso.eliminar_regla_clasificacion(rid)
    assert casos_de_uso.obtener_regla_clasificacion(rid) is None


def test_listar_para_mostrar_incluye_id_y_estado(repo_falso):
    casos_de_uso.crear_regla_clasificacion(1, "normal", 100, [("motivo", "igual_a", ["A"])])
    filas = casos_de_uso.listar_reglas_clasificacion_para_mostrar()
    assert len(filas) == 1
    assert "id" in filas[0] and filas[0]["activo"] is True


# --- Validaciones (no requieren repo) ---

def test_validacion_sin_condiciones_falla(repo_falso):
    with pytest.raises(ValueError):
        casos_de_uso.crear_regla_clasificacion(1, "normal", 100, [])


def test_validacion_valor_vacio_falla(repo_falso):
    with pytest.raises(ValueError):
        casos_de_uso.crear_regla_clasificacion(1, "normal", 100, [("motivo", "igual_a", ["   "])])


def test_validacion_proceso_none_falla(repo_falso):
    with pytest.raises(ValueError):
        casos_de_uso.crear_regla_clasificacion(None, "normal", 100, [("motivo", "igual_a", ["A"])])


def test_validacion_operador_invalido_falla(repo_falso):
    with pytest.raises(ValueError):
        casos_de_uso.crear_regla_clasificacion(1, "normal", 100, [("motivo", "empieza_por", ["A"])])
