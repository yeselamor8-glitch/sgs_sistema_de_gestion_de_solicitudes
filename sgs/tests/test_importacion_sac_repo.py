import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from sgs.models.orm import Base, Ciudadano, Solicitud
from sgs.repos.gestion_solicitud_repo import GestionSolicitudRepo
from sgs.repos.importacion_sac_repo import ImportacionSacRepo


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Solicitud.__table__, Ciudadano.__table__])
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


def _fila_sac(numero: str, estado: str) -> dict:
    return {
        "numerosolicitud": numero,
        "fechasolicitud": "2026-01-10",
        "motivo": "Gestión en aseguramiento",
        "tipoasuntosol": "Acceso",
        "solicitud": "Cita Primer Nivel",
        "estadosolicitud": estado,
    }


def test_reimportacion_no_sobrescribe_estado_sac_editado_en_app(sesion):
    repo = ImportacionSacRepo(sesion)
    repo.crear_o_actualizar_solicitud(_fila_sac("S001", "En trámite"), "S001", None, "clasificada")
    sesion.commit()

    # La app gestiona el estado desde el detalle y lo cambia
    GestionSolicitudRepo(sesion).actualizar_gestion("S001", {"estado_sac": "Solucionada"})
    sesion.commit()

    # Reimportación: SAC "actualizó" el mismo número con otro estado
    fila_reimportada = _fila_sac("S001", "Sin respuesta")
    fila_reimportada["estado"] = "Sin respuesta"
    repo.crear_o_actualizar_solicitud(fila_reimportada, "S001", None, "clasificada")
    sesion.commit()

    solicitud = sesion.execute(
        select(Solicitud).where(Solicitud.numero_solicitud_sac == "S001")
    ).scalar_one()
    assert solicitud.sac_estado == "Solucionada"


def test_importacion_nueva_guarda_estado_sac_del_archivo(sesion):
    repo = ImportacionSacRepo(sesion)
    repo.crear_o_actualizar_solicitud(_fila_sac("S002", "En trámite"), "S002", None, "clasificada")
    sesion.commit()

    solicitud = sesion.execute(
        select(Solicitud).where(Solicitud.numero_solicitud_sac == "S002")
    ).scalar_one()
    assert solicitud.sac_estado == "En trámite"


def test_importacion_mapea_encabezados_reales_del_exporte_sac(sesion):
    """El exporte SAC usa emailnoidentificado, mpioorigensg,
    regimenafvigentesg y epsvigentesg; esos nombres deben poblar los campos
    doc_* (y el correo/ciudadano) para que el Detalle los muestre."""
    repo = ImportacionSacRepo(sesion)
    fila = {
        "numerosolicitud": "S003",
        "fechasolicitud": "2026-01-10",
        "motivo": "Gestión en aseguramiento",
        "tipoasuntosol": "Acceso",
        "solicitud": "Cita Primer Nivel",
        "estado": "En trámite",
        "tipodocumento": "CC",
        "numerodocumento": "12345",
        "emailnoidentificado": "ciudadano@correo.com",
        "mpioorigensg": "Bogotá",
        "regimenafvigentesg": "Contributivo",
        "epsvigentesg": "Savia Salud",
    }
    repo.crear_o_actualizar_solicitud(fila, "S003", None, "clasificada")
    sesion.commit()

    solicitud = sesion.execute(
        select(Solicitud).where(Solicitud.numero_solicitud_sac == "S003")
    ).scalar_one()
    assert solicitud.doc_correo == "ciudadano@correo.com"
    assert solicitud.doc_municipio_origen == "Bogotá"
    assert solicitud.doc_regimen == "Contributivo"
    assert solicitud.doc_eps == "Savia Salud"

    ciudadano = sesion.execute(
        select(Ciudadano).where(Ciudadano.numero_documento == "12345")
    ).scalar_one()
    assert ciudadano.correo == "ciudadano@correo.com"


def test_importacion_con_codigos_numericos_de_municipio_no_viola_fk(sesion):
    """El exporte SAC trae codigompio como número; con los catálogos vacíos
    la importación no debe crashear: los *_id quedan NULL y el código se
    conserva en los campos doc_* (visibles en el Detalle)."""
    repo = ImportacionSacRepo(sesion)
    fila = {
        "numerosolicitud": "S004",
        "fechasolicitud": "2026-01-10",
        "motivo": "Gestión en aseguramiento",
        "tipoasuntosol": "Acceso",
        "solicitud": "Cita Primer Nivel",
        "estado": "En trámite",
        "tipodocumento": "CC",
        "numerodocumento": "88888",
        "codigompio": "1",
        "mpioorigensg": "05001",
        "regimenafvigentesg": "Contributivo",
        "epsvigentesg": "Savia Salud",
    }
    repo.crear_o_actualizar_solicitud(fila, "S004", None, "clasificada")
    sesion.commit()

    solicitud = sesion.execute(
        select(Solicitud).where(Solicitud.numero_solicitud_sac == "S004")
    ).scalar_one()
    assert solicitud.doc_municipio_residencia == "1"
    assert solicitud.doc_municipio_origen == "05001"
    assert solicitud.doc_regimen == "Contributivo"
    assert solicitud.doc_eps == "Savia Salud"

    ciudadano = sesion.execute(
        select(Ciudadano).where(Ciudadano.numero_documento == "88888")
    ).scalar_one()
    assert ciudadano.municipio_origen_id is None
    assert ciudadano.municipio_residencia_id is None
    assert ciudadano.regimen_id is None
    assert ciudadano.eps_id is None