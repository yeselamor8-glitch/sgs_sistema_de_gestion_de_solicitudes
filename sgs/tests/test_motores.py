import datetime as dt

from sgs.motores.motor_clasificacion import Condicion, Operador, Regla, clasificar
from sgs.motores.motor_semaforo import (
    A_TIEMPO,
    CERCA_DE_VENCIMIENTO,
    COMPLETADO,
    SIN_FECHA,
    VENCIDO,
    calcular_semaforo,
    calcular_semaforo_solicitud,
)
from sgs.motores.motor_tiempos import (
    ParametrosTiempo,
    calcular_bloque_respuesta,
    calcular_bloque_traslado,
    calcular_decision,
    calcular_edad,
    calcular_fecha_limite,
    calcular_oportunidad_respuesta,
    calcular_oportunidad_traslado,
    indicador_oportunidad_traslado,
    sumar_dias_habiles,
)

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


def test_semaforo_rojo_cuando_indicador_es_vencido():
    assert calcular_semaforo("VENCIDO") == VENCIDO


def test_semaforo_amarillo_cuando_indicador_es_cerca_de_vencimiento():
    assert calcular_semaforo("CERCA_DE_VENCIMIENTO") == CERCA_DE_VENCIMIENTO


def test_semaforo_blanco_cuando_indicador_es_a_tiempo():
    assert calcular_semaforo("A_TIEMPO") == A_TIEMPO


def test_semaforo_sin_fecha_limite_es_sin_fecha():
    # Sin indicador (aún no hay traslado registrado) no se puede evaluar:
    # en lugar de un color falso se usa el estado gris.
    assert calcular_semaforo(None) == SIN_FECHA
    assert calcular_semaforo("") == SIN_FECHA
    assert calcular_semaforo("INDICADOR_DESCONOCIDO") == SIN_FECHA


# ----------------------------------------------------------------------
# Semaforización de la solicitud (fases 1/2 + COMPLETADO, contra la fecha actual)
# ----------------------------------------------------------------------

_PARAMS_PRIORIDAD = ParametrosTiempo(
    dias_por_solicitud={},
    dias_por_prioridad={"Riesgo Vital": 1, "Priorizado": 2, "No prioritario": 10},
    prioridad_es_calendario={"Riesgo Vital"},
    dias_por_eps={},
    festivos=set(),
)


def test_semaforo_solicitud_completado_cuando_hubo_respuesta_si():
    # La respuesta SI tiene precedencia sobre las dos fases.
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 9, 13),
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=dt.date(2026, 8, 13),
            fecha_limite_respuesta=dt.date(2026, 8, 20),
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
            hubo_respuesta="SI",
        )
        == COMPLETADO
    )


def test_semaforo_solicitud_completado_cuando_hay_radicado_de_ente_control():
    # Radicado presente => se remitió al ente de control => completada.
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 9, 13),
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=None,
            fecha_limite_respuesta=None,
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
            hubo_respuesta="NO",
            radicado_ente_control="RAD-987",
        )
        == COMPLETADO
    )


def test_semaforo_solicitud_completado_cuando_estado_gestion_es_solucionada():
    # Marcar la solicitud como "Solucionada" (listado/detalle) también la
    # deja en COMPLETADO aunque no haya respuesta SI ni radicado.
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 9, 13),
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=None,
            fecha_limite_respuesta=None,
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
            estado_gestion="Solucionada",
        )
        == COMPLETADO
    )


def test_semaforo_solicitud_fase1_riesgo_vital_vencida_por_fecha_actual():
    # Ejemplo del negocio: ingreso 12-ago, Riesgo Vital (1 día calendario
    # para trasladar) y HOY 13-sep => la fase 1 debe marcar VENCIDA.
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 9, 13),
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=None,
            fecha_limite_respuesta=None,
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
        )
        == VENCIDO
    )


def test_semaforo_solicitud_fase1_vence_hoy_es_cerca():
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 8, 13),
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=None,
            fecha_limite_respuesta=None,
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
        )
        == CERCA_DE_VENCIMIENTO
    )


def test_semaforo_solicitud_fase1_a_tiempo_con_prioridad_de_dias_habiles():
    # Priorizado = 2 días hábiles; "No prioritario" = 10. Recién ingresada
    # y HOY = fecha de ingreso -> quedan varios días -> blanco.
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 3, 2),
            fecha_ingreso=dt.date(2026, 3, 2),
            fecha_traslado=None,
            fecha_limite_respuesta=None,
            prioridad_caso="No prioritario",
            parametros=_PARAMS_PRIORIDAD,
        )
        == A_TIEMPO
    )


def test_semaforo_solicitud_fase1_prioridad_desconocida_usa_fallback():
    # Sin regla de prioridad ni EPS/solicitud conocidos la fase 1 cae al
    # fallback (10 días hábiles): el plazo existe, ya no es SIN_FECHA.
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 9, 13),
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=None,
            fecha_limite_respuesta=None,
            prioridad_caso="Sin regla",
            parametros=_PARAMS_PRIORIDAD,
        )
        == VENCIDO
    )


def test_semaforo_solicitud_fase1_riesgo_simple_usa_dias_habiles_del_proceso():
    # "Riesgo simple" no tiene días propios en la maestra: la fase 1 usa
    # los tiempos de respuesta de su proceso (EPS Savia Salud = 3 días
    # hábiles), igual que la fase 2.
    params = ParametrosTiempo(
        dias_por_solicitud={},
        dias_por_prioridad={"Riesgo Vital": 1, "Priorizado": 2},
        prioridad_es_calendario={"Riesgo Vital"},
        dias_por_eps={"Savia Salud": 3},
        festivos=set(),
    )
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 3, 2),
            fecha_ingreso=dt.date(2026, 3, 2),
            fecha_traslado=None,
            fecha_limite_respuesta=None,
            prioridad_caso="Riesgo simple",
            eps="Savia Salud",
            solicitud="Cita Primer Nivel",
            parametros=params,
        )
        == A_TIEMPO
    )
    # Pasada la fecha límite (ingreso + 3 hábiles = 05-mar) -> vencida.
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 3, 6),
            fecha_ingreso=dt.date(2026, 3, 2),
            fecha_traslado=None,
            fecha_limite_respuesta=None,
            prioridad_caso="Riesgo simple",
            eps="Savia Salud",
            solicitud="Cita Primer Nivel",
            parametros=params,
        )
        == VENCIDO
    )


def test_semaforo_solicitud_fase1_sin_fecha_ingreso_es_sin_fecha():
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 9, 13),
            fecha_ingreso=None,
            fecha_traslado=None,
            fecha_limite_respuesta=None,
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
        )
        == SIN_FECHA
    )


def test_semaforo_solicitud_fase2_a_tiempo_vs_fecha_limite_de_respuesta():
    hoy = dt.date(2026, 9, 14)
    assert (
        calcular_semaforo_solicitud(
            hoy,
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=dt.date(2026, 8, 13),
            fecha_limite_respuesta=hoy + dt.timedelta(days=10),
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
        )
        == A_TIEMPO
    )


def test_semaforo_solicitud_fase2_vencida_tras_la_fecha_limite():
    hoy = dt.date(2026, 9, 14)
    assert (
        calcular_semaforo_solicitud(
            hoy,
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=dt.date(2026, 8, 13),
            fecha_limite_respuesta=hoy - dt.timedelta(days=3),
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
        )
        == VENCIDO
    )


def test_semaforo_solicitud_fase2_cerca_cuando_vence_hoy_o_manana():
    hoy = dt.date(2026, 9, 14)
    # vence HOY -> 0 días hábiles restantes -> cerca
    assert (
        calcular_semaforo_solicitud(
            hoy,
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=dt.date(2026, 8, 13),
            fecha_limite_respuesta=hoy,
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
        )
        == CERCA_DE_VENCIMIENTO
    )
    # vence el siguiente día hábil -> 1 día restante -> cerca
    assert (
        calcular_semaforo_solicitud(
            hoy,
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=dt.date(2026, 8, 13),
            fecha_limite_respuesta=sumar_dias_habiles(hoy, 1, set()),
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
        )
        == CERCA_DE_VENCIMIENTO
    )


def test_semaforo_solicitud_umbral_cerca_configurable():
    hoy = dt.date(2026, 9, 14)
    # Faltan 3 días hábiles para la fecha límite.
    fecha_limite = sumar_dias_habiles(hoy, 3, set())

    # Con el umbral por defecto (1): 3 días restantes -> aún A_TIEMPO.
    assert (
        calcular_semaforo_solicitud(
            hoy,
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=dt.date(2026, 8, 13),
            fecha_limite_respuesta=fecha_limite,
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
        )
        == A_TIEMPO
    )

    # Con umbral configurado en 3: los mismos 3 días restantes -> CERCA.
    assert (
        calcular_semaforo_solicitud(
            hoy,
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=dt.date(2026, 8, 13),
            fecha_limite_respuesta=fecha_limite,
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
            dias_habiles_cerca=3,
        )
        == CERCA_DE_VENCIMIENTO
    )


def test_semaforo_solicitud_fase2_sin_fecha_limite_es_sin_fecha():
    assert (
        calcular_semaforo_solicitud(
            dt.date(2026, 9, 14),
            fecha_ingreso=dt.date(2026, 8, 12),
            fecha_traslado=dt.date(2026, 8, 13),
            fecha_limite_respuesta=None,
            prioridad_caso="Riesgo Vital",
            parametros=_PARAMS_PRIORIDAD,
        )
        == SIN_FECHA
    )


def test_oportunidad_traslado_mismo_dia_es_cero():
    assert calcular_oportunidad_traslado(dt.date(2026, 3, 2), dt.date(2026, 3, 2), set()) == 0


def test_oportunidad_traslado_dia_habil_siguiente_es_uno():
    assert calcular_oportunidad_traslado(dt.date(2026, 3, 2), dt.date(2026, 3, 3), set()) == 1


def test_oportunidad_traslado_cuenta_dias_habiles_y_excluye_fines_de_semana():
    # Lunes -> miércoles: martes y miércoles hábiles = 2
    assert calcular_oportunidad_traslado(dt.date(2026, 3, 2), dt.date(2026, 3, 4), set()) == 2
    # Viernes -> lunes siguiente: solo lunes = 1
    assert calcular_oportunidad_traslado(dt.date(2026, 3, 6), dt.date(2026, 3, 9), set()) == 1


def test_oportunidad_traslado_excluye_festivos():
    festivos = {dt.date(2026, 3, 5)}
    # Miércoles -> viernes con jueves festivo: solo viernes = 1
    assert calcular_oportunidad_traslado(dt.date(2026, 3, 4), dt.date(2026, 3, 6), festivos) == 1


def test_indicador_oportunidad_traslado():
    assert indicador_oportunidad_traslado(0) == "A_TIEMPO"
    assert indicador_oportunidad_traslado(1) == "A_TIEMPO"
    assert indicador_oportunidad_traslado(2) == "CERCA_DE_VENCIMIENTO"
    assert indicador_oportunidad_traslado(3) == "VENCIDO"


def test_calcular_bloque_traslado_computa_fecha_limite_oportunidad_e_indicador():
    params = ParametrosTiempo(
        dias_por_solicitud={("Cita Primer Nivel", None): 3},
        dias_por_prioridad={"Priorizado": 2},
        prioridad_es_calendario={"Riesgo Vital"},
        dias_por_eps={},
        festivos=set(),
    )
    bloque = calcular_bloque_traslado(
        dt.date(2026, 3, 2),  # fecha de ingreso
        dt.date(2026, 3, 4),  # fecha de traslado
        "Riesgo simple",
        None,
        "Cita Primer Nivel",
        "Gestión",
        params,
    )
    assert bloque["fecha_limite"] == sumar_dias_habiles(dt.date(2026, 3, 4), 3, set())
    assert bloque["oportunidad_dias"] == 2
    assert bloque["indicador_oportunidad"] == "CERCA_DE_VENCIMIENTO"


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


# ----------------------------------------------------------------------
# Cadena de tiempos: decisión y oportunidad de la respuesta
# ----------------------------------------------------------------------

def test_decision_si_cierra_sac():
    assert calcular_decision("SI") == "CERRAR_SAC"


def test_decision_no_remite_a_ente_de_control():
    assert calcular_decision("NO") == "REMITIR_ENTE_CONTROL"


def test_decision_na_o_vacio_es_na():
    assert calcular_decision("N_A") == "N_A"
    assert calcular_decision("") == "N_A"
    assert calcular_decision(None) == "N_A"


def test_oportunidad_respuesta_dentro_del_limite_es_oportuna():
    assert calcular_oportunidad_respuesta("SI", dt.date(2026, 3, 5), dt.date(2026, 3, 10)) == "OPORTUNA"


def test_oportunidad_respuesta_el_mismo_dia_del_limite_es_oportuna():
    assert calcular_oportunidad_respuesta("SI", dt.date(2026, 3, 10), dt.date(2026, 3, 10)) == "OPORTUNA"


def test_oportunidad_respuesta_tardia_es_inoportuna():
    assert calcular_oportunidad_respuesta("SI", dt.date(2026, 3, 12), dt.date(2026, 3, 10)) == "INOPORTUNA"


def test_oportunidad_respuesta_no_es_no_hubo_respuesta():
    assert calcular_oportunidad_respuesta("NO", None, None) == "NO_HUBO_RESPUESTA"


def test_oportunidad_respuesta_si_sin_datos_completos_es_inconsistente():
    assert calcular_oportunidad_respuesta("SI", None, dt.date(2026, 3, 10)) == "INCONSISTENTE"
    assert calcular_oportunidad_respuesta("SI", dt.date(2026, 3, 5), None) == "INCONSISTENTE"


def test_oportunidad_respuesta_na_es_inconsistente():
    assert calcular_oportunidad_respuesta("N_A", None, None) == "INCONSISTENTE"


def test_oportunidad_respuesta_antes_del_traslado_es_inconsistente():
    # Caso AK<AB de la maestra: una respuesta con fecha anterior al traslado
    # no se compara contra la límite; los datos son inconsistentes.
    assert (
        calcular_oportunidad_respuesta("SI", dt.date(2026, 3, 3), dt.date(2026, 3, 20), dt.date(2026, 3, 5))
        == "INCONSISTENTE"
    )


def test_oportunidad_respuesta_despues_del_traslado_sigue_comparando_contra_la_limite():
    # Respuesta posterior al traslado pero dentro de la límite -> OPORTUNA.
    assert (
        calcular_oportunidad_respuesta("SI", dt.date(2026, 3, 10), dt.date(2026, 3, 20), dt.date(2026, 3, 5))
        == "OPORTUNA"
    )


def test_calcular_bloque_respuesta_computa_decision_y_oportunidad():
    bloque = calcular_bloque_respuesta("SI", dt.date(2026, 3, 5), dt.date(2026, 3, 10))
    assert bloque == {"decision": "CERRAR_SAC", "oportunidad_respuesta": "OPORTUNA"}

    bloque_no = calcular_bloque_respuesta("NO", None, None)
    assert bloque_no == {"decision": "REMITIR_ENTE_CONTROL", "oportunidad_respuesta": "NO_HUBO_RESPUESTA"}


# ----------------------------------------------------------------------
# Edad calculada
# ----------------------------------------------------------------------

def test_edad_calcula_anios_cumplidos():
    assert calcular_edad(dt.date(1990, 3, 10), dt.date(2026, 3, 9)) == 35
    assert calcular_edad(dt.date(1990, 3, 10), dt.date(2026, 3, 10)) == 36


def test_edad_sin_fecha_nacimiento_es_none():
    assert calcular_edad(None) is None


def test_edad_con_fecha_futura_es_cero():
    assert calcular_edad(dt.date(2030, 1, 1), dt.date(2026, 1, 1)) == 0
