"""
Siembra inicial de datos para poder empezar a probar el sistema con
PostgreSQL real.

Uso:
    export SGS_DB_URL="postgresql+psycopg://usuario:clave@localhost:5432/sgs_local"
    PYTHONPATH=. python3 scripts/seed_inicial.py

Es SEGURO ejecutarlo más de una vez: usa upsert (verifica si ya existe
antes de crear) en vez de insertar a ciegas.
"""
from __future__ import annotations

import datetime as dt
import sys

# Blindaje para Windows: algunas consolas (PowerShell con code page
# cp1252) truenan con UnicodeEncodeError si el script imprime tildes
# o símbolos fuera de ese charset. Forzamos UTF-8 en la salida.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from sqlalchemy import select

from sgs.config.db import get_session
from sgs.models.orm import (
    Proceso,
    ReglaTiemposEps,
    ReglaTiemposPrioridad,
    ReglaTiemposSolicitud,
    Usuario,
)
from sgs.motores import motor_auth

PROCESOS = [
    ("ACCESO_SERVICIOS_SALUD", "Acceso a los servicios de salud (Savia Salud, base)"),
    ("ACCESO_SERVICIOS_SALUD_ESPECIALISTAS", "Acceso a servicios de salud — especialistas (Savia Salud)"),
    ("ACCESO_SERVICIOS_SALUD_OTRAS_EPS", "Acceso a servicios de salud — otras EPS"),
    ("ACCESO_SERVICIOS_SALUD_SURA_EPS", "Acceso a servicios de salud — Sura EPS (filtro pendiente de definir)"),
    ("ACREDITACION_PERMANENCIA", "Acreditación de permanencia"),
    ("AFILIACIONES", "Afiliaciones — subclasificación Excepcional"),
    ("AFILIACIONES_INFO", "Afiliaciones — información/orientación"),
    ("AFILIACIONES_TRANSACCIONALES", "Afiliaciones — subclasificación Transaccional"),
    ("DISMINUCION_NIVEL", "Disminución o cambio de nivel"),
    ("LISTADO_CENSAL", "Listado censal / población especial"),
    ("NOVEDAD_DOCUMENTOS", "Inconsistencia en documento"),
    ("PORTABILIDADES", "Portabilidad"),
    ("SALUD_PUBLICA", "Salud pública (excluye Discapacidad)"),
    ("SOAT", "SOAT / tránsito / accidente"),
    ("DISCAPACIDAD", "Discapacidad"),
    ("MIGRANTES_IRREGULARES_PPNA", "Migrantes irregulares / PPNA (tipoidentificacion=PO)"),
    ("MOVILIDAD", "Movilidad (cambio de régimen)"),
    ("RECLAMACIONES", "Reclamaciones y quejas"),
    ("TRASLADO", "Traslado (EPS/municipio)"),
    ("URGENTES_Y_PRIORITARIOS", "Urgentes y prioritarios"),
    ("SIN_CLASIFICACION", "Sin clasificación — destino por defecto de las solicitudes que ninguna regla clasifica"),
]

# ----------------------------------------------------------------------
# Reglas de tiempo POR PROCESO — extraídas de las 20 maestras 2026.
#
# 18 procesos comparten la MISMA tabla "por solicitud" (verificada: los
# checks T17C=5, T36C=10 y T51C=15 coinciden en las 18 base) + las 5 EPS
# con Coosalud=5 (valor adoptado de OTRAS_EPS a las otras 17, decisión del
# usuario). DISCAPACIDAD tiene SU PROPIA tabla (valores distintos en
# accesos, traslados y prioridades) + solo 2 EPS + overrides Reclamación/
# Queja de 15 días.
# ----------------------------------------------------------------------

# Los 18 procesos con la tabla base (todos excepto DISCAPACIDAD).
PROCESOS_BASE = [nombre for nombre, _ in PROCESOS if nombre != "DISCAPACIDAD"]

# Tabla "por solicitud" compartida por los 18 procesos base (maestra ACCESO).
REGLAS_TIEMPOS_SOLICITUD_BASE = [
    ("Inscripción", 10),
    ("Inscripción por contribución solidaria", 10),
    ("Institucional", 10),
    ("Afiliación excepcional", 10),
    ("Verificación", 0),
    ("Aceptación contribución solidaria", 10),
    ("Disminución o cambio de nivel", 15),
    ("Acreditación de permanencia", 1),
    ("Novedad con planillas - Contribución solidaria", 10),
    ("Inconsistencia en documento", 10),
    ("Incapacidad", 0),
    ("Suspensión por Mora", 0),
    ("Autorización medicamento", 5),
    ("Autorización procedimiento", 5),
    ("Autorización especialista", 5),
    ("Autorización Primer Nivel", 5),
    ("Otra autorización", 5),
    ("Autorización No POS", 5),
    ("Cambio ips", 5),
    ("Cita Primer Nivel", 5),
    ("Cita Especialista", 5),
    ("Programación de procedimiento", 5),
    ("Entrega de medicamento", 5),
    ("Novedad copago", 5),
    ("Historia clínica", 5),
    ("Urgentes y prioritarios", 5),
    ("Mlas prácticas", 15),
    ("Trato deshumanizado", 15),
    ("Agresión", 15),
    ("Entrega no pos", 5),
    ("Línea telefónica", 10),
    ("Pagina web", 10),
    ("Correo", 10),
    ("Discapacidad", 15),
    ("Eventos de interés en Salud Publica", 2),
    ("Servicio Social Complementario", 0),
    ("Servicio Social Para acceder a servicios de salud", 0),
    ("Servicio Social que sustituye el servicio de salud", 0),
    ("Resoluciones Vigentes", 0),
    ("Repatriados", 10),
    ("Otro", 0),
    ("N/A", 0),
    ("Traslado eps", 15),
    ("Traslado municipio", 15),
    ("Cambio de régimen", 15),
]

# Tabla "por solicitud" PROPIA de DISCAPACIDAD (maestra DISCAPACIDAD).
REGLAS_TIEMPOS_SOLICITUD_DISCAPACIDAD = [
    ("Inscripción", 10),
    ("Inscripción por contribución solidaria", 10),
    ("Institucional", 10),
    ("Afiliación excepcional", 10),
    ("Verificación", 0),
    ("Aceptación contribución solidaria", 10),
    ("Disminución o cambio de nivel", 15),
    ("Acreditación de permanencia", 1),
    ("Novedad con planillas - Contribución solidaria", 10),
    ("Inconsistencia en documento", 10),
    ("Incapacidad", 0),
    ("Suspensión por Mora", 0),
    ("Autorización medicamento", 3),
    ("Autorización procedimiento", 10),
    ("Autorización especialista", 10),
    ("Autorización Primer Nivel", 10),
    ("Otra autorización", 10),
    ("Autorización No POS", 10),
    ("Cambio ips", 10),
    ("Cita Primer Nivel", 3),
    ("Cita Especialista", 10),
    ("Programación de procedimiento", 10),
    ("Entrega de medicamento", 3),
    ("Novedad copago", 0),
    ("Historia clínica", 0),
    ("Entrega no pos", 3),
    ("Línea telefónica", 10),
    ("Pagina web", 10),
    ("Correo", 10),
    ("Cambio de régimen", 0),
    ("Traslado eps", 0),
    ("Traslado municipio", 0),
    ("Discapacidad", 15),
    ("Eventos de interés en Salud Publica", 2),
    ("Servicio Social Complementario", 0),
    ("Servicio Social Para acceder a servicios de salud", 0),
    ("Servicio Social que sustituye el servicio de salud", 0),
    ("Resoluciones Vigentes", 0),
    ("Repatriados", 10),
    ("Otro", 0),
    ("N/A", 0),
]

# Overrides Reclamación/Queja de DISCAPACIDAD (bloque T47-T66 de la
# maestra): 15 días para estas solicitudes cuando el motivo es una
# reclamación o queja (la columna D de la maestra).
OVERRIDES_DISCAPACIDAD = [
    "Línea telefónica",
    "Pagina web",
    "Correo",
    "Autorización especialista",
    "Autorización medicamento",
    "Cambio ips",
    "Autorización Primer Nivel",
    "Cita Primer Nivel",
    "Programación de procedimiento",
    "Entrega de medicamento",
    "Historia clínica",
    "Autorización No POS",
    "Novedad copago",
    "Urgentes y prioritarios",
    "Traslado eps",
    "Traslado municipio",
    "Cambio de régimen",
    "Mlas prácticas",
    "Trato deshumanizado",
    "Agresión",
]

REGLAS_TIEMPOS_PRIORIDAD = [
    ("Riesgo Vital", 1, True),   # día calendario
    ("Priorizado", 2, False),    # días hábiles
]

# nombre EPS -> días hábiles. Los 18 procesos base adoptan el valor de la
# maestra OTRAS_EPS (Coosalud=5) sobre las otras 17 (decisión del usuario).
REGLAS_TIEMPOS_EPS_BASE = [
    ("Savia Salud", 3),
    ("Suramericana EPS", 3),
    ("Coosalud", 5),
    ("Sanitas", 3),
    ("Salud Total", 3),
]

# DISCAPACIDAD: la maestra solo define 2 EPS (Savia Salud y Suramericana).
REGLAS_TIEMPOS_EPS_DISCAPACIDAD = [
    ("Savia Salud", 3),
    ("Suramericana EPS", 3),
]

FESTIVOS_2026 = [
    "2026-01-01", "2026-01-12", "2026-03-23", "2026-04-02", "2026-04-03",
    "2026-05-01", "2026-05-18", "2026-06-08", "2026-06-15", "2026-06-29",
    "2026-07-20", "2026-08-07", "2026-08-17", "2026-10-12", "2026-11-02",
    "2026-11-16", "2026-12-08", "2026-12-25",
]


def sembrar_procesos(db) -> None:
    existentes = {p.nombre for p in db.execute(select(Proceso)).scalars()}
    for nombre, descripcion in PROCESOS:
        if nombre not in existentes:
            db.add(Proceso(nombre=nombre, descripcion=descripcion, activo=True))
    print(f"Procesos: {len(PROCESOS)} verificados/creados.")


def sembrar_tiempos_solicitud(db) -> None:
    procesos_por_nombre = {p.nombre: p for p in db.execute(select(Proceso)).scalars()}
    existentes = {
        (r.proceso_id, r.solicitud, r.motivo) for r in db.execute(select(ReglaTiemposSolicitud)).scalars()
    }
    creados = 0

    def agregar(proceso_id: int, solicitud: str, motivo, dias: int) -> None:
        nonlocal creados
        if (proceso_id, solicitud, motivo) not in existentes:
            db.add(ReglaTiemposSolicitud(proceso_id=proceso_id, solicitud=solicitud, motivo=motivo, dias_habiles=dias))
            creados += 1

    for nombre in PROCESOS_BASE:
        proceso = procesos_por_nombre.get(nombre)
        if proceso is None:
            print(f"  [!] Proceso no encontrado, se omite: {nombre}")
            continue
        for solicitud, dias in REGLAS_TIEMPOS_SOLICITUD_BASE:
            agregar(proceso.id, solicitud, None, dias)

    discapacidad = procesos_por_nombre.get("DISCAPACIDAD")
    if discapacidad is not None:
        for solicitud, dias in REGLAS_TIEMPOS_SOLICITUD_DISCAPACIDAD:
            agregar(discapacidad.id, solicitud, None, dias)
        for solicitud in OVERRIDES_DISCAPACIDAD:
            agregar(discapacidad.id, solicitud, "Queja", 15)

    print(f"Reglas de tiempo por solicitud: {creados} nuevas creadas.")


def sembrar_tiempos_prioridad(db) -> None:
    existentes = {r.prioridad_caso for r in db.execute(select(ReglaTiemposPrioridad)).scalars()}
    creados = 0
    for prioridad, dias, es_calendario in REGLAS_TIEMPOS_PRIORIDAD:
        if prioridad not in existentes:
            db.add(
                ReglaTiemposPrioridad(
                    prioridad_caso=prioridad, dias_habiles=dias, es_dia_calendario=es_calendario
                )
            )
            creados += 1
    print(f"Reglas de tiempo por prioridad: {creados} nuevas creadas.")


def sembrar_tiempos_eps(db) -> None:
    from sgs.models.orm import CatalogoEps

    procesos_por_nombre = {p.nombre: p for p in db.execute(select(Proceso)).scalars()}

    existentes_eps = {e.nombre: e for e in db.execute(select(CatalogoEps)).scalars()}

    def _eps_id(nombre: str) -> int:
        nonlocal existentes_eps
        eps = existentes_eps.get(nombre)
        if eps is None:
            eps = CatalogoEps(nombre=nombre, activo=True)
            db.add(eps)
            db.flush()
            existentes_eps[nombre] = eps
        return eps.id

    existentes_reglas = {(r.proceso_id, r.eps_id) for r in db.execute(select(ReglaTiemposEps)).scalars()}
    creados = 0

    def agregar(proceso_id: int, eps_nombre: str, dias: int) -> None:
        nonlocal creados
        eps_id = _eps_id(eps_nombre)
        if (proceso_id, eps_id) not in existentes_reglas:
            db.add(ReglaTiemposEps(proceso_id=proceso_id, eps_id=eps_id, dias_habiles=dias))
            creados += 1

    for nombre in PROCESOS_BASE:
        proceso = procesos_por_nombre.get(nombre)
        if proceso is None:
            continue
        for eps_nombre, dias in REGLAS_TIEMPOS_EPS_BASE:
            agregar(proceso.id, eps_nombre, dias)

    discapacidad = procesos_por_nombre.get("DISCAPACIDAD")
    if discapacidad is not None:
        for eps_nombre, dias in REGLAS_TIEMPOS_EPS_DISCAPACIDAD:
            agregar(discapacidad.id, eps_nombre, dias)

    print(f"Catálogo EPS + reglas de tiempo por EPS: {creados} reglas nuevas creadas.")


def sembrar_festivos(db) -> None:
    from sgs.models.orm import Festivo

    existentes = {f.fecha for f in db.execute(select(Festivo)).scalars()}
    creados = 0
    for fecha_str in FESTIVOS_2026:
        fecha = dt.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha not in existentes:
            db.add(Festivo(fecha=fecha, descripcion="Festivo 2026"))
            creados += 1
    print(f"Festivos: {creados} nuevos creados.")


def sembrar_usuario_admin(db) -> None:
    existente = db.execute(select(Usuario).where(Usuario.username == "admin")).scalar_one_or_none()
    if existente:
        print("Usuario 'admin' ya existe — no se crea de nuevo.")
        return
    admin = Usuario(
        codigo_sac=None,
        username="admin",
        nombre="Administrador",
        rol="ADMINISTRADOR",
        password_hash=motor_auth.hashear_password("CambiarEsta123"),
        activo=True,
    )
    db.add(admin)
    print("Usuario 'admin' creado con contraseña temporal 'CambiarEsta123' — cámbiala después de entrar.")


def sembrar_usuario_funcionario(db) -> None:
    existente = db.execute(select(Usuario).where(Usuario.username == "funcionario")).scalar_one_or_none()
    if existente:
        print("Usuario 'funcionario' ya existe — no se crea de nuevo.")
        return
    db.add(
        Usuario(
            codigo_sac="FUNC-001",
            username="funcionario",
            nombre="Funcionario de prueba",
            rol="FUNCIONARIO",
            password_hash=motor_auth.hashear_password("Funcionario123"),
            activo=True,
        )
    )
    print("Usuario 'funcionario' creado con contraseña temporal 'Funcionario123'.")


def sembrar_parametros_generales(db) -> None:
    from sgs.repos.parametro_general_repo import ParametroGeneralRepo

    repo = ParametroGeneralRepo(db)
    existentes = repo.listar()
    if "nombre_entidad" not in existentes:
        repo.guardar("nombre_entidad", "Alcaldía de Medellín — Secretaría de Salud", "Nombre mostrado en la aplicación")
    if "dias_fallback_tiempo_respuesta" not in existentes:
        repo.guardar("dias_fallback_tiempo_respuesta", "10", "Días hábiles por defecto cuando ninguna regla de tiempos aplica")
    print("Parámetros generales: verificados/creados.")


def main() -> None:
    with get_session() as db:
        sembrar_usuario_admin(db)
        sembrar_usuario_funcionario(db)
        sembrar_procesos(db)
        sembrar_tiempos_solicitud(db)
        sembrar_tiempos_prioridad(db)
        sembrar_tiempos_eps(db)
        sembrar_festivos(db)
        sembrar_reglas_clasificacion(db)
        sembrar_parametros_generales(db)
    print("\nListo. Ya puedes iniciar sesión con usuario 'admin'.")


# =====================================================================
# Reglas de clasificación reales — extraídas directamente del código
# Python (pandas) que generaba las 20 maestras desde el exporte SAC.
# Fuente de verdad definitiva (más precisa que el instructivo inicial).
#
# Formato: (proceso_nombre, tipo_regla, orden, [(campo, operador, [valores]), ...])
# Varias reglas para el mismo proceso = OR entre reglas (se usan cuando
# el filtro original tenía un OR entre columnas distintas, algo que una
# sola regla AND no puede expresar).
# =====================================================================

REGLAS_CLASIFICACION = [
    ("ACCESO_SERVICIOS_SALUD_ESPECIALISTAS", "normal", 100, [
        ("motivo", "igual_a", ["GESTIÓN EN ASEGURAMIENTO"]),
        ("tipoasuntosol", "igual_a", ["Acceso a los servicios de salud"]),
        ("solicitud", "igual_a", ["Cita Especialista", "Programación de procedimiento"]),
        ("epsvigentesg", "igual_a", ["Savia Salud"]),
    ]),
    ("DISMINUCION_NIVEL", "normal", 100, [
        ("motivo", "igual_a", ["GESTIÓN EN ASEGURAMIENTO", "INFORMACIÓN", "INFORMACIÓN / ORIENTACION"]),
        ("tipoasuntosol", "igual_a", ["Régimen Subsidiado", "Régimen Contributivo"]),
        ("solicitud", "igual_a", ["Disminución o cambio de nivel"]),
    ]),
    ("NOVEDAD_DOCUMENTOS", "normal", 100, [
        ("motivo", "igual_a", ["GESTIÓN EN ASEGURAMIENTO", "INFORMACIÓN", "INFORMACIÓN / ORIENTACION"]),
        ("tipoasuntosol", "igual_a", ["Régimen Subsidiado", "Régimen Contributivo"]),
        ("solicitud", "igual_a", ["Inconsistencia en documento"]),
    ]),
    ("AFILIACIONES_TRANSACCIONALES", "normal", 100, [
        ("motivo", "igual_a", ["GESTIÓN EN ASEGURAMIENTO"]),
        ("tipoasuntosol", "igual_a", ["Afiliación al Régimen contributivo", "Afiliación al Régimen subsidiado"]),
        ("solicitud", "igual_a", ["Inscripción", "Inscripción por contribución solidaria"]),
        ("subclasificacion", "igual_a", ["Transaccional"]),
    ]),
    ("AFILIACIONES", "normal", 100, [
        ("motivo", "igual_a", ["GESTIÓN EN ASEGURAMIENTO"]),
        ("tipoasuntosol", "igual_a", ["Afiliación al Régimen contributivo", "Afiliación al Régimen subsidiado"]),
        ("solicitud", "igual_a", ["Inscripción", "Inscripción por contribución solidaria"]),
        ("subclasificacion", "igual_a", ["Excepcional"]),
    ]),
    ("AFILIACIONES_INFO", "normal", 100, [
        ("motivo", "igual_a", ["INFORMACIÓN", "INFORMACIÓN / ORIENTACION"]),
        ("tipoasuntosol", "igual_a", ["Afiliación al Régimen contributivo", "Afiliación al Régimen subsidiado"]),
        ("solicitud", "igual_a", ["Inscripción", "Inscripción por contribución solidaria", "Institucional", "Verificación", "Aceptación contribución solidaria"]),
    ]),
    ("MIGRANTES_IRREGULARES_PPNA", "excepcion", 1, [
        ("tipoidentificacion", "igual_a", ["PO"]),
    ]),
    ("MOVILIDAD", "normal", 100, [
        ("tipoasuntosol", "igual_a", ["Movilidad"]),
    ]),
    ("TRASLADO", "normal", 100, [
        ("tipoasuntosol", "igual_a", ["Traslado"]),
    ]),
    ("DISCAPACIDAD", "normal", 100, [
        ("tipoasuntosol", "igual_a", ["Salud Pública"]),
        ("solicitud", "igual_a", ["Discapacidad"]),
    ]),
    ("ACCESO_SERVICIOS_SALUD", "normal", 100, [
        ("motivo", "igual_a", ["GESTIÓN EN ASEGURAMIENTO"]),
        ("tipoasuntosol", "igual_a", ["Acceso a los servicios de salud"]),
        ("solicitud", "igual_a", ["Autorización especialista", "Autorización procedimiento", "Cambio ips", "Cita Primer Nivel", "Entrega de medicamento", "Otra autorización", "IPS"]),
        ("epsvigentesg", "igual_a", ["Savia Salud"]),
    ]),
    ("SALUD_PUBLICA", "normal", 100, [
        ("tipoasuntosol", "igual_a", ["Salud Pública"]),
        ("solicitud", "igual_a", ["Eventos de interés en Salud Publica"]),
    ]),
    # SOAT: 4 reglas (mismo proceso) porque el filtro original busca el
    # texto en CUALQUIERA de las 4 columnas actuacionfuncionario1..4 —
    # un OR entre columnas distintas, que una sola regla AND no expresa.
    ("SOAT", "normal", 100, [
        ("grupopoblacional", "igual_a", ["26"]),
        ("actuacionfuncionario1", "contiene", ["SOAT", "TRANSITO", "ACCIDENTE"]),
    ]),
    ("SOAT", "normal", 100, [
        ("grupopoblacional", "igual_a", ["26"]),
        ("actuacionfuncionario2", "contiene", ["SOAT", "TRANSITO", "ACCIDENTE"]),
    ]),
    ("SOAT", "normal", 100, [
        ("grupopoblacional", "igual_a", ["26"]),
        ("actuacionfuncionario3", "contiene", ["SOAT", "TRANSITO", "ACCIDENTE"]),
    ]),
    ("SOAT", "normal", 100, [
        ("grupopoblacional", "igual_a", ["26"]),
        ("actuacionfuncionario4", "contiene", ["SOAT", "TRANSITO", "ACCIDENTE"]),
    ]),
    ("RECLAMACIONES", "normal", 100, [
        ("motivo", "igual_a", ["RECLAMACIÓN", "QUEJAS"]),
    ]),
    ("PORTABILIDADES", "normal", 100, [
        ("tipoasuntosol", "igual_a", ["Portabilidad"]),
    ]),
    ("ACCESO_SERVICIOS_SALUD_OTRAS_EPS", "normal", 100, [
        ("epsvigentesg", "distinto_de", ["Savia Salud", "Suramericana EPS"]),
        ("tipoasuntosol", "igual_a", ["Acceso a los servicios de salud"]),
        ("motivo", "igual_a", ["GESTIÓN EN ASEGURAMIENTO"]),
        ("tipoidentificacion", "distinto_de", ["PO"]),
    ]),
    ("LISTADO_CENSAL", "normal", 100, [
        ("tipoasuntosol", "igual_a", ["Listado población especial", "Listado censal"]),
    ]),
    ("ACREDITACION_PERMANENCIA", "normal", 100, [
        ("solicitud", "igual_a", ["Acreditación de permanencia"]),
    ]),
    # Urgentes y prioritarios: 2 reglas (mismo proceso) porque el filtro
    # original es OR entre 'solicitud' y 'subclasificacion'.
    ("URGENTES_Y_PRIORITARIOS", "normal", 100, [
        ("solicitud", "igual_a", ["Urgentes y prioritarios"]),
    ]),
    ("URGENTES_Y_PRIORITARIOS", "normal", 100, [
        ("subclasificacion", "igual_a", ["Urgentes y prioritarios"]),
    ]),
    ("ACCESO_SERVICIOS_SALUD_SURA_EPS", "normal", 100, [
        ("epsvigentesg", "igual_a", ["Suramericana EPS"]),
        ("tipoasuntosol", "igual_a", ["Acceso a los servicios de salud"]),
        ("motivo", "igual_a", ["GESTIÓN EN ASEGURAMIENTO"]),
        ("tipoidentificacion", "distinto_de", ["PO"]),
    ]),
]


def sembrar_reglas_clasificacion(db) -> None:
    from sgs.repos.reglas_repo import ReglaClasificacionRepo

    repo = ReglaClasificacionRepo(db)
    procesos_por_nombre = {p.nombre: p for p in db.execute(select(Proceso)).scalars()}

    decision_por_proceso: dict[int, bool] = {}  # proceso.id -> ¿omitir? (ya tenía reglas)
    procesos_omitidos: set[int] = set()
    creadas = 0

    for proceso_nombre, tipo_regla, orden, condiciones in REGLAS_CLASIFICACION:
        proceso = procesos_por_nombre.get(proceso_nombre)
        if proceso is None:
            print(f"  [!] Proceso no encontrado, se omite regla: {proceso_nombre}")
            continue

        if proceso.id not in decision_por_proceso:
            decision_por_proceso[proceso.id] = repo.proceso_tiene_reglas(proceso.id)

        if decision_por_proceso[proceso.id]:
            procesos_omitidos.add(proceso.id)
            continue

        repo.crear_regla(proceso.id, tipo_regla, orden, [(c, o, v) for c, o, v in condiciones])
        creadas += 1

    print(f"Reglas de clasificación: {creadas} creadas, {len(procesos_omitidos)} procesos ya tenían reglas (omitidos).")


if __name__ == "__main__":
    main()