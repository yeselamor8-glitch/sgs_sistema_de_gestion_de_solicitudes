from sgs.motores.motor_importacion_sac import _normalizar_numero_solicitud, detectar_duplicados


def test_detectar_duplicados_revela_numero_repetido_y_ya_existente():
    filas = [
        {"numerosolicitud": "SAC-100", "fechasolicitud": "2026-09-01", "motivo": "Gestión", "tipoasuntosol": "A", "solicitud": "X"},
        {"numerosolicitud": "SAC-100", "fechasolicitud": "2026-09-01", "motivo": "Gestión", "tipoasuntosol": "A", "solicitud": "X"},
        {"numerosolicitud": "SAC-200", "fechasolicitud": "2026-09-01", "motivo": "Gestión", "tipoasuntosol": "A", "solicitud": "Y"},
    ]
    existentes = {"SAC-200": {"motivo": "Gestión"}}

    archivos, registrados = detectar_duplicados(filas, existentes)

    assert archivos == ["SAC-100"]
    assert registrados == ["SAC-200"]


def test_normalizar_numero_solicitud_elimina_excel_float_0():
    assert _normalizar_numero_solicitud(12345.0) == "12345"
    assert _normalizar_numero_solicitud("12345.0") == "12345"
    assert _normalizar_numero_solicitud("12345/0") == "12345"
