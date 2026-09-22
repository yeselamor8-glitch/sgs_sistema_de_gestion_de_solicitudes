"""Pruebas de auditoría: contexto de sesión y helper de registro.

No se usa BD SQLite real porque valor_anterior/nuevo son JSONB; se prueba
con un doble de repo en memoria y el contexto de sesión directo.
"""
from contextlib import contextmanager

import sgs.app.casos_de_uso as casos_de_uso
from sgs.app import contexto_sesion


def test_contexto_sesion_set_y_limpiar():
    contexto_sesion.limpiar()
    assert contexto_sesion.usuario_id_actual() is None

    contexto_sesion.set_actor(7, "Admin", "ADMINISTRADOR")
    actor = contexto_sesion.actor_actual()
    assert actor.usuario_id == 7
    assert actor.nombre == "Admin"
    assert contexto_sesion.usuario_id_actual() == 7

    contexto_sesion.limpiar()
    assert contexto_sesion.usuario_id_actual() is None


class _AuditoriaRepoFalso:
    registros: list = []

    def __init__(self, db=None):
        pass

    def registrar(self, usuario_id, accion, entidad, entidad_id=None,
                  valor_anterior=None, valor_nuevo=None, solicitud_relacionada_id=None):
        _AuditoriaRepoFalso.registros.append({
            "usuario_id": usuario_id, "accion": accion, "entidad": entidad,
            "entidad_id": entidad_id, "valor_nuevo": valor_nuevo,
        })


@contextmanager
def _sesion_falsa():
    yield object()


def test_registrar_auditoria_usa_actor_de_sesion(monkeypatch):
    _AuditoriaRepoFalso.registros = []
    import sgs.repos.auditoria_repo as auditoria_repo
    monkeypatch.setattr(auditoria_repo, "AuditoriaRepo", _AuditoriaRepoFalso)
    monkeypatch.setattr(casos_de_uso, "get_session", _sesion_falsa)

    contexto_sesion.set_actor(99, "Admin", "ADMINISTRADOR")
    casos_de_uso._registrar_auditoria(
        accion="Prueba", entidad="solicitud", entidad_id=5, valor_nuevo={"x": 1},
    )
    assert len(_AuditoriaRepoFalso.registros) == 1
    reg = _AuditoriaRepoFalso.registros[0]
    assert reg["usuario_id"] == 99
    assert reg["accion"] == "Prueba"
    assert reg["valor_nuevo"] == {"x": 1}
    contexto_sesion.limpiar()


def test_registrar_auditoria_no_propaga_errores(monkeypatch):
    # Si el repo falla, auditar NO debe tumbar la acción de negocio.
    import sgs.repos.auditoria_repo as auditoria_repo

    class _RepoQueFalla:
        def __init__(self, db=None):
            pass

        def registrar(self, *a, **k):
            raise RuntimeError("boom")

    monkeypatch.setattr(auditoria_repo, "AuditoriaRepo", _RepoQueFalla)
    monkeypatch.setattr(casos_de_uso, "get_session", _sesion_falsa)
    # no debe lanzar
    casos_de_uso._registrar_auditoria(accion="x", entidad="y")
