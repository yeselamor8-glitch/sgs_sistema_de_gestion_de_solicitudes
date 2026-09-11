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
]

# Tabla "por solicitud" — la misma que analizamos en las 18 maestras
# idénticas (motivo=NULL -> regla general), más los overrides de
# Reclamación/Queja encontrados en la maestra DISCAPACIDAD.
REGLAS_TIEMPOS_SOLICITUD = [
    ("Cita Primer Nivel", None, 3),
    ("Autorización especialista", None, 10),
    ("Autorización procedimiento", None, 10),
    ("Cambio ips", None, 5),
    ("Entrega de medicamento", None, 3),
    ("Otra autorización", None, 10),
    ("Cita Especialista", None, 5),
    ("Programación de procedimiento", None, 5),
    ("Traslado eps", None, 0),
    ("Traslado municipio", None, 0),
    ("Cambio de régimen", None, 0),
    ("Disminución o cambio de nivel", None, 15),
    ("Inconsistencia en documento", None, 15),
    ("Acreditación de permanencia", None, 15),
    ("Urgentes y prioritarios", None, 2),
    # Overrides Reclamación/Queja (hallazgo maestra DISCAPACIDAD — el
    # Excel original nunca los alcanzaba por el bug del VLOOKUP)
    ("Cita Primer Nivel", "Queja", 15),
    ("Autorización especialista", "Queja", 15),
    ("Portabilidad – Línea telefónica", "Queja", 15),
    ("Traslado eps", "Queja", 15),
    ("Cambio de régimen", "Queja", 15),
]

REGLAS_TIEMPOS_PRIORIDAD = [
    ("Riesgo Vital", 1, True),   # día calendario
    ("Priorizado", 2, False),    # días hábiles
]

# nombre EPS -> días hábiles. Coosalud=5 confirmado por el usuario
# (adoptando el valor de la maestra OTRAS_EPS sobre las otras 18).
REGLAS_TIEMPOS_EPS = [
    ("Savia Salud", 3),
    ("Suramericana", 3),
    ("Coosalud", 5),
    ("Sanitas", 3),
    ("Salud Total", 3),
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
    existentes = {
        (r.solicitud, r.motivo) for r in db.execute(select(ReglaTiemposSolicitud)).scalars()
    }
    creados = 0
    for solicitud, motivo, dias in REGLAS_TIEMPOS_SOLICITUD:
        if (solicitud, motivo) not in existentes:
            db.add(ReglaTiemposSolicitud(solicitud=solicitud, motivo=motivo, dias_habiles=dias))
            creados += 1
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

    existentes_eps = {e.nombre: e for e in db.execute(select(CatalogoEps)).scalars()}
    for nombre, _dias in REGLAS_TIEMPOS_EPS:
        if nombre not in existentes_eps:
            eps = CatalogoEps(nombre=nombre, activo=True)
            db.add(eps)
            db.flush()
            existentes_eps[nombre] = eps

    existentes_reglas = {r.eps_id for r in db.execute(select(ReglaTiemposEps)).scalars()}
    creados = 0
    for nombre, dias in REGLAS_TIEMPOS_EPS:
        eps_id = existentes_eps[nombre].id
        if eps_id not in existentes_reglas:
            db.add(ReglaTiemposEps(eps_id=eps_id, dias_habiles=dias))
            creados += 1
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