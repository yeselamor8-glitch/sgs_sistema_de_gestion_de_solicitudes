from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sgs.app.casos_de_uso as casos_de_uso
from sgs.models.orm import (
    Auditoria,
    Base,
    Notificacion,
    Proceso,
    Solicitud,
    SolicitudCambio,
    Usuario,
)

_TABLAS = [
    Usuario.__table__,
    Proceso.__table__,
    Solicitud.__table__,
    SolicitudCambio.__table__,
    Notificacion.__table__,
    Auditoria.__table__,
]


@pytest.fixture()
def session_factory(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLAS)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    with SessionLocal() as db:
        db.add_all([
            Usuario(id=1, codigo_sac="A1", username="admin", nombre="Admin", password_hash="x", rol="ADMINISTRADOR", activo=True),
            Usuario(id=2, codigo_sac="F1", username="func", nombre="Funcionaria", password_hash="x", rol="FUNCIONARIO", activo=True),
            Proceso(id=1, nombre="Traslado", descripcion="", activo=True),
            Proceso(id=2, nombre="Especialistas", descripcion="", activo=True),
            Solicitud(numero_solicitud_sac="S100", proceso_id=1, funcionario_id=2),
        ])
        db.commit()

    @contextmanager
    def get_session():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(casos_de_uso, "get_session", get_session)
    return SessionLocal


def test_solicitar_reasignacion_crea_cambio_y_notifica_admin(session_factory):
    cambio_id = casos_de_uso.solicitar_reasignacion_proceso("S100", 2, "Pertenece a Especialistas", usuario_id=2)
    assert cambio_id is not None

    # el admin ve la pendiente
    pendientes = casos_de_uso.listar_solicitudes_cambio_pendientes()
    assert len(pendientes) == 1
    assert pendientes[0]["numero_solicitud_sac"] == "S100"
    assert pendientes[0]["proceso_solicitado"] == "Especialistas"

    # el admin (id=1) recibió una notificación no leída
    assert casos_de_uso.contar_notificaciones_no_leidas(1) == 1


def test_solicitar_reasignacion_al_mismo_proceso_falla(session_factory):
    with pytest.raises(ValueError):
        casos_de_uso.solicitar_reasignacion_proceso("S100", 1, "motivo", usuario_id=2)


def test_solicitar_reasignacion_sin_motivo_falla(session_factory):
    with pytest.raises(ValueError):
        casos_de_uso.solicitar_reasignacion_proceso("S100", 2, "   ", usuario_id=2)


def test_aprobar_reasignacion_cambia_proceso_y_notifica_funcionario(session_factory):
    cambio_id = casos_de_uso.solicitar_reasignacion_proceso("S100", 2, "motivo", usuario_id=2)
    casos_de_uso.resolver_solicitud_cambio(cambio_id, aprobada=True, admin_id=1, observacion="Correcto")

    # la solicitud quedó en el proceso 2
    with session_factory() as db:
        solicitud = db.query(Solicitud).filter_by(numero_solicitud_sac="S100").one()
        assert solicitud.proceso_id == 2

    # ya no hay pendientes
    assert casos_de_uso.listar_solicitudes_cambio_pendientes() == []

    # el funcionario (id=2) ve su solicitud aprobada
    mias = casos_de_uso.listar_mis_solicitudes_cambio(2)
    assert len(mias) == 1
    assert mias[0]["estado"] == "aprobada"

    # el funcionario recibió notificación de aprobación
    assert casos_de_uso.contar_notificaciones_no_leidas(2) == 1


def test_rechazar_reasignacion_no_cambia_proceso_y_guarda_observacion(session_factory):
    cambio_id = casos_de_uso.solicitar_reasignacion_proceso("S100", 2, "motivo", usuario_id=2)
    casos_de_uso.resolver_solicitud_cambio(cambio_id, aprobada=False, admin_id=1, observacion="No procede")

    with session_factory() as db:
        solicitud = db.query(Solicitud).filter_by(numero_solicitud_sac="S100").one()
        assert solicitud.proceso_id == 1  # sin cambios

    mias = casos_de_uso.listar_mis_solicitudes_cambio(2)
    assert mias[0]["estado"] == "rechazada"
    assert mias[0]["observacion_admin"] == "No procede"


def test_marcar_notificaciones_leidas(session_factory):
    casos_de_uso.solicitar_reasignacion_proceso("S100", 2, "motivo", usuario_id=2)
    assert casos_de_uso.contar_notificaciones_no_leidas(1) == 1

    casos_de_uso.marcar_notificaciones_leidas(1)
    assert casos_de_uso.contar_notificaciones_no_leidas(1) == 0


def test_resolver_cambio_ya_resuelto_falla(session_factory):
    cambio_id = casos_de_uso.solicitar_reasignacion_proceso("S100", 2, "motivo", usuario_id=2)
    casos_de_uso.resolver_solicitud_cambio(cambio_id, aprobada=True, admin_id=1)
    with pytest.raises(ValueError):
        casos_de_uso.resolver_solicitud_cambio(cambio_id, aprobada=False, admin_id=1)
