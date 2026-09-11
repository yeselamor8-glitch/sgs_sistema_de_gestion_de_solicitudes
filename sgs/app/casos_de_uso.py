"""
Capa de aplicación — casos de uso. Es la ÚNICA capa que la futura UI
(PySide6, Fase 5) debe llamar. Nunca expone sesiones de SQLAlchemy ni
modelos ORM directamente a la UI: recibe/devuelve tipos simples.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sgs.config.db import get_session
from sgs.motores import motor_auth, motor_clasificacion, motor_importacion_sac, motor_semaforo, motor_tiempos
from sgs.motores.lector_archivo_sac import leer_archivo_sac
from sgs.repos.gestion_solicitud_repo import GestionSolicitudRepo
from sgs.repos.importacion_sac_repo import ImportacionSacRepo
from sgs.repos.reglas_repo import ReglaClasificacionRepo, ReglaTiemposRepo
from sgs.repos.solicitud_repo import SolicitudRepo
from sgs.repos.usuario_repo import UsuarioRepo
from sgs.repos.vista_columnas_repo import VistaColumnasRepo


@dataclass(frozen=True)
class ResultadoAutenticacion:
    ok: bool
    usuario_id: int | None = None
    username: str | None = None
    nombre: str | None = None
    rol: str | None = None
    mensaje_error: str | None = None


def autenticar(username: str, password: str) -> ResultadoAutenticacion:
    """
    Único punto de entrada de login para la UI. Nunca expone
    password_hash ni el objeto Usuario de SQLAlchemy hacia afuera.
    """
    username = (username or "").strip()
    if not username or not password:
        return ResultadoAutenticacion(ok=False, mensaje_error="Ingresa usuario y contraseña.")

    with get_session() as db:
        usuario = UsuarioRepo(db).obtener_por_username(username)
        if usuario is None:
            # mismo mensaje que "contraseña incorrecta" a propósito:
            # no revelar si el usuario existe o no
            return ResultadoAutenticacion(ok=False, mensaje_error="Usuario o contraseña incorrectos.")

        if not motor_auth.verificar_password(password, usuario.password_hash):
            return ResultadoAutenticacion(ok=False, mensaje_error="Usuario o contraseña incorrectos.")

        return ResultadoAutenticacion(
            ok=True, usuario_id=usuario.id, username=usuario.username, nombre=usuario.nombre, rol=usuario.rol
        )


def clasificar_solicitud(datos_sac: dict[str, str | None]) -> motor_clasificacion.ResultadoClasificacion:
    """
    Clasifica una solicitud SAC contra las reglas activas.
    `datos_sac` trae las claves crudas del exporte SAC (motivo,
    tipoasuntosol, solicitud, detalle, tipoidentificacion, ...).
    """
    with get_session() as db:
        reglas = ReglaClasificacionRepo(db).listar_reglas_activas()
    return motor_clasificacion.clasificar(datos_sac, reglas)


def calcular_tiempos_y_semaforo(
    fecha_traslado: dt.date,
    prioridad_caso: str | None,
    eps: str | None,
    solicitud: str | None,
    festivos: set[dt.date],
    hoy: dt.date | None = None,
) -> dict:
    """Devuelve fecha límite, la regla que se usó, y el color de semáforo vigente hoy."""
    hoy = hoy or dt.date.today()
    with get_session() as db:
        parametros = ReglaTiemposRepo(db).cargar_parametros(festivos)

    fecha_limite, regla_aplicada = motor_tiempos.calcular_fecha_limite(
        fecha_traslado, prioridad_caso, eps, solicitud, parametros
    )
    semaforo = motor_semaforo.calcular_semaforo(hoy, fecha_limite, festivos)

    return {
        "fecha_limite": fecha_limite,
        "regla_aplicada": regla_aplicada,
        "semaforo": semaforo,
    }


def obtener_mis_solicitudes(funcionario_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
    """Caso de uso detrás de la pantalla 'Mis solicitudes' del funcionario."""
    with get_session() as db:
        repo = SolicitudRepo(db)
        solicitudes = repo.listar_por_funcionario(funcionario_id, limit=limit, offset=offset)
        return [
            {
                "id": s.id,
                "numero_solicitud_sac": s.numero_solicitud_sac,
                "sac_solicitud": s.sac_solicitud,
                "estado_gestion": s.estado_gestion,
                "clasificacion_estado": s.clasificacion_estado,
            }
            for s in solicitudes
        ]


def _fecha_texto(valor) -> str:
    return valor.isoformat() if valor is not None else ""


def _fila_solicitud(fila: dict) -> dict:
    solicitud = fila["solicitud"]
    ciudadano = fila["ciudadano"]
    proceso = fila["proceso"]
    funcionario = fila["funcionario"]
    traslado = fila["traslado"]
    respuesta = fila["respuesta"]
    return {
        "id": solicitud.id,
        "numero_solicitud_sac": solicitud.numero_solicitud_sac,
        "semaforo": "SIN_FECHA",
        "estado_sac": solicitud.sac_estado or "",
        "nombre_ciudadano": ciudadano.nombre if ciudadano else "",
        "documento": ciudadano.numero_documento if ciudadano else solicitud.doc_numero_documento or "",
        "proceso": proceso.nombre if proceso else "Sin proceso",
        "funcionario": funcionario.nombre if funcionario else "Sin asignar",
        "funcionario_id": solicitud.funcionario_id,
        "proceso_id": solicitud.proceso_id,
        "motivo": solicitud.sac_motivo or "",
        "tipo_asunto": solicitud.sac_tipo_asunto or "",
        "solicitud": solicitud.sac_solicitud or "",
        "prioridad_caso": solicitud.sac_prioridad_caso or "",
        "eps": solicitud.doc_eps or "",
        "fecha_ingreso": _fecha_texto(solicitud.sac_fecha_ingreso),
        "fecha_limite": _fecha_texto(traslado.fecha_limite_respuesta if traslado else None),
        "estado_gestion": solicitud.estado_gestion or "",
        "clasificacion_estado": solicitud.clasificacion_estado or "",
        "fecha_traslado": _fecha_texto(traslado.fecha_traslado if traslado else None),
        "institucion_competente": traslado.institucion_competente if traslado else "",
        "traslado": traslado,
        "respuesta": respuesta,
    }


def obtener_solicitudes(filtros: dict | None, usuario_id: int | None, rol: str | None) -> list[dict]:
    filtros = dict(filtros or {})
    if rol != "ADMINISTRADOR":
        from sgs.repos.permisos_repo import FuncionarioProcesoRepo

        with get_session() as db:
            filtros["proceso_ids"] = (
                FuncionarioProcesoRepo(db).procesos_de(usuario_id)
                if usuario_id is not None
                else []
            )
    with get_session() as db:
        filas = [_fila_solicitud(fila) for fila in SolicitudRepo(db).listar_con_filtros(filtros)]
        festivos: set[dt.date] = set()
        for fila in filas:
            fecha = fila.get("fecha_limite")
            fila["semaforo"] = motor_semaforo.calcular_semaforo(
                dt.date.today(), dt.date.fromisoformat(fecha) if fecha else None, festivos
            )
        return filas


def obtener_dashboard(usuario_id: int | None, rol: str | None) -> dict:
    filas = obtener_solicitudes({}, usuario_id, rol)
    conteos = {"total": len(filas), "en_tiempo": 0, "proximas_vencer": 0, "vencidas": 0}
    for fila in filas:
        if fila["semaforo"] == motor_semaforo.VERDE:
            conteos["en_tiempo"] += 1
        elif fila["semaforo"] == motor_semaforo.AMARILLO:
            conteos["proximas_vencer"] += 1
        elif fila["semaforo"] == motor_semaforo.ROJO:
            conteos["vencidas"] += 1
    prioritarias = [
        (f["numero_solicitud_sac"], f["proceso"], f["semaforo"], f["estado_gestion"])
        for f in filas if f["semaforo"] in (motor_semaforo.ROJO, motor_semaforo.AMARILLO)
    ][:10]
    por_proceso: dict[str, int] = {}
    for fila in filas:
        por_proceso[fila["proceso"]] = por_proceso.get(fila["proceso"], 0) + 1
    maximo = max(por_proceso.values(), default=1)
    conteos["atencion_prioritaria"] = prioritarias
    conteos["por_proceso"] = [
        (nombre, total, round(total * 100 / maximo)) for nombre, total in por_proceso.items()
    ]
    return conteos


def obtener_detalle_solicitud(numero_solicitud: str) -> dict:
    with get_session() as db:
        fila = SolicitudRepo(db).obtener_detalle(numero_solicitud)
        if fila is None:
            raise ValueError(f"No existe la solicitud {numero_solicitud}")
        solicitud = fila["solicitud"]
        ciudadano = fila["ciudadano"]
        proceso = fila["proceso"]
        funcionario = fila["funcionario"]
        traslado = fila["traslado"]
        respuesta = fila["respuesta"]
        ente = fila["ente_control"]
        limite = traslado.fecha_limite_respuesta if traslado else None
        return {
            "numero_solicitud_sac": numero_solicitud,
            "semaforo": motor_semaforo.calcular_semaforo(dt.date.today(), limite, set()),
            "proceso": proceso.nombre if proceso else "Sin proceso",
            "funcionario": funcionario.nombre if funcionario else "Sin asignar",
            "funcionario_id": solicitud.funcionario_id,
            "proceso_id": solicitud.proceso_id,
            "tipo_documento": ciudadano.tipo_documento if ciudadano else solicitud.doc_tipo_documento or "",
            "documento": ciudadano.numero_documento if ciudadano else solicitud.doc_numero_documento or "",
            "nombre_ciudadano": ciudadano.nombre if ciudadano else solicitud.doc_nombre or "",
            "sexo": ciudadano.sexo if ciudadano else solicitud.doc_sexo or "",
            "fecha_nacimiento": _fecha_texto(ciudadano.fecha_nacimiento if ciudadano else solicitud.doc_fecha_nacimiento),
            "edad": solicitud.doc_edad or "",
            "telefono": ciudadano.telefono if ciudadano else solicitud.doc_telefono or "",
            "correo": ciudadano.correo if ciudadano else solicitud.doc_correo or "",
            "municipio_origen": solicitud.doc_municipio_origen or "",
            "municipio_residencia": solicitud.doc_municipio_residencia or "",
            "poblacion_priorizada": solicitud.doc_poblacion_priorizada or "",
            "regimen": solicitud.doc_regimen or "",
            "eps": solicitud.doc_eps or "",
            "motivo": solicitud.sac_motivo or "",
            "tipo_asunto": solicitud.sac_tipo_asunto or "",
            "solicitud": solicitud.sac_solicitud or "",
            "subclasificacion": solicitud.sac_subclasificacion or "",
            "prioridad_caso": solicitud.sac_prioridad_caso or "",
            "barrera_acceso": solicitud.sac_barrera_acceso or "",
            "usuario_sac": solicitud.sac_usuario or "",
            "fecha_ingreso": _fecha_texto(solicitud.sac_fecha_ingreso),
            "estado_sac": solicitud.sac_estado or "",
            "detalle": solicitud.sac_detalle or "",
            "actuacion_funcionario": solicitud.sac_actuacion_funcionario or "",
            "fecha_traslado": _fecha_texto(traslado.fecha_traslado if traslado else None),
            "institucion_competente": traslado.institucion_competente if traslado else "",
            "oportunidad_traslado_dias": traslado.oportunidad_dias_habiles if traslado else "",
            "indicador_oportunidad_traslado": traslado.indicador_oportunidad if traslado else "",
            "fecha_limite": _fecha_texto(limite),
            "dias_restantes": "",
            "hubo_respuesta": respuesta.hubo_respuesta if respuesta else "NO",
            "decision": respuesta.decision if respuesta else "",
            "fecha_respuesta": _fecha_texto(respuesta.fecha_respuesta if respuesta else None),
            "oportunidad_respuesta": respuesta.oportunidad_respuesta if respuesta else "",
            "notificacion_usuario": respuesta.notificacion_usuario if respuesta else "Pendiente",
            "respuesta_entidad": respuesta.respuesta_entidad if respuesta else "",
            "radicado_ente_control": ente.radicado if ente else "",
            "entidad_control": ente.entidad if ente else "",
            "fecha_reporte_control": _fecha_texto(ente.fecha_reporte if ente else None),
            "estado_gestion": solicitud.estado_gestion or "pendiente",
            "observaciones": solicitud.observaciones or "",
        }


def listar_funcionarios_por_proceso(proceso_id: int | None) -> list[dict]:
    if proceso_id is None:
        return []
    with get_session() as db:
        return [
            {"id": u.id, "nombre": u.nombre, "username": u.username}
            for u in UsuarioRepo(db).listar_funcionarios_por_proceso(proceso_id)
        ]


def asignar_funcionario_a_solicitud(numero_sac: str, funcionario_id: int | None) -> None:
    with get_session() as db:
        GestionSolicitudRepo(db).actualizar_gestion(
            numero_sac, {"funcionario_id": funcionario_id}
        )


def obtener_configuracion_columnas(usuario_id: int, pantalla: str) -> list[dict] | None:
    """None significa que el usuario nunca ha guardado una vista propia
    para esta pantalla -> la UI debe usar la configuración por defecto."""
    with get_session() as db:
        return VistaColumnasRepo(db).obtener(usuario_id, pantalla)


def guardar_configuracion_columnas(usuario_id: int, pantalla: str, configuracion: list[dict]) -> None:
    with get_session() as db:
        VistaColumnasRepo(db).guardar(usuario_id, pantalla, configuracion)


def guardar_gestion_solicitud(numero_solicitud_sac: str, cambios: dict) -> None:
    """
    Único punto de entrada para que la UI guarde cambios de gestión
    (Traslado, Respuesta, Ente de control, Estado, Observaciones).
    Nunca acepta ni escribe campos del bloque SAC (sac_*) — esos son
    de solo lectura desde aquí; si `cambios` trajera alguno, se ignora
    silenciosamente en el repo porque no está en su lista de campos.
    """
    with get_session() as db:
        GestionSolicitudRepo(db).actualizar_gestion(numero_solicitud_sac, cambios)


# ----------------------------------------------------------------------
# Importar SAC
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class VistaPreviaImportacion:
    encabezados: list[str]
    total_filas: int
    filas_muestra: list[dict]  # primeras N filas, para mostrar en pantalla
    columnas_faltantes: list[str]  # no vacío = estructura inválida, no continuar


def validar_y_previsualizar_archivo_sac(ruta_archivo: str, filas_muestra: int = 20) -> VistaPreviaImportacion:
    """Pasos 'Seleccionar archivo' -> 'Validar estructura' -> 'Vista previa'."""
    archivo = leer_archivo_sac(ruta_archivo)
    faltantes = motor_importacion_sac.validar_estructura(archivo.encabezados)
    return VistaPreviaImportacion(
        encabezados=archivo.encabezados,
        total_filas=len(archivo.filas),
        filas_muestra=archivo.filas[:filas_muestra],
        columnas_faltantes=faltantes,
    )


def clasificar_y_detectar_duplicados(ruta_archivo: str) -> motor_importacion_sac.ResumenImportacion:
    """Pasos 'Clasificar' -> 'Detectar duplicados' -> 'Mostrar resumen'.
    Vuelve a leer el archivo (se asume mismo `ruta_archivo` de la vista
    previa) para no tener que mantener el contenido completo en memoria
    de la UI entre pasos."""
    archivo = leer_archivo_sac(ruta_archivo)
    numeros = [str(f.get("numerosolicitud", "")).strip() for f in archivo.filas if f.get("numerosolicitud")]

    with get_session() as db:
        reglas = ReglaClasificacionRepo(db).listar_reglas_activas()
        existentes = ImportacionSacRepo(db).obtener_existentes(numeros)

    return motor_importacion_sac.procesar_archivo(archivo.filas, existentes, reglas)


def confirmar_importacion_sac(ruta_archivo: str, archivo_nombre: str, usuario_id: int) -> dict:
    """Paso 'Confirmar importación' -> 'Guardar en PostgreSQL'.
    Repite la clasificación (para trabajar con datos frescos) y esta
    vez sí escribe: crea/actualiza cada solicitud y registra la
    importación con su detalle fila a fila."""
    archivo = leer_archivo_sac(ruta_archivo)

    with get_session() as db:
        reglas = ReglaClasificacionRepo(db).listar_reglas_activas()
        repo_importacion = ImportacionSacRepo(db)
        numeros = [str(f.get("numerosolicitud", "")).strip() for f in archivo.filas if f.get("numerosolicitud")]
        existentes = repo_importacion.obtener_existentes(numeros)

        resumen = motor_importacion_sac.procesar_archivo(archivo.filas, existentes, reglas)

        detalle_para_registrar: list[tuple[int, str]] = []
        por_numero = {
            str(f.get("numerosolicitud", "")).strip(): f for f in archivo.filas if f.get("numerosolicitud")
        }

        for resultado in resumen.resultados:
            if resultado.accion == "error":
                continue  # las filas con error no se guardan
            fila = por_numero[resultado.numero_solicitud_sac]
            solicitud, _ = repo_importacion.crear_o_actualizar_solicitud(
                fila, resultado.numero_solicitud_sac, resultado.proceso_id, resultado.clasificacion_estado
            )
            detalle_para_registrar.append((solicitud.id, resultado.accion))

        importacion = repo_importacion.registrar_importacion(
            archivo_nombre=archivo_nombre,
            usuario_id=usuario_id,
            conteos={
                "total": resumen.total,
                "nuevos": resumen.nuevos,
                "actualizados": resumen.actualizados,
                "sin_cambios": resumen.sin_cambios,
                "errores": resumen.errores,
                "sin_clasificar": resumen.sin_clasificar,
            },
            detalle=detalle_para_registrar,
        )

    por_proceso: dict[str, int] = {}
    with get_session() as db:
        from sgs.models.orm import Proceso

        for resultado in resumen.resultados:
            if resultado.accion == "error" or resultado.proceso_id is None:
                continue
            proceso = db.get(Proceso, resultado.proceso_id)
            nombre = proceso.nombre if proceso else "Sin proceso"
            por_proceso[nombre] = por_proceso.get(nombre, 0) + 1

    return {
        "importacion_id": importacion.id,
        "total": resumen.total,
        "nuevos": resumen.nuevos,
        "actualizados": resumen.actualizados,
        "sin_cambios": resumen.sin_cambios,
        "errores": resumen.errores,
        "sin_clasificar": resumen.sin_clasificar,
        "conflictos": resumen.conflictos,
        "por_proceso": por_proceso,
    }


# ----------------------------------------------------------------------
# Configuración · Usuarios
# ----------------------------------------------------------------------

def listar_usuarios() -> list[dict]:
    with get_session() as db:
        return [
            {
                "id": u.id,
                "codigo_sac": u.codigo_sac,
                "username": u.username,
                "nombre": u.nombre,
                "rol": u.rol,
                "activo": u.activo,
            }
            for u in UsuarioRepo(db).listar()
        ]


def crear_usuario(codigo_sac: str, username: str, nombre: str, rol: str, password: str) -> int:
    from sgs.models.orm import Usuario as UsuarioModel

    with get_session() as db:
        usuario = UsuarioModel(
            codigo_sac=codigo_sac or None,
            username=username,
            nombre=nombre,
            rol=rol,
            password_hash=motor_auth.hashear_password(password),
            activo=True,
        )
        UsuarioRepo(db).guardar(usuario)
        return usuario.id


def cambiar_estado_usuario(usuario_id: int, activo: bool) -> None:
    with get_session() as db:
        repo = UsuarioRepo(db)
        usuario = repo.obtener_por_id(usuario_id)
        if usuario is None:
            raise ValueError(f"No existe el usuario {usuario_id}")
        usuario.activo = activo


def restablecer_password(usuario_id: int, password_nueva: str) -> None:
    with get_session() as db:
        repo = UsuarioRepo(db)
        usuario = repo.obtener_por_id(usuario_id)
        if usuario is None:
            raise ValueError(f"No existe el usuario {usuario_id}")
        usuario.password_hash = motor_auth.hashear_password(password_nueva)


def actualizar_usuario(
    usuario_id: int, nombre: str, rol: str, codigo_sac: str | None, password_nueva: str | None = None
) -> None:
    with get_session() as db:
        usuario = UsuarioRepo(db).obtener_por_id(usuario_id)
        if usuario is None:
            raise ValueError(f"No existe el usuario {usuario_id}")
        usuario.nombre = nombre.strip()
        usuario.rol = rol
        usuario.codigo_sac = codigo_sac.strip() if codigo_sac else None
        if password_nueva:
            usuario.password_hash = motor_auth.hashear_password(password_nueva)


# ----------------------------------------------------------------------
# Configuración · Procesos
# ----------------------------------------------------------------------

def listar_procesos() -> list[dict]:
    from sgs.repos.proceso_repo import ProcesoRepo

    with get_session() as db:
        return [
            {"id": p.id, "nombre": p.nombre, "descripcion": p.descripcion or "", "activo": p.activo}
            for p in ProcesoRepo(db).listar()
        ]


def crear_proceso(nombre: str, descripcion: str) -> int:
    from sgs.repos.proceso_repo import ProcesoRepo

    with get_session() as db:
        proceso = ProcesoRepo(db).crear(nombre, descripcion)
        return proceso.id


def cambiar_estado_proceso(proceso_id: int, activo: bool) -> None:
    from sgs.repos.proceso_repo import ProcesoRepo

    with get_session() as db:
        ProcesoRepo(db).cambiar_estado(proceso_id, activo)


# ----------------------------------------------------------------------
# Configuración · Roles y permisos
# ----------------------------------------------------------------------

def usuario_tiene_permiso(usuario_id: int, nombre_permiso: str) -> bool:
    from sgs.repos.permisos_repo import PermisoRepo

    with get_session() as db:
        return PermisoRepo(db).usuario_tiene_permiso(usuario_id, nombre_permiso)


def establecer_permiso(usuario_id: int, nombre_permiso: str, activo: bool) -> None:
    from sgs.repos.permisos_repo import PermisoRepo

    with get_session() as db:
        PermisoRepo(db).establecer_permiso(usuario_id, nombre_permiso, activo)


# ----------------------------------------------------------------------
# Configuración · Asignación de funcionarios a procesos
# ----------------------------------------------------------------------

def listar_procesos_de_funcionario(usuario_id: int) -> list[int]:
    from sgs.repos.permisos_repo import FuncionarioProcesoRepo

    with get_session() as db:
        return FuncionarioProcesoRepo(db).procesos_de(usuario_id)


def asignar_procesos_a_funcionario(usuario_id: int, proceso_ids: list[int]) -> None:
    from sgs.repos.permisos_repo import FuncionarioProcesoRepo

    with get_session() as db:
        FuncionarioProcesoRepo(db).establecer_procesos(usuario_id, proceso_ids)


# ----------------------------------------------------------------------
# Configuración · Semaforización
# ----------------------------------------------------------------------

def obtener_parametros_semaforizacion() -> dict:
    from sgs.repos.parametros_semaforizacion_repo import ParametrosSemaforizacionRepo

    with get_session() as db:
        fila = ParametrosSemaforizacionRepo(db).obtener()
        return {"dias_rojo": fila.dias_habiles_verde_hasta, "dias_amarillo": fila.dias_habiles_amarillo_hasta}


def guardar_parametros_semaforizacion(dias_rojo: int, dias_amarillo: int) -> None:
    from sgs.repos.parametros_semaforizacion_repo import ParametrosSemaforizacionRepo

    with get_session() as db:
        ParametrosSemaforizacionRepo(db).guardar(dias_rojo, dias_amarillo)


# ----------------------------------------------------------------------
# Configuración · Reglas de clasificación (solo consulta por ahora)
# ----------------------------------------------------------------------

def listar_reglas_clasificacion_para_mostrar() -> list[dict]:
    with get_session() as db:
        return ReglaClasificacionRepo(db).listar_para_mostrar()


# ----------------------------------------------------------------------
# Configuración · Tiempos de respuesta
# ----------------------------------------------------------------------

def listar_reglas_tiempos_solicitud() -> list[dict]:
    with get_session() as db:
        return ReglaTiemposRepo(db).listar_reglas_solicitud()


def listar_reglas_tiempos_prioridad() -> list[dict]:
    with get_session() as db:
        return ReglaTiemposRepo(db).listar_reglas_prioridad()


def listar_reglas_tiempos_eps() -> list[dict]:
    with get_session() as db:
        return ReglaTiemposRepo(db).listar_reglas_eps()


def listar_festivos() -> list[dict]:
    with get_session() as db:
        return ReglaTiemposRepo(db).listar_festivos()


def guardar_reglas_tiempos_solicitud(filas: list[dict]) -> None:
    with get_session() as db:
        ReglaTiemposRepo(db).reemplazar_reglas_solicitud(filas)


def guardar_reglas_tiempos_prioridad(filas: list[dict]) -> None:
    with get_session() as db:
        ReglaTiemposRepo(db).reemplazar_reglas_prioridad(filas)


def guardar_reglas_tiempos_eps(filas: list[dict]) -> None:
    with get_session() as db:
        ReglaTiemposRepo(db).reemplazar_reglas_eps(filas)


def guardar_festivos(filas: list[dict]) -> None:
    with get_session() as db:
        ReglaTiemposRepo(db).reemplazar_festivos(filas)


# ----------------------------------------------------------------------
# Configuración · Parámetros generales
# ----------------------------------------------------------------------

def obtener_parametros_generales() -> dict[str, str]:
    from sgs.repos.parametro_general_repo import ParametroGeneralRepo

    with get_session() as db:
        return ParametroGeneralRepo(db).listar()


def guardar_parametro_general(clave: str, valor: str) -> None:
    from sgs.repos.parametro_general_repo import ParametroGeneralRepo

    with get_session() as db:
        ParametroGeneralRepo(db).guardar(clave, valor)