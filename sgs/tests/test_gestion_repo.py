import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sgs.models.orm import Base, EnteControl, Respuesta, Solicitud, Traslado
from sgs.repos.gestion_solicitud_repo import GestionSolicitudRepo


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    # Solo las tablas que este repo toca -> evita chocar con tipos
    # específicos de PostgreSQL (ARRAY, JSONB) de otras tablas del modelo.
    Base.metadata.create_all(
        engine, tables=[Solicitud.__table__, Traslado.__table__, Respuesta.__table__, EnteControl.__table__]
    )
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Solicitud(numero_solicitud_sac="SAC-TEST-001"))
    db.commit()
    yield db
    db.close()


def test_actualiza_estado_y_observaciones_sin_tocar_bloque_sac(sesion):
    repo = GestionSolicitudRepo(sesion)
    repo.actualizar_gestion("SAC-TEST-001", {"estado_gestion": "Solucionada", "observaciones": "Listo"})
    sesion.commit()

    s = repo.obtener_por_numero_sac("SAC-TEST-001")
    assert s.estado_gestion == "Solucionada"
    assert s.observaciones == "Listo"


def test_asigna_funcionario_a_solicitud(sesion):
    repo = GestionSolicitudRepo(sesion)
    repo.actualizar_gestion("SAC-TEST-001", {"funcionario_id": 7})
    sesion.commit()

    solicitud = repo.obtener_por_numero_sac("SAC-TEST-001")
    assert solicitud.funcionario_id == 7


def test_crea_traslado_si_no_existia():
    pass  # cubierto abajo con fixture; placeholder para claridad de nombres


def test_upsert_traslado_crea_y_luego_actualiza(sesion):
    repo = GestionSolicitudRepo(sesion)
    repo.actualizar_gestion(
        "SAC-TEST-001", {"fecha_traslado": "2026-08-24", "institucion_competente": "Savia Salud"}
    )
    sesion.commit()

    s = repo.obtener_por_numero_sac("SAC-TEST-001")
    from sqlalchemy import select

    traslado = sesion.execute(select(Traslado).where(Traslado.solicitud_id == s.id)).scalar_one()
    assert traslado.fecha_traslado == dt.date(2026, 8, 24)
    assert traslado.institucion_competente == "Savia Salud"

    # segunda llamada -> debe actualizar la misma fila, no crear otra
    repo.actualizar_gestion("SAC-TEST-001", {"institucion_competente": "Nueva EPS"})
    sesion.commit()
    traslados = sesion.execute(select(Traslado).where(Traslado.solicitud_id == s.id)).scalars().all()
    assert len(traslados) == 1
    assert traslados[0].institucion_competente == "Nueva EPS"
    assert traslados[0].fecha_traslado == dt.date(2026, 8, 24)  # se conserva, no se borró


def test_upsert_respuesta_y_ente_control(sesion):
    repo = GestionSolicitudRepo(sesion)
    repo.actualizar_gestion(
        "SAC-TEST-001",
        {
            "hubo_respuesta": "NO",
            "respuesta_entidad": "",
            "radicado_ente_control": "202608-RC-00456",
            "entidad_control": "Supersalud",
            "fecha_reporte_control": "2026-09-01",
        },
    )
    sesion.commit()

    s = repo.obtener_por_numero_sac("SAC-TEST-001")
    from sqlalchemy import select

    respuesta = sesion.execute(select(Respuesta).where(Respuesta.solicitud_id == s.id)).scalar_one()
    assert respuesta.hubo_respuesta == "NO"

    ente = sesion.execute(select(EnteControl).where(EnteControl.solicitud_id == s.id)).scalar_one()
    assert ente.radicado == "202608-RC-00456"
    assert ente.fecha_reporte == dt.date(2026, 9, 1)


def test_solicitud_inexistente_lanza_error_claro(sesion):
    repo = GestionSolicitudRepo(sesion)
    with pytest.raises(ValueError, match="SAC-NO-EXISTE"):
        repo.actualizar_gestion("SAC-NO-EXISTE", {"estado_gestion": "Solucionada"})


def test_traslado_persiste_campos_calculados_de_tiempos(sesion):
    repo = GestionSolicitudRepo(sesion)
    repo.actualizar_gestion(
        "SAC-TEST-001",
        {
            "fecha_traslado": "2026-08-24",
            "fecha_limite_respuesta": "2026-08-28",
            "oportunidad_dias_habiles": 2,
            "indicador_oportunidad": "CERCA_DE_VENCIMIENTO",
        },
    )
    sesion.commit()

    solicitud = repo.obtener_por_numero_sac("SAC-TEST-001")
    from sqlalchemy import select

    traslado = sesion.execute(select(Traslado).where(Traslado.solicitud_id == solicitud.id)).scalar_one()
    assert traslado.fecha_limite_respuesta == dt.date(2026, 8, 28)
    assert traslado.oportunidad_dias_habiles == 2
    assert traslado.indicador_oportunidad == "CERCA_DE_VENCIMIENTO"


def test_traslado_acepta_fecha_limite_como_date_no_solo_str(sesion):
    """Regresión: el caso de uso entrega fecha_limite_respuesta como
    datetime.date (lo calcula el motor) y el repo debe perseguirlo sin
    lanzar en strptime."""
    repo = GestionSolicitudRepo(sesion)
    repo.actualizar_gestion(
        "SAC-TEST-001",
        {
            "fecha_traslado": "2026-08-24",
            "fecha_limite_respuesta": dt.date(2026, 8, 28),
            "oportunidad_dias_habiles": 2,
            "indicador_oportunidad": "CERCA_DE_VENCIMIENTO",
        },
    )
    sesion.commit()

    solicitud = repo.obtener_por_numero_sac("SAC-TEST-001")
    from sqlalchemy import select

    traslado = sesion.execute(select(Traslado).where(Traslado.solicitud_id == solicitud.id)).scalar_one()
    assert traslado.fecha_limite_respuesta == dt.date(2026, 8, 28)


def test_estado_sac_escribible_como_estado_operativo(sesion):
    repo = GestionSolicitudRepo(sesion)
    repo.actualizar_gestion("SAC-TEST-001", {"estado_sac": "Solucionada"})
    sesion.commit()

    solicitud = repo.obtener_por_numero_sac("SAC-TEST-001")
    assert solicitud.sac_estado == "Solucionada"


def test_respuesta_persiste_decision_y_oportunidad_calculadas(sesion):
    """El repo persiste decision/oportunidad_respuesta tal como los entrega el
    caso de uso (ya resueltos por el motor); no los calcula él."""
    repo = GestionSolicitudRepo(sesion)
    repo.actualizar_gestion(
        "SAC-TEST-001",
        {
            "hubo_respuesta": "SI",
            "fecha_respuesta": "2026-08-26",
            "decision": "CERRAR_SAC",
            "oportunidad_respuesta": "OPORTUNA",
        },
    )
    sesion.commit()

    solicitud = repo.obtener_por_numero_sac("SAC-TEST-001")
    from sqlalchemy import select

    respuesta = sesion.execute(select(Respuesta).where(Respuesta.solicitud_id == solicitud.id)).scalar_one()
    assert respuesta.decision == "CERRAR_SAC"
    assert respuesta.oportunidad_respuesta == "OPORTUNA"


def test_obtener_fecha_limite_respuesta_lee_el_traslado_vigente(sesion):
    repo = GestionSolicitudRepo(sesion)
    repo.actualizar_gestion(
        "SAC-TEST-001", {"fecha_traslado": "2026-08-24", "fecha_limite_respuesta": "2026-08-28"}
    )
    sesion.commit()

    assert repo.obtener_fecha_limite_respuesta("SAC-TEST-001") == dt.date(2026, 8, 28)
    assert repo.obtener_fecha_limite_respuesta("SAC-TEST-NO-EXISTE") is None