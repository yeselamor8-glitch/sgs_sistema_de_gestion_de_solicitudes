from sgs.motores.motor_clasificacion import Condicion, Operador, Regla
from sgs.motores.motor_importacion_sac import (
    ResumenImportacion,
    procesar_archivo,
    procesar_fila,
    validar_estructura,
)
from sgs.repos.importacion_sac_repo import _valor_fecha

REGLA_ESPECIALISTAS = Regla(
    proceso_id=2,
    orden_evaluacion=100,
    tipo_regla="normal",
    condiciones=(
        Condicion("motivo", Operador.IGUAL_A, ("Gestión en aseguramiento",)),
        Condicion("solicitud", Operador.IGUAL_A, ("Cita Especialista",)),
    ),
)


def _fila(numero="SAC-001", **overrides):
    base = {
        "numerosolicitud": numero,
        "fechasolicitud": "2026-09-01",
        "motivo": "Gestión en aseguramiento",
        "tipoasuntosol": "Acceso a los servicios de salud",
        "solicitud": "Cita Especialista",
    }
    base.update(overrides)
    return base


def test_validar_estructura_detecta_columnas_faltantes():
    faltantes = validar_estructura(["numerosolicitud", "fechasolicitud", "motivo"])
    assert "tipoasuntosol" in faltantes
    assert "solicitud" in faltantes


def test_convierte_fecha_serial_de_excel_a_date():
    assert _valor_fecha(37225.0).isoformat() == "2001-11-30"
    assert _valor_fecha("2026-09-10").isoformat() == "2026-09-10"


def test_validar_estructura_ok_cuando_estan_todas():
    encabezados = ["numerosolicitud", "fechasolicitud", "motivo", "tipoasuntosol", "solicitud", "otra_col"]
    assert validar_estructura(encabezados) == []


def test_fila_sin_numero_es_error():
    resultado = procesar_fila(_fila(numero=""), {}, [REGLA_ESPECIALISTAS])
    assert resultado.accion == "error"


def test_fila_sin_campo_requerido_es_error():
    resultado = procesar_fila(_fila(motivo=""), {}, [REGLA_ESPECIALISTAS])
    assert resultado.accion == "error"
    assert any("motivo" in e for e in resultado.errores)


def test_fila_nueva_cuando_no_existe():
    resultado = procesar_fila(_fila(), {}, [REGLA_ESPECIALISTAS])
    assert resultado.accion == "nuevo"
    assert resultado.clasificacion_estado == "clasificada"
    assert resultado.proceso_id == 2


def test_fila_sin_cambios_cuando_es_identica_a_la_existente():
    fila = _fila()
    existentes = {"SAC-001": dict(fila)}
    resultado = procesar_fila(fila, existentes, [REGLA_ESPECIALISTAS])
    assert resultado.accion == "sin_cambios"


def test_fila_actualizada_cuando_cambia_un_campo_sac():
    fila_nueva = _fila(detalle="Nuevo detalle relevante")
    existentes = {"SAC-001": _fila(detalle="Detalle viejo")}
    resultado = procesar_fila(fila_nueva, existentes, [REGLA_ESPECIALISTAS])
    assert resultado.accion == "actualizado"


def test_fila_sin_clasificar_cuando_ninguna_regla_aplica():
    resultado = procesar_fila(_fila(solicitud="Otra cosa"), {}, [REGLA_ESPECIALISTAS])
    assert resultado.clasificacion_estado == "sin_clasificar"
    assert resultado.proceso_id is None


def test_procesar_archivo_resume_conteos_correctamente():
    filas = [
        _fila("SAC-001"),  # nueva, clasificada
        _fila("SAC-002", solicitud="Otra cosa"),  # nueva, sin clasificar
        _fila(numero=""),  # error
    ]
    existentes = {}
    resumen = procesar_archivo(filas, existentes, [REGLA_ESPECIALISTAS])
    assert isinstance(resumen, ResumenImportacion)
    assert resumen.total == 3
    assert resumen.nuevos == 2  # las 2 filas con número válido, sin existente previo
    assert resumen.errores == 1
    assert resumen.sin_clasificar == 1