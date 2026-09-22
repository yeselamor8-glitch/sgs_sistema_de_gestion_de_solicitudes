import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from sgs.app.casos_de_uso import _fila_solicitud
from sgs.models.orm import (
    Base,
    Ciudadano,
    EnteControl,
    Proceso,
    Respuesta,
    Solicitud,
    Traslado,
    Usuario,
)
from sgs.repos.solicitud_repo import SolicitudRepo

TABLAS = [
    Solicitud.__table__,
    Ciudadano.__table__,
    Proceso.__table__,
    Usuario.__table__,
    Traslado.__table__,
    Respuesta.__table__,
    EnteControl.__table__,
]


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=TABLAS)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Usuario(username="u1", nombre="Admin", password_hash="x", rol="ADMINISTRADOR"))
    db.add(Proceso(id=1, nombre="RECLAMACIONES"))
    db.add(
        Solicitud(
            numero_solicitud_sac="S001",
            doc_nombre="Ana Gómez",
            doc_numero_documento="1001",
            sac_fecha_ingreso=dt.datetime(2026, 3, 2),
        )
    )
    db.add(
        Solicitud(
            numero_solicitud_sac="S002",
            doc_nombre="Luis Pérez",
            doc_numero_documento="2002",
            proceso_id=1,
            sac_fecha_ingreso=dt.datetime(2026, 6, 1),
        )
    )
    db.commit()
    yield db
    db.close()


def test_listar_por_nombre_usa_doc_cuando_no_hay_ciudadano(sesion):
    repo = SolicitudRepo(sesion)
    filas = repo.listar_con_filtros({"nombre": "ana"})
    assert [f["solicitud"].numero_solicitud_sac for f in filas] == ["S001"]


def test_fila_solicitud_fallback_doc_nombre_y_documento(sesion):
    solicitud = sesion.execute(
        select(Solicitud).where(Solicitud.numero_solicitud_sac == "S001")
    ).scalar_one()
    fila = _fila_solicitud(
        {
            "solicitud": solicitud,
            "ciudadano": None,
            "proceso": None,
            "funcionario": None,
            "traslado": None,
            "respuesta": None,
        }
    )
    assert fila["nombre_ciudadano"] == "Ana Gómez"
    assert fila["documento"] == "1001"


def test_contar_total_y_con_filtros(sesion):
    repo = SolicitudRepo(sesion)
    assert repo.contar({}) == 2
    assert repo.contar({"numero": "S002"}) == 1
    assert repo.contar({"proceso": "RECLAMACIONES"}) == 1
    assert repo.contar({"fecha_desde": "2026-01-01", "fecha_hasta": "2026-03-31"}) == 1