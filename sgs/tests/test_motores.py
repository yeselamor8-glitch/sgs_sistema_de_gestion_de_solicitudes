import datetime as dt

from sgs.motores.motor_clasificacion import Condicion, Operador, Regla, clasificar
from sgs.motores.motor_semaforo import AMARILLO, ROJO, VERDE, calcular_semaforo
from sgs.motores.motor_tiempos import ParametrosTiempo, calcular_fecha_limite, sumar_dias_habiles

FESTIVOS_2026 = {dt.date(2026, 1, 1), dt.date(2026, 12, 25)}


def test_riesgo_vital_es_un_dia_calendario():
    params = ParametrosTiempo(
        dias_por_solicitud={("Cita Primer Nivel", None): 3},
        dias_por_prioridad={"Riesgo Vital": 1, "Priorizado": 2},
        prioridad_es_calendario={"Riesgo Vital"},
        dias_por_eps={},
        festivos=FESTIVOS_2026,
    )
    fecha, regla = calcular_fecha_limite(
        dt.date(2026, 3, 10), "Riesgo Vital", "Savia Salud", "Cita Primer Nivel", params
    )
    assert fecha == dt.date(2026, 3, 11)
    assert regla.startswith("prioridad_calendario")


def test_eps_override_gana_sobre_solicitud():
    params = ParametrosTiempo(
        dias_por_solicitud={("Cita Especialista", None): 5},
        dias_por_prioridad={},
        prioridad_es_calendario=set(),
        dias_por_eps={"Savia Salud": 3},
        festivos=set(),
    )
    fecha, regla = calcular_fecha_limite(
        dt.date(2026, 3, 2), "Riesgo simple", "Savia Salud", "Cita Especialista", params
    )
    assert regla.startswith("eps:")
    assert fecha == sumar_dias_habiles(dt.date(2026, 3, 2), 3, set())


def test_fallback_diez_dias_cuando_solicitud_no_esta_en_tabla():
    params = ParametrosTiempo(
        dias_por_solicitud={("Cita Primer Nivel", None): 3},
        dias_por_prioridad={},
        prioridad_es_calendario=set(),
        dias_por_eps={},
        festivos=set(),
    )
    fecha, regla = calcular_fecha_limite(
        dt.date(2026, 3, 2), "N/A", "Nueva EPS", "Notificación", params
    )
    assert regla == "fallback_10_dias"


def test_reclamacion_usa_tiempo_especifico_no_el_general():
    # Cita Primer Nivel: 3 días en general, 15 si el motivo es Queja/Reclamación
    # (hallazgo maestra DISCAPACIDAD — el Excel original nunca llegaba a esta
    # fila por el bug de VLOOKUP; este motor sí la respeta)
    params = ParametrosTiempo(
        dias_por_solicitud={
            ("Cita Primer Nivel", None): 3,
            ("Cita Primer Nivel", "Queja"): 15,
        },
        dias_por_prioridad={},
        prioridad_es_calendario=set(),
        dias_por_eps={},
        festivos=set(),
    )
    fecha_gestion, regla_gestion = calcular_fecha_limite(
        dt.date(2026, 3, 2), "Riesgo simple", None, "Cita Primer Nivel", params, motivo="Gestión"
    )
    fecha_queja, regla_queja = calcular_fecha_limite(
        dt.date(2026, 3, 2), "Riesgo simple", None, "Cita Primer Nivel", params, motivo="Queja"
    )
    assert regla_gestion == "solicitud:Cita Primer Nivel"
    assert regla_queja.startswith("solicitud_reclamacion:")
    assert fecha_queja > fecha_gestion


def test_reclamacion_sin_fila_especifica_cae_a_la_general():
    params = ParametrosTiempo(
        dias_por_solicitud={("Traslado eps", None): 0},
        dias_por_prioridad={},
        prioridad_es_calendario=set(),
        dias_por_eps={},
        festivos=set(),
    )
    fecha, regla = calcular_fecha_limite(
        dt.date(2026, 3, 2), "N/A", None, "Traslado eps", params, motivo="Reclamación"
    )
    assert regla == "solicitud_mismo_dia:Traslado eps"
    assert fecha == dt.date(2026, 3, 2)


def test_semaforo_rojo_cuando_vencida():
    color = calcular_semaforo(dt.date(2026, 3, 10), dt.date(2026, 3, 5), set())
    assert color == ROJO


def test_semaforo_verde_con_tiempo_de_sobra():
    color = calcular_semaforo(dt.date(2026, 3, 1), dt.date(2026, 3, 10), set())
    assert color == VERDE


def test_clasificacion_especialistas_por_and_de_cuatro_condiciones():
    regla_especialistas = Regla(
        proceso_id=2,
        orden_evaluacion=100,
        tipo_regla="normal",
        condiciones=(
            Condicion("motivo", Operador.IGUAL_A, ("GESTIÓN EN ASEGURAMIENTO",)),
            Condicion("tipoasuntosol", Operador.IGUAL_A, ("Acceso a los servicios de salud",)),
            Condicion("solicitud", Operador.IGUAL_A, ("Cita Especialista", "Programación de procedimiento")),
            Condicion("epsvigentesg", Operador.IGUAL_A, ("Savia Salud",)),
        ),
    )
    datos = {
        "motivo": "Gestión en aseguramiento",
        "tipoasuntosol": "Acceso a los servicios de salud",
        "solicitud": "Cita Especialista",
        "epsvigentesg": "Savia Salud",
    }
    resultado = clasificar(datos, [regla_especialistas])
    assert resultado.estado == "clasificada"
    assert resultado.proceso_id == 2


def test_excepcion_ppna_gana_sobre_regla_normal_de_otras_eps():
    excepcion_ppna = Regla(
        proceso_id=16,  # MIGRANTES_IRREGULARES_PPNA
        orden_evaluacion=1,
        tipo_regla="excepcion",
        condiciones=(
            Condicion("tipoidentificacion", Operador.IGUAL_A, ("PO",)),
            Condicion("detalle", Operador.CONTIENE, ("medicina general",)),
        ),
    )
    regla_otras_eps = Regla(
        proceso_id=3,
        orden_evaluacion=100,
        tipo_regla="normal",
        condiciones=(
            Condicion("epsvigente", Operador.DISTINTO_DE, ("Savia Salud",)),
            Condicion("tipoidentificacion", Operador.DISTINTO_DE, ("PO",)),
        ),
    )
    datos = {
        "tipoidentificacion": "PO",
        "detalle": "Solicita cita de medicina general",
        "epsvigente": "Nueva EPS",
    }
    resultado = clasificar(datos, [excepcion_ppna, regla_otras_eps])
    assert resultado.estado == "clasificada"
    assert resultado.proceso_id == 16


def test_sin_clasificacion_cuando_ninguna_regla_aplica():
    regla = Regla(
        proceso_id=1,
        orden_evaluacion=100,
        tipo_regla="normal",
        condiciones=(Condicion("motivo", Operador.IGUAL_A, ("RECLAMACIÓN",)),),
    )
    resultado = clasificar({"motivo": "GESTIÓN EN ASEGURAMIENTO"}, [regla])
    assert resultado.estado == "sin_clasificar"
