import datetime as dt
from contextlib import contextmanager
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import sgs.app.casos_de_uso as casos_de_uso
from sgs.app.casos_de_uso import _nombre_ciudadano
from sgs.motores import motor_semaforo
from sgs.models.orm import (
    Base,
    CatalogoEps,
    Ciudadano,
    EnteControl,
    Festivo,
    ParametrosSemaforizacion,
    Proceso,
    ReglaTiemposEps,
    ReglaTiemposPrioridad,
    ReglaTiemposSolicitud,
    Respuesta,
    Solicitud,
    Traslado,
    Usuario,
)

_TABLAS_MEMORIA = [
    ParametrosSemaforizacion.__table__,
    Solicitud.__table__,
    CatalogoEps.__table__,
    ReglaTiemposEps.__table__,
    ReglaTiemposPrioridad.__table__,
    ReglaTiemposSolicitud.__table__,
    Festivo.__table__,
]

_TABLAS_MEMORIA_COMPLETA = [
    Solicitud.__table__,
    Ciudadano.__table__,
    Proceso.__table__,
    Usuario.__table__,
    Traslado.__table__,
    Respuesta.__table__,
    EnteControl.__table__,
    CatalogoEps.__table__,
    ReglaTiemposEps.__table__,
    ReglaTiemposPrioridad.__table__,
    ReglaTiemposSolicitud.__table__,
    Festivo.__table__,
]


def test_nombre_ciudadano_prioriza_el_ciudadano_registrado():
    solicitud = SimpleNamespace(doc_nombre="ANA DEL EXPORTE")
    ciudadano = SimpleNamespace(nombre="Ana Registrada")
    assert _nombre_ciudadano(ciudadano, solicitud) == "Ana Registrada"


def test_nombre_ciudadano_cae_al_nombre_del_exporte_sac():
    solicitud = SimpleNamespace(doc_nombre="ANA DEL EXPORTE")
    assert _nombre_ciudadano(None, solicitud) == "ANA DEL EXPORTE"


def test_nombre_ciudadano_usa_exporte_si_el_registro_esta_vacio():
    solicitud = SimpleNamespace(doc_nombre="ANA DEL EXPORTE")
    assert _nombre_ciudadano(SimpleNamespace(nombre="   "), solicitud) == "ANA DEL EXPORTE"


def _session_de_memoria():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLAS_MEMORIA)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    with SessionLocal() as db:
        db.add(
            Solicitud(
                numero_solicitud_sac="S100",
                sac_fecha_ingreso=dt.datetime(2026, 9, 8),
                sac_prioridad_caso="Riesgo simple",
                doc_eps="Savia Salud",
                sac_solicitud="Cita Primer Nivel",
                sac_motivo="Gestión",
                ciudadano_id=None,
                proceso_id=None,
            )
        )
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

    return get_session


def test_previsualizar_traslado_calcula_sin_guardar_y_semaforiza_fase_2(monkeypatch):
    monkeypatch.setattr(casos_de_uso, "get_session", _session_de_memoria())

    prev = casos_de_uso.previsualizar_traslado("S100", dt.date.today() + dt.timedelta(days=5))

    # Traslado elegido -> entra a FASE 2: el semáforo compara HOY contra la
    # fecha límite de respuesta recién calculada (regla por proceso/EPS).
    assert prev["semaforo"] == "A_TIEMPO"  # límite a ~10 días hábiles -> varios restantes
    assert prev["oportunidad_dias"] is not None
    assert prev["fecha_limite"]  # ISO no vacío
    assert prev["dias_restantes"] not in ("", None)


def _session_de_memoria_completa():
    """Misma convención que `_session_de_memoria` pero con las tablas que
    el listado/detalle cruzan (Proceso, Usuario, Traslado, Respuesta,
    EnteControl) y regla de prioridad sembrada para probar el semáforo."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLAS_MEMORIA_COMPLETA)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    hace = lambda dias: dt.datetime.combine(dt.date.today() - dt.timedelta(days=dias), dt.time.min)
    with SessionLocal() as db:
        db.add(
            ReglaTiemposPrioridad(
                id=1, prioridad_caso="Riesgo Vital", dias_habiles=1, es_dia_calendario=True
            )
        )
        db.add(
            Solicitud(
                numero_solicitud_sac="S-F1",
                sac_fecha_ingreso=hace(400),
                sac_prioridad_caso="Riesgo Vital",
                doc_eps="Savia Salud",
                sac_solicitud="Cita Primer Nivel",
                sac_motivo="Gestión",
                ciudadano_id=None,
                proceso_id=None,
            )
        )
        db.add(
            Solicitud(
                numero_solicitud_sac="S-RS",
                sac_fecha_ingreso=hace(100),
                sac_prioridad_caso="Riesgo simple",
                doc_eps="Savia Salud",
                sac_solicitud="Cita Primer Nivel",
                sac_motivo="Gestión",
                ciudadano_id=None,
                proceso_id=None,
            )
        )
        db.add(
            Solicitud(
                numero_solicitud_sac="S-R",
                sac_fecha_ingreso=hace(10),
                sac_prioridad_caso="Riesgo Vital",
                doc_eps="Savia Salud",
                sac_solicitud="Cita Primer Nivel",
                sac_motivo="Gestión",
                ciudadano_id=None,
                proceso_id=None,
            )
        )
        db.commit()

    with SessionLocal() as db:
        sac = db.execute(select(Solicitud).where(Solicitud.numero_solicitud_sac == "S-R")).scalar_one()
        db.add(Traslado(solicitud_id=sac.id, fecha_traslado=dt.date.today() - dt.timedelta(days=9)))
        db.add(EnteControl(solicitud_id=sac.id, radicado="RAD-1"))
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

    return get_session


def test_listado_semaforo_fase1_vencido_sin_fecha_de_traslado(monkeypatch):
    # Sin traslado la fase 1 usa la prioridad contra la FECHA ACTUAL:
    # ingresada hace 400 días con Riesgo Vital (1 día) -> VENCIDA.
    monkeypatch.setattr(casos_de_uso, "get_session", _session_de_memoria_completa())

    filas = casos_de_uso.obtener_solicitudes({}, None, "ADMINISTRADOR")
    f = next(f for f in filas if f["numero_solicitud_sac"] == "S-F1")
    assert f["semaforo"] == motor_semaforo.VENCIDO


def test_listado_semaforo_fase1_riesgo_simple_vencido_por_fallback(monkeypatch):
    # "Riesgo simple" sin reglas sembradas (solo hay Riesgo Vital) cae al
    # fallback de 10 días hábiles: ingresada hace 100 días -> VENCIDA.
    monkeypatch.setattr(casos_de_uso, "get_session", _session_de_memoria_completa())

    filas = casos_de_uso.obtener_solicitudes({}, None, "ADMINISTRADOR")
    f = next(f for f in filas if f["numero_solicitud_sac"] == "S-RS")
    assert f["semaforo"] == motor_semaforo.VENCIDO


def test_listado_y_detalle_semaforo_completado_por_radicado(monkeypatch):
    # Con radicado de ente de control registrado la solicitud se marca
    # COMPLETADA en listado y detalle, sin importar las fases.
    monkeypatch.setattr(casos_de_uso, "get_session", _session_de_memoria_completa())

    filas = casos_de_uso.obtener_solicitudes({}, None, "ADMINISTRADOR")
    f = next(f for f in filas if f["numero_solicitud_sac"] == "S-R")
    assert f["semaforo"] == motor_semaforo.COMPLETADO

    detalle = casos_de_uso.obtener_detalle_solicitud("S-R")
    assert detalle["semaforo"] == motor_semaforo.COMPLETADO
    assert detalle["radicado_ente_control"] == "RAD-1"


# ----------------------------------------------------------------------
# Orden del listado de Solicitudes (vista por defecto vs con criterios)
# ----------------------------------------------------------------------

def test_rango_urgencia_ordena_de_mas_a_menos_urgente():
    assert motor_semaforo.rango_urgencia(motor_semaforo.VENCIDO) < motor_semaforo.rango_urgencia(
        motor_semaforo.CERCA_DE_VENCIMIENTO
    )
    assert motor_semaforo.rango_urgencia(motor_semaforo.CERCA_DE_VENCIMIENTO) < motor_semaforo.rango_urgencia(
        motor_semaforo.A_TIEMPO
    )
    assert motor_semaforo.rango_urgencia(motor_semaforo.A_TIEMPO) < motor_semaforo.rango_urgencia(
        motor_semaforo.SIN_FECHA
    )
    assert motor_semaforo.rango_urgencia(motor_semaforo.SIN_FECHA) < motor_semaforo.rango_urgencia(
        motor_semaforo.COMPLETADO
    )
    # Código desconocido / None van al final (menos urgentes).
    assert motor_semaforo.rango_urgencia("XXX") > motor_semaforo.rango_urgencia(motor_semaforo.COMPLETADO)
    assert motor_semaforo.rango_urgencia(None) > motor_semaforo.rango_urgencia(motor_semaforo.COMPLETADO)


def test_listado_orden_por_defecto_prioriza_urgencia(monkeypatch):
    # Sin criterios: las urgentes (VENCIDO) primero, las COMPLETADAS al final.
    monkeypatch.setattr(casos_de_uso, "get_session", _session_de_memoria_completa())

    filas = casos_de_uso.obtener_solicitudes({}, None, "ADMINISTRADOR", hay_criterios=False)
    rangos = [motor_semaforo.rango_urgencia(f["semaforo"]) for f in filas]
    assert rangos == sorted(rangos)  # no decreciente = más urgente primero
    # La COMPLETADA (S-R) queda después de las VENCIDAS.
    assert filas[-1]["numero_solicitud_sac"] == "S-R"


def test_listado_orden_por_defecto_desempata_por_fecha_mas_antigua(monkeypatch):
    # S-F1 (hace 400 días) y S-RS (hace 100 días) son ambas VENCIDO: la
    # más antigua (S-F1) debe ir primero.
    monkeypatch.setattr(casos_de_uso, "get_session", _session_de_memoria_completa())

    filas = casos_de_uso.obtener_solicitudes({}, None, "ADMINISTRADOR", hay_criterios=False)
    numeros_vencidos = [f["numero_solicitud_sac"] for f in filas if f["semaforo"] == motor_semaforo.VENCIDO]
    assert numeros_vencidos.index("S-F1") < numeros_vencidos.index("S-RS")


def test_listado_con_criterios_ordena_por_fecha_descendente(monkeypatch):
    # Con criterios: fecha de ingreso descendente (más reciente primero),
    # sin importar el semáforo. S-R (hace 10) > S-RS (hace 100) > S-F1 (hace 400).
    monkeypatch.setattr(casos_de_uso, "get_session", _session_de_memoria_completa())

    filas = casos_de_uso.obtener_solicitudes({}, None, "ADMINISTRADOR", hay_criterios=True)
    numeros = [f["numero_solicitud_sac"] for f in filas]
    assert numeros == ["S-R", "S-RS", "S-F1"]


# ----------------------------------------------------------------------
# Helper de orden manual por clic (ordenar_filas)
# ----------------------------------------------------------------------

def test_ordenar_filas_por_semaforo_usa_urgencia_no_alfabetico():
    from sgs.ui.columnas_solicitudes import ordenar_filas

    filas = [
        {"semaforo": motor_semaforo.A_TIEMPO},
        {"semaforo": motor_semaforo.VENCIDO},
        {"semaforo": motor_semaforo.COMPLETADO},
    ]
    ordenadas = ordenar_filas(filas, "semaforo", descendente=False)
    assert [f["semaforo"] for f in ordenadas] == [
        motor_semaforo.VENCIDO,
        motor_semaforo.A_TIEMPO,
        motor_semaforo.COMPLETADO,
    ]
    # Descendente invierte el orden de urgencia.
    ordenadas_desc = ordenar_filas(filas, "semaforo", descendente=True)
    assert ordenadas_desc[0]["semaforo"] == motor_semaforo.COMPLETADO


def test_ordenar_filas_por_fecha_pone_vacios_al_final_en_ambas_direcciones():
    from sgs.ui.columnas_solicitudes import ordenar_filas

    filas = [
        {"fecha_ingreso": "2026-01-10"},
        {"fecha_ingreso": ""},
        {"fecha_ingreso": "2026-03-05"},
    ]
    asc = ordenar_filas(filas, "fecha_ingreso", descendente=False)
    assert [f["fecha_ingreso"] for f in asc] == ["2026-01-10", "2026-03-05", ""]
    desc = ordenar_filas(filas, "fecha_ingreso", descendente=True)
    assert [f["fecha_ingreso"] for f in desc] == ["2026-03-05", "2026-01-10", ""]


def test_ordenar_filas_por_texto_es_insensible_a_mayusculas():
    from sgs.ui.columnas_solicitudes import ordenar_filas

    filas = [
        {"nombre_ciudadano": "Zulema"},
        {"nombre_ciudadano": "ana"},
        {"nombre_ciudadano": "Bruno"},
    ]
    asc = ordenar_filas(filas, "nombre_ciudadano", descendente=False)
    assert [f["nombre_ciudadano"] for f in asc] == ["ana", "Bruno", "Zulema"]
